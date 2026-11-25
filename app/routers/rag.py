import json
import logging
import time
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database.connection import SessionLocal, get_db
from app.schemas.requests import AskRequest, DocumentRequest, FeedbackRequest, SearchRequest
from app.schemas.responses import (
    AskResponse,
    DocumentoInfo,
    DocumentosResponse,
    DocumentResponse,
    FeedbackResponse,
    FeedbackResumo,
    IngestResponse,
    InteracaoInfo,
    SearchResponse,
    SearchResult,
)
from app.services.llm.base import ErroDoProvedor
from app.services.llm.cadeia import criar_cadeia
from app.services.metricas import registrar_bloqueio, registrar_resposta, registrar_voto
from app.services.rag.cache import (
    buscar_resposta,
    guardar_resposta,
    invalidar,
    montar_chave,
    versao_do_indice,
)
from app.services.rag.documentos import (
    EXTENSOES_ACEITAS,
    colecao_principal,
    doc_id_de_texto,
    embedder_principal,
    gerar_doc_id,
    ingerir_conteudo,
    listar_documentos,
    remover_documento,
)
from app.services.rag.feedback import InteracaoInexistente, registrar_feedback, resumir_feedback
from app.services.rag.geracao import versao_do_prompt
from app.services.rag.historico import listar_interacoes, registrar_interacao
from app.services.rag.pipeline import (
    assinatura_da_recuperacao,
    responder,
    responder_em_partes,
)
from app.services.rag.reranker import obter_reranker
from app.services.rag.vetores import buscar
from app.services.redis_service import get_redis_client
from app.services.seguranca import (
    DEMO,
    Cliente,
    Uso,
    identificar_cliente,
    identificar_quem_pergunta,
    registrar_uso,
    registrar_uso_do_dia,
)

router = APIRouter()
logger = logging.getLogger(__name__)


# Dependências: nos testes, são trocadas por uma coleção em memória e um modelo falso.
def obter_colecao_rag():
    return colecao_principal()


def obter_embedder_rag():
    return embedder_principal()


def obter_redis_rag():
    """O cliente do Redis; None se ele estiver fora do ar (o RAG segue sem cache)."""
    try:
        return get_redis_client()
    except Exception:  # noqa: BLE001 - qualquer falha de conexão só desliga o cache
        return None


@lru_cache
def _cadeia_de_llm():
    return criar_cadeia()


def obter_llm_rag():
    """A cadeia de LLM do .env; None se nenhuma chave estiver configurada."""
    try:
        return _cadeia_de_llm()
    except ValueError:
        return None


def obter_reranker_rag():
    """O reranker; None se ele estiver desligado (RAG_RERANKER_ATIVO=false no .env)."""
    if not settings.RAG_RERANKER_ATIVO:
        return None
    return obter_reranker(settings.RAG_RERANKER_MODELO)


def barrar(uso: Uso, mensagem: str) -> None:
    """Passou do limite: 429, com o tempo de espera no cabeçalho Retry-After."""
    registrar_bloqueio()
    raise HTTPException(
        status_code=429, detail=mensagem, headers={"Retry-After": str(uso.espera_s)}
    )


def limitar_perguntas(
    cliente: Cliente = Depends(identificar_quem_pergunta), redis_cliente=Depends(obter_redis_rag)
) -> str:
    """Autentica e conta a pergunta; passou do limite, 429.

    Chave de demo: limite menor por minuto (por IP) e, depois dele, o teto do dia somando
    todos os visitantes. A ordem importa: quem foi barrado no minuto não gasta o teto do dia.
    """
    demo = cliente.papel == DEMO
    limite = (
        settings.RATE_LIMIT_DEMO_POR_MINUTO if demo else settings.RATE_LIMIT_PERGUNTAS_POR_MINUTO
    )
    uso = registrar_uso(redis_cliente, cliente.id, limite)
    if not uso.permitido:
        barrar(
            uso,
            f"Limite de {uso.limite} perguntas por minuto atingido. "
            f"Tente de novo em {uso.espera_s} s.",
        )
    if demo:
        dia = registrar_uso_do_dia(redis_cliente, "demo", settings.LIMITE_DIARIO_DEMO)
        if not dia.permitido:
            barrar(
                dia,
                f"A demonstração atingiu o limite de {dia.limite} perguntas de hoje. "
                "Volte amanhã ou assista ao vídeo no README.",
            )
    return cliente.id


