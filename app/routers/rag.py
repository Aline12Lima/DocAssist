import time
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.config import settings
from app.schemas.requests import AskRequest, DocumentRequest, SearchRequest
from app.schemas.responses import (
    AskResponse,
    DocumentoInfo,
    DocumentosResponse,
    DocumentResponse,
    IngestResponse,
    SearchResponse,
    SearchResult,
)
from app.services.llm.cadeia import criar_cadeia
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
from app.services.rag.pipeline import responder
from app.services.rag.vetores import buscar

router = APIRouter()


# Dependências: nos testes, são trocadas por uma coleção em memória e um modelo falso.
def obter_colecao_rag():
    return colecao_principal()


def obter_embedder_rag():
    return embedder_principal()


@lru_cache
def _cadeia_de_llm():
    return criar_cadeia()


def obter_llm_rag():
    """A cadeia de LLM do .env; None se nenhuma chave estiver configurada."""
    try:
        return _cadeia_de_llm()
    except ValueError:
        return None


def montar_filtros(doc_id: str | None, fonte: str | None) -> dict | None:
    condicoes = [{campo: valor} for campo, valor in (("doc_id", doc_id), ("fonte", fonte)) if valor]
    if not condicoes:
        return None
    return condicoes[0] if len(condicoes) == 1 else {"$and": condicoes}


@router.post(
    "/ask",
    response_model=AskResponse,
    summary="Responde a pergunta com base nos documentos, citando as fontes",
    responses={409: {"description": "Nenhum documento indexado"}},
)
def ask(
    body: AskRequest,
    colecao=Depends(obter_colecao_rag),
    embedder=Depends(obter_embedder_rag),
    llm=Depends(obter_llm_rag),
):
    """
    1. Busca os trechos mais parecidos com a pergunta.
    2. Se nenhum for relevante o bastante, responde **"não encontrei"** sem chamar o LLM.
    3. Envia os trechos numerados ao LLM, que responde **só com base neles**, citando `[n]`.
    4. Confere as citações: as que não existem são removidas; sem nenhuma, tenta de novo.

    Se o LLM falhar, a resposta traz os trechos encontrados e um `aviso`, nunca um erro 500.
    """
    if colecao.count() == 0:
        raise HTTPException(status_code=409, detail="Nenhum documento indexado")
    filtros = montar_filtros(body.doc_id, body.fonte)
    return responder(body.pergunta, colecao, embedder, llm, k=body.top_k, filtros=filtros)


@router.post(
    "/ingest",
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
    colecao=Depends(obter_colecao_rag),
    embedder=Depends(obter_embedder_rag),
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
        conteudo, extensao, doc_id, colecao, embedder, {"titulo": titulo, "fonte": fonte}
    )
    if resultado.chunks == 0:
        raise HTTPException(status_code=422, detail="Nenhum texto encontrado no arquivo")

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
    summary="Remove um documento e todos os seus chunks",
    responses={404: {"description": "Documento não encontrado"}},
)
def delete_document(doc_id: str, colecao=Depends(obter_colecao_rag)):
    removidos = remover_documento(colecao, doc_id)
    if removidos == 0:
        raise HTTPException(status_code=404, detail=f"Documento não encontrado: {doc_id}")
    return {"doc_id": doc_id, "chunks_removidos": removidos}


@router.post(
    "/documents",
    response_model=DocumentResponse,
    summary="Adiciona um texto à base (use /rag/ingest para arquivos)",
    deprecated=True,
)
def add_doc(
    body: DocumentRequest,
    colecao=Depends(obter_colecao_rag),
    embedder=Depends(obter_embedder_rag),
):
    """
    Mantido por compatibilidade. O texto é tratado como um pequeno documento Markdown e
    passa pela mesma ingestão do `/rag/ingest`. Enviar o mesmo texto de novo não duplica.
    """
    doc_id = body.metadata.get("doc_id") or doc_id_de_texto(body.text)
    documento = {"titulo": body.metadata.get("titulo"), "fonte": body.metadata.get("fonte")}
    ingerir_conteudo(body.text.encode("utf-8"), ".md", doc_id, colecao, embedder, documento)
    return DocumentResponse(id=doc_id, text=body.text)


@router.post(
    "/search",
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

    resultados = buscar(body.query, colecao, embedder, k=body.top_k, filtros=filtros)
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
def get_stats(colecao=Depends(obter_colecao_rag), embedder=Depends(obter_embedder_rag)):
    """Coleção em uso, modelo de embedding, quantidade de documentos e de chunks."""
    return {
        "colecao": colecao.name,
        "modelo": embedder.config.nome,
        "documentos": len(listar_documentos(colecao)),
        "chunks": colecao.count(),
    }