AUTENTICAR = [Depends(identificar_cliente)]  # só a chave completa (ingerir, apagar, histórico)
PERGUNTAR = [Depends(identificar_quem_pergunta)]  # também a chave de demo (votar)
LIMITAR = [Depends(limitar_perguntas)]  # também a chave de demo, com limites próprios


BUSCA_INDISPONIVEL = (
    "A busca está indisponível agora: não foi possível gerar o embedding da pergunta. "
    "Tente de novo em instantes."
)


def obter_fabrica_de_sessao():
    """Para o streaming: a resposta continua depois que a função do endpoint termina,
    então a sessão do banco é aberta lá dentro, na hora de registrar a interação."""
    return SessionLocal


def evento_sse(evento: str, dados) -> str:
    """Um evento no formato Server-Sent Events: linhas "event:" e "data:" e uma linha vazia."""
    return f"event: {evento}\ndata: {json.dumps(dados, ensure_ascii=False, default=str)}\n\n"


def montar_filtros(doc_id: str | None, fonte: str | None) -> dict | None:
    condicoes = [{campo: valor} for campo, valor in (("doc_id", doc_id), ("fonte", fonte)) if valor]
    if not condicoes:
        return None
    return condicoes[0] if len(condicoes) == 1 else {"$and": condicoes}


@router.post(
    "/ask",
    dependencies=LIMITAR,
    response_model=AskResponse,
    summary="Responde a pergunta com base nos documentos, citando as fontes",
    responses={409: {"description": "Nenhum documento indexado"}},
)
def ask(
    body: AskRequest,
    colecao=Depends(obter_colecao_rag),
    embedder=Depends(obter_embedder_rag),
    llm=Depends(obter_llm_rag),
    redis_cliente=Depends(obter_redis_rag),
    reranker=Depends(obter_reranker_rag),
    db: Session = Depends(get_db),
):
    """
    0. Se a mesma pergunta já foi respondida com a base e o prompt atuais, devolve do
       **cache**, em milissegundos e sem chamar o LLM.
    1. Busca os candidatos mais parecidos com a pergunta e o **reranker** os reordena.
    2. Se nenhum for relevante o bastante, responde **"não encontrei"** sem chamar o LLM.
    3. Envia os trechos numerados ao LLM, que responde **só com base neles**, citando `[n]`.
    4. Confere as citações: as que não existem são removidas; sem nenhuma, tenta de novo.

    Se o LLM falhar, a resposta traz os trechos encontrados e um `aviso`, nunca um erro 500.
    Toda pergunta fica registrada no histórico (`interacao_id`).
    """
    if colecao.count() == 0:
        raise HTTPException(status_code=409, detail="Nenhum documento indexado")

    inicio = time.perf_counter()
    filtros = montar_filtros(body.doc_id, body.fonte)
    k = body.top_k or settings.RAG_TOP_K_CONTEXTO
    versao = versao_do_indice(redis_cliente)
    chave = montar_chave(
        body.pergunta, filtros, k, versao, versao_do_prompt(), assinatura_da_recuperacao(reranker)
    )

    resultado = buscar_resposta(redis_cliente, chave)
    if resultado:
        resultado["pergunta"] = body.pergunta  # como a pessoa escreveu desta vez
        resultado["meta"]["cache"] = True
        resultado["meta"]["latencia_ms"] = int((time.perf_counter() - inicio) * 1000)
    else:
        try:
            resultado = responder(
                body.pergunta, colecao, embedder, llm, k=k, filtros=filtros, reranker=reranker
            )
        except ErroDoProvedor as erro:  # falhas do LLM já viram aviso; esta é do embedding
            logger.warning("Embedding indisponível: %s", erro)
            raise HTTPException(status_code=503, detail=BUSCA_INDISPONIVEL) from erro
        resultado["meta"]["index_version"] = versao
        if not resultado["meta"]["falha_do_llm"]:  # uma falha não pode ficar 24 h no cache
            guardar_resposta(redis_cliente, chave, resultado, settings.RAG_CACHE_TTL_S)

    resultado["meta"]["index_version"] = versao
    resultado["interacao_id"] = registrar_interacao(
        db, resultado, filtros, versao, do_cache=resultado["meta"]["cache"]
    )
    registrar_resposta(resultado, rota="ask")
    return resultado


@router.post(
    "/ask/stream",
    dependencies=LIMITAR,
    summary="Pergunta com resposta em streaming (Server-Sent Events)",
    response_class=StreamingResponse,
    responses={
        200: {
            "content": {"text/event-stream": {}},
            "description": "Eventos `parcial` (pedaços do texto) e um `fim` (resultado final)",
        },
        409: {"description": "Nenhum documento indexado"},
    },
)
def ask_stream(
    body: AskRequest,
    colecao=Depends(obter_colecao_rag),
    embedder=Depends(obter_embedder_rag),
    llm=Depends(obter_llm_rag),
    redis_cliente=Depends(obter_redis_rag),
    reranker=Depends(obter_reranker_rag),
    fabrica_de_sessao=Depends(obter_fabrica_de_sessao),
):
    """
    Mesmo pipeline do `/rag/ask`, mas o texto chega **aos pedaços**, enquanto o modelo
    escreve. A pessoa começa a ler em ~1 s em vez de esperar a resposta inteira.

    Eventos:
    - `parcial`: `{"texto": "..."}`, um pedaço da resposta (prévia, citações não conferidas);
    - `fim`: o mesmo JSON do `/rag/ask`, com as citações conferidas e o `interacao_id`.
      O texto do `fim` é o oficial e substitui a prévia;
    - `erro`: `{"detalhe": "..."}`, se algo inesperado acontecer no meio do caminho.

    Respostas do cache e "não encontrei" chegam direto como um único `fim`.
    Teste com `curl -N` (o `-N` desliga o buffer e mostra os eventos conforme chegam).
    """
    if colecao.count() == 0:
        raise HTTPException(status_code=409, detail="Nenhum documento indexado")

    inicio = time.perf_counter()
    filtros = montar_filtros(body.doc_id, body.fonte)
    k = body.top_k or settings.RAG_TOP_K_CONTEXTO
    versao = versao_do_indice(redis_cliente)
    chave = montar_chave(
        body.pergunta, filtros, k, versao, versao_do_prompt(), assinatura_da_recuperacao(reranker)
    )

    def eventos():
        try:
            resultado = buscar_resposta(redis_cliente, chave)
            if resultado:
                resultado["pergunta"] = body.pergunta
                resultado["meta"]["cache"] = True
                resultado["meta"]["latencia_ms"] = int((time.perf_counter() - inicio) * 1000)
            else:
                for evento in responder_em_partes(
                    body.pergunta, colecao, embedder, llm, k=k, filtros=filtros, reranker=reranker
                ):
                    if evento["evento"] == "fim":
                        resultado = evento["dados"]
                    else:
                        yield evento_sse(evento["evento"], evento["dados"])
                resultado["meta"]["index_version"] = versao
                if not resultado["meta"]["falha_do_llm"]:
                    guardar_resposta(redis_cliente, chave, resultado, settings.RAG_CACHE_TTL_S)

            resultado["meta"]["index_version"] = versao
            db = fabrica_de_sessao()
            try:
                resultado["interacao_id"] = registrar_interacao(
                    db, resultado, filtros, versao, do_cache=resultado["meta"]["cache"]
                )
            finally:
                db.close()
            registrar_resposta(resultado, rota="stream")
            yield evento_sse("fim", resultado)
        except ErroDoProvedor as erro:
            logger.warning("Embedding indisponível no streaming: %s", erro)
            yield evento_sse("erro", {"detalhe": BUSCA_INDISPONIVEL})
        except Exception as erro:  # noqa: BLE001 - o cabeçalho 200 já foi enviado
            logger.exception("Erro no streaming do /rag/ask")
            yield evento_sse("erro", {"detalhe": f"Erro inesperado: {type(erro).__name__}"})

    return StreamingResponse(
        eventos(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get(
    "/interacoes",
    dependencies=AUTENTICAR,
    response_model=list[InteracaoInfo],
    summary="Últimas perguntas feitas ao /rag/ask",
)
def list_interactions(
    limite: int = Query(20, ge=1, le=200),
    so_sem_resposta: bool = Query(False, description="Só as que terminaram sem resposta"),
    db: Session = Depends(get_db),
):
    """Histórico com modelo, tokens, latência e se a resposta veio do cache."""
    return listar_interacoes(db, limite, so_sem_resposta)


@router.post(
    "/feedback",
    dependencies=PERGUNTAR,
    response_model=FeedbackResponse,
    summary="Registra se uma resposta foi útil (👍) ou não (👎)",
    responses={404: {"description": "interacao_id não encontrado no histórico"}},
)
def give_feedback(body: FeedbackRequest, db: Session = Depends(get_db)):
    """Use o `interacao_id` que veio na resposta do `/rag/ask` ou do `/rag/ask/stream`.
    Votar de novo na mesma resposta troca o voto: vale o último."""
    try:
        voto = registrar_feedback(db, body.interacao_id, body.util, body.comentario)
    except InteracaoInexistente as erro:
        raise HTTPException(status_code=404, detail="interacao_id não encontrado") from erro
    registrar_voto(body.util)
    return voto


@router.get(
    "/feedback/resumo",
    dependencies=AUTENTICAR,
    response_model=FeedbackResumo,
    summary="Quantas respostas ajudaram e as últimas que não ajudaram",
)
def feedback_summary(
    limite: int = Query(10, ge=1, le=100, description="Quantas respostas 👎 listar"),
    db: Session = Depends(get_db),
):
    """As respostas com 👎 são candidatas a novas perguntas do golden set."""
    return resumir_feedback(db, limite)


@router.post(
    "/ingest",
    dependencies=AUTENTICAR,
    response_model=IngestResponse,
    summary="Envia um arquivo (PDF, Markdown ou HTML) para a base",
    responses={
        413: {"description": "Arquivo acima do limite de tamanho"},
        415: {"description": "Formato não suportado"},
        422: {"description": "Nenhum texto encontrado no arquivo"},
    },
)
def ingest(
    arquivo: UploadFile = File(..., description="Arquivo .pdf, .md ou .html"),
    doc_id: str | None = Form(None, description="ID do documento (padrão: nome do arquivo)"),
    titulo: str | None = Form(None, description="Título (padrão: o do próprio arquivo)"),
    fonte: str | None = Form(None, description="Fonte, para filtrar buscas (ex.: docker)"),
    url: str | None = Form(None, description="Endereço da página original, para as citações"),
    colecao=Depends(obter_colecao_rag),
    embedder=Depends(obter_embedder_rag),
    redis_cliente=Depends(obter_redis_rag),
):
    """
    Lê o arquivo, divide em seções e chunks, gera os embeddings e salva na base.

    - **Reenviar o mesmo arquivo não duplica**: os IDs dos chunks vêm do documento e da posição.
    - **Atualizar um arquivo** substitui os chunks antigos e apaga os que deixaram de existir.
    - Chunks que não mudaram não passam pelo modelo de novo.
    """
    extensao = Path(arquivo.filename or "").suffix.lower()
    if extensao not in EXTENSOES_ACEITAS:
        raise HTTPException(status_code=415, detail="Formatos aceitos: PDF, MD, HTML")

    conteudo = arquivo.file.read()
    if len(conteudo) > settings.RAG_MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(
            status_code=413, detail=f"Limite de {settings.RAG_MAX_UPLOAD_MB} MB por arquivo"
        )

    doc_id = doc_id or gerar_doc_id(arquivo.filename)
    inicio = time.perf_counter()
    resultado = ingerir_conteudo(
        conteudo,
        extensao,
        doc_id,
        colecao,
        embedder,
        {"titulo": titulo, "fonte": fonte, "url": url},
    )
    if resultado.chunks == 0:
        raise HTTPException(status_code=422, detail="Nenhum texto encontrado no arquivo")
    if resultado.gerados or resultado.removidos:
        invalidar(redis_cliente)  # a base mudou: respostas antigas deixam de valer

    return IngestResponse(
        doc_id=doc_id,
        chunks=resultado.chunks,
        gerados=resultado.gerados,
        removidos=resultado.removidos,
        tempo_ms=int((time.perf_counter() - inicio) * 1000),
    )


@router.get(
    "/documents",
    response_model=DocumentosResponse,
    summary="Lista os documentos da base",
)
def list_documents(colecao=Depends(obter_colecao_rag)):
    """Mostra cada documento indexado, com título, fonte e quantidade de chunks."""
    documentos = listar_documentos(colecao)
    return DocumentosResponse(
        total=len(documentos), documentos=[DocumentoInfo(**d) for d in documentos]
    )


@router.delete(
    "/documents/{doc_id}",
    dependencies=AUTENTICAR,
    summary="Remove um documento e todos os seus chunks",
    responses={404: {"description": "Documento não encontrado"}},
)
def delete_document(
    doc_id: str, colecao=Depends(obter_colecao_rag), redis_cliente=Depends(obter_redis_rag)
):
    removidos = remover_documento(colecao, doc_id)
    if removidos == 0:
        raise HTTPException(status_code=404, detail=f"Documento não encontrado: {doc_id}")
    invalidar(redis_cliente)
    return {"doc_id": doc_id, "chunks_removidos": removidos}


@router.post(
    "/documents",
    dependencies=AUTENTICAR,
    response_model=DocumentResponse,
    summary="Adiciona um texto à base (use /rag/ingest para arquivos)",
    deprecated=True,
)
def add_doc(
    body: DocumentRequest,
    colecao=Depends(obter_colecao_rag),
    embedder=Depends(obter_embedder_rag),
    redis_cliente=Depends(obter_redis_rag),
):
    """
    Mantido por compatibilidade. O texto é tratado como um pequeno documento Markdown e
    passa pela mesma ingestão do `/rag/ingest`. Enviar o mesmo texto de novo não duplica.
    """
    doc_id = body.metadata.get("doc_id") or doc_id_de_texto(body.text)
    documento = {"titulo": body.metadata.get("titulo"), "fonte": body.metadata.get("fonte")}
    resultado = ingerir_conteudo(
        body.text.encode("utf-8"), ".md", doc_id, colecao, embedder, documento
    )
    if resultado.gerados or resultado.removidos:
        invalidar(redis_cliente)
    return DocumentResponse(id=doc_id, text=body.text)


@router.post(
    "/search",
    dependencies=AUTENTICAR,
    response_model=SearchResponse,
    summary="Busca os trechos mais parecidos com a pergunta",
    responses={409: {"description": "Nenhum documento indexado"}},
)
def search(
    body: SearchRequest,
    colecao=Depends(obter_colecao_rag),
    embedder=Depends(obter_embedder_rag),
):
    """
    Busca por **significado** usando o modelo multilíngue: a pergunta pode estar em
    português mesmo com documentos em inglês.

    - **Distância cosseno:** menor = mais parecido.
    - **Filtros opcionais:** `doc_id` e `fonte` restringem a busca antes da comparação.
    """
    if colecao.count() == 0:
        raise HTTPException(status_code=409, detail="Nenhum documento indexado")

    filtros = montar_filtros(body.doc_id, body.fonte)

    try:
        resultados = buscar(body.query, colecao, embedder, k=body.top_k, filtros=filtros)
    except ErroDoProvedor as erro:
        logger.warning("Embedding indisponível: %s", erro)
        raise HTTPException(status_code=503, detail=BUSCA_INDISPONIVEL) from erro
    return SearchResponse(
        query=body.query,
        results=[
            SearchResult(
                id=r["id"], text=r["texto"], distance=r["distancia"], metadata=r["metadados"]
            )
            for r in resultados
        ],
        total=len(resultados),
    )


@router.get("/stats", summary="Estatísticas da base")
def get_stats(
    colecao=Depends(obter_colecao_rag),
    embedder=Depends(obter_embedder_rag),
    redis_cliente=Depends(obter_redis_rag),
):
    """Coleção em uso, modelo de embedding, quantidade de documentos e de chunks."""
    return {
        "colecao": colecao.name,
        "modelo": embedder.config.nome,
        "documentos": len(listar_documentos(colecao)),
        "chunks": colecao.count(),
        "index_version": versao_do_indice(redis_cliente),
    }
