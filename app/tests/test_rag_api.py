"""Testes dos endpoints do RAG com um Chroma em memória e um modelo falso."""

import json

import chromadb
import pytest
from chromadb.config import Settings as ChromaSettings
from fastapi.testclient import TestClient

from app.config import settings
from app.database.connection import get_db
from app.main import app
from app.routers.rag import (
    obter_colecao_rag,
    obter_embedder_rag,
    obter_fabrica_de_sessao,
    obter_llm_rag,
    obter_redis_rag,
    obter_reranker_rag,
)
from app.services import seguranca
from app.services.rag.vetores import obter_colecao
from app.tests.fakes import (
    EmbedderFalso,
    EmbedderForaDoAr,
    LLMFalso,
    LLMQueFalha,
    RedisFalso,
    RerankerFalso,
    sessao_de_teste,
)

MARKDOWN = b"""# Guia do Redis

## Expiration

After the timeout has expired, the key will automatically be deleted.

## Persistence

RDB persistence performs point-in-time snapshots of your dataset at specified intervals.
"""


@pytest.fixture
def cliente():
    chroma = chromadb.EphemeralClient(ChromaSettings(anonymized_telemetry=False))
    colecao = obter_colecao("docs_teste_api", recriar=True, cliente=chroma)
    app.dependency_overrides[obter_colecao_rag] = lambda: colecao
    app.dependency_overrides[obter_embedder_rag] = lambda: EmbedderFalso()
    llm = LLMFalso(*["Ela é apagada após o timeout [1]."] * 10)
    redis, db = RedisFalso(), sessao_de_teste()
    app.dependency_overrides[obter_llm_rag] = lambda: llm
    app.dependency_overrides[obter_redis_rag] = lambda: redis
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[obter_reranker_rag] = lambda: None  # o modelo real não é baixado
    app.dependency_overrides[obter_fabrica_de_sessao] = lambda: lambda: db
    cliente = TestClient(app)
    cliente.llm, cliente.redis = llm, redis
    yield cliente
    app.dependency_overrides.clear()
    chroma.delete_collection("docs_teste_api")


def enviar(cliente, nome="Guia Rápido.md", conteudo=MARKDOWN, **campos):
    return cliente.post("/rag/ingest", files={"arquivo": (nome, conteudo)}, data=campos)


def test_ingest_cria_chunks_e_gera_doc_id_pelo_nome(cliente):
    resposta = enviar(cliente, fonte="redis")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["doc_id"] == "guia-rapido"
    assert corpo["chunks"] > 0
    assert corpo["gerados"] == corpo["chunks"]


def test_ingest_do_mesmo_arquivo_nao_duplica(cliente):
    primeira = enviar(cliente).json()
    segunda = enviar(cliente).json()

    assert segunda["chunks"] == primeira["chunks"]
    assert segunda["gerados"] == 0
    assert cliente.get("/rag/stats").json()["chunks"] == primeira["chunks"]


def test_ingest_recusa_formato_nao_suportado(cliente):
    resposta = enviar(cliente, nome="planilha.xlsx", conteudo=b"nada")

    assert resposta.status_code == 415


def test_ingest_recusa_arquivo_grande_demais(cliente, monkeypatch):
    monkeypatch.setattr(settings, "RAG_MAX_UPLOAD_MB", 0)

    resposta = enviar(cliente)

    assert resposta.status_code == 413


def test_ingest_recusa_arquivo_sem_texto(cliente):
    resposta = enviar(cliente, nome="vazio.md", conteudo=b"   ")

    assert resposta.status_code == 422


def test_listar_e_remover_documento(cliente):
    enviar(cliente, doc_id="guia-redis", fonte="redis")

    lista = cliente.get("/rag/documents").json()
    assert lista["total"] == 1
    assert lista["documentos"][0]["doc_id"] == "guia-redis"
    assert lista["documentos"][0]["fonte"] == "redis"

    assert cliente.delete("/rag/documents/guia-redis").status_code == 200
    assert cliente.get("/rag/documents").json()["total"] == 0
    assert cliente.delete("/rag/documents/guia-redis").status_code == 404


def test_search_com_base_vazia_responde_409(cliente):
    resposta = cliente.post("/rag/search", json={"query": "qualquer coisa"})

    assert resposta.status_code == 409


def test_search_encontra_o_trecho_e_respeita_o_filtro(cliente):
    enviar(cliente, doc_id="guia-redis", fonte="redis")
    enviar(cliente, nome="outro.md", conteudo=b"# Outro\n\nNada a ver com o assunto.", fonte="x")

    resposta = cliente.post(
        "/rag/search", json={"query": "timeout expired key deleted", "top_k": 5, "fonte": "redis"}
    )

    assert resposta.status_code == 200
    resultados = resposta.json()["results"]
    assert "automatically be deleted" in resultados[0]["text"]
    assert all(r["metadata"]["fonte"] == "redis" for r in resultados)


def test_documents_antigo_ingere_texto_sem_duplicar(cliente):
    corpo = {"text": "FastAPI é um framework Python moderno e muito rápido.", "metadata": {}}

    primeira = cliente.post("/rag/documents", json=corpo).json()
    segunda = cliente.post("/rag/documents", json=corpo).json()

    assert primeira["id"] == segunda["id"]
    assert primeira["id"].startswith("texto-")
    assert cliente.get("/rag/stats").json()["documentos"] == 1


def test_ask_responde_com_citacoes(cliente, monkeypatch):
    monkeypatch.setattr(settings, "RAG_LIMIAR_DISTANCIA", 1.5)
    enviar(cliente, doc_id="guia-redis", fonte="redis")

    resposta = cliente.post("/rag/ask", json={"pergunta": "key deleted after timeout expired"})

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["encontrou_resposta"] is True
    assert corpo["resposta"] == "Ela é apagada após o timeout [1]."
    assert corpo["citacoes"][0]["n"] == 1
    assert corpo["citacoes"][0]["doc_id"] == "guia-redis"
    assert corpo["meta"]["prompt_version"] == settings.LLM_PROMPT_VERSAO


def test_ask_com_base_vazia_responde_409(cliente):
    resposta = cliente.post("/rag/ask", json={"pergunta": "qualquer coisa"})

    assert resposta.status_code == 409


def perguntar(cliente, pergunta="key deleted after timeout expired"):
    return cliente.post("/rag/ask", json={"pergunta": pergunta}).json()


def test_ask_repetida_vem_do_cache_sem_chamar_o_llm(cliente, monkeypatch):
    monkeypatch.setattr(settings, "RAG_LIMIAR_DISTANCIA", 1.5)
    enviar(cliente, doc_id="guia-redis")

    primeira = perguntar(cliente)
    segunda = perguntar(cliente, "  Key deleted after TIMEOUT expired?? ")

    assert primeira["meta"]["cache"] is False
    assert segunda["meta"]["cache"] is True
    assert segunda["resposta"] == primeira["resposta"]
    assert segunda["pergunta"] == "  Key deleted after TIMEOUT expired?? "
    assert len(cliente.llm.mensagens_recebidas) == 1  # o LLM só foi chamado uma vez


def test_ingestao_invalida_o_cache(cliente, monkeypatch):
    monkeypatch.setattr(settings, "RAG_LIMIAR_DISTANCIA", 1.5)
    enviar(cliente, doc_id="guia-redis")
    perguntar(cliente)
    versao_antes = cliente.get("/rag/stats").json()["index_version"]

    enviar(cliente, nome="novo.md", conteudo=b"# Novo\n\nUm documento novo sobre timeout.")
    depois = perguntar(cliente)

    assert cliente.get("/rag/stats").json()["index_version"] == versao_antes + 1
    assert depois["meta"]["cache"] is False
    assert len(cliente.llm.mensagens_recebidas) == 2


def test_reenviar_o_mesmo_arquivo_nao_invalida(cliente):
    enviar(cliente, doc_id="guia-redis")
    versao = cliente.get("/rag/stats").json()["index_version"]

    enviar(cliente, doc_id="guia-redis")  # nada mudou

    assert cliente.get("/rag/stats").json()["index_version"] == versao


def test_falha_do_llm_nao_vai_para_o_cache(cliente, monkeypatch):
    monkeypatch.setattr(settings, "RAG_LIMIAR_DISTANCIA", 1.5)
    enviar(cliente, doc_id="guia-redis")
    app.dependency_overrides[obter_llm_rag] = lambda: LLMQueFalha()

    perguntar(cliente)

    assert not [c for c in cliente.redis.dados if c.startswith("rag:ans:")]


def test_ask_registra_no_historico(cliente, monkeypatch):
    monkeypatch.setattr(settings, "RAG_LIMIAR_DISTANCIA", 1.5)
    enviar(cliente, doc_id="guia-redis")

    resposta = perguntar(cliente)
    perguntar(cliente)  # a segunda vem do cache

    historico = cliente.get("/rag/interacoes").json()
    assert resposta["interacao_id"] in [h["id"] for h in historico]
    assert sorted(h["do_cache"] for h in historico) == [False, True]


def test_ask_com_reranker_informa_a_nota(cliente, monkeypatch):
    monkeypatch.setattr(settings, "RAG_LIMIAR_RERANKER", 2.0)
    app.dependency_overrides[obter_reranker_rag] = lambda: RerankerFalso(padrao=7.5)
    enviar(cliente)

    corpo = cliente.post("/rag/ask", json={"pergunta": "Quando a chave é apagada?"}).json()

    assert corpo["encontrou_resposta"] is True
    assert corpo["meta"]["reranker"] == "falso:reranker"
    assert corpo["meta"]["nota_reranker_top1"] == 7.5
    assert corpo["citacoes"][0]["nota_reranker"] == 7.5


def test_ask_com_nota_baixa_responde_nao_encontrei(cliente, monkeypatch):
    monkeypatch.setattr(settings, "RAG_LIMIAR_RERANKER", 2.0)
    app.dependency_overrides[obter_reranker_rag] = lambda: RerankerFalso(padrao=0.1)
    enviar(cliente)

    corpo = cliente.post("/rag/ask", json={"pergunta": "Como configurar o Kubernetes?"}).json()

    assert corpo["encontrou_resposta"] is False
    assert cliente.llm.mensagens_recebidas == []


# ---------- /rag/ask/stream


def ler_eventos(texto: str) -> list[tuple[str, dict]]:
    """Separa a resposta SSE em (evento, dados)."""
    eventos = []
    for bloco in texto.strip().split("\n\n"):
        linhas = dict(linha.split(": ", 1) for linha in bloco.splitlines())
        eventos.append((linhas["event"], json.loads(linhas["data"])))
    return eventos


def test_stream_manda_pedacos_e_depois_o_fim(cliente, monkeypatch):
    monkeypatch.setattr(settings, "RAG_LIMIAR_DISTANCIA", 1.5)
    enviar(cliente)

    resposta = cliente.post("/rag/ask/stream", json={"pergunta": "Quando a chave é apagada?"})

    assert resposta.status_code == 200
    assert resposta.headers["content-type"].startswith("text/event-stream")
    eventos = ler_eventos(resposta.text)
    parciais = [dados["texto"] for nome, dados in eventos if nome == "parcial"]
    assert len(parciais) > 1
    assert "".join(parciais) == "Ela é apagada após o timeout [1]."
    nome, fim = eventos[-1]
    assert nome == "fim"
    assert fim["encontrou_resposta"] is True
    assert fim["citacoes"][0]["n"] == 1
    assert fim["meta"]["modelo"] == "falso:modelo"
    assert fim["interacao_id"]


def test_stream_usa_o_cache_na_segunda_vez(cliente, monkeypatch):
    monkeypatch.setattr(settings, "RAG_LIMIAR_DISTANCIA", 1.5)
    enviar(cliente)
    cliente.post("/rag/ask/stream", json={"pergunta": "Quando a chave é apagada?"})

    eventos = ler_eventos(
        cliente.post("/rag/ask/stream", json={"pergunta": "quando a chave é apagada"}).text
    )

    assert [nome for nome, _ in eventos] == ["fim"]
    assert eventos[0][1]["meta"]["cache"] is True


def test_stream_com_llm_fora_do_ar_termina_com_aviso(cliente, monkeypatch):
    monkeypatch.setattr(settings, "RAG_LIMIAR_DISTANCIA", 1.5)
    app.dependency_overrides[obter_llm_rag] = lambda: LLMQueFalha()
    enviar(cliente)

    eventos = ler_eventos(cliente.post("/rag/ask/stream", json={"pergunta": "TTL?"}).text)

    assert [nome for nome, _ in eventos] == ["fim"]
    assert eventos[0][1]["encontrou_resposta"] is False
    assert eventos[0][1]["meta"]["falha_do_llm"] is True


def test_stream_sem_documentos_da_409(cliente):
    resposta = cliente.post("/rag/ask/stream", json={"pergunta": "Algo?"})
    assert resposta.status_code == 409


# ---------- /rag/feedback


def perguntar_e_pegar_id(cliente, monkeypatch, pergunta="Quando a chave é apagada?") -> str:
    monkeypatch.setattr(settings, "RAG_LIMIAR_DISTANCIA", 1.5)
    return cliente.post("/rag/ask", json={"pergunta": pergunta}).json()["interacao_id"]


def test_feedback_registra_o_voto(cliente, monkeypatch):
    enviar(cliente)
    interacao_id = perguntar_e_pegar_id(cliente, monkeypatch)

    resposta = cliente.post(
        "/rag/feedback",
        json={"interacao_id": interacao_id, "util": False, "comentario": "  faltou exemplo  "},
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["interacao_id"] == interacao_id
    assert corpo["util"] is False
    assert corpo["comentario"] == "faltou exemplo"


def test_feedback_de_novo_troca_o_voto(cliente, monkeypatch):
    enviar(cliente)
    interacao_id = perguntar_e_pegar_id(cliente, monkeypatch)
    primeiro = cliente.post("/rag/feedback", json={"interacao_id": interacao_id, "util": False})

    segundo = cliente.post("/rag/feedback", json={"interacao_id": interacao_id, "util": True})

    assert segundo.json()["id"] == primeiro.json()["id"]
    resumo = cliente.get("/rag/feedback/resumo").json()
    assert (resumo["votos"], resumo["uteis"], resumo["nao_uteis"]) == (1, 1, 0)


def test_feedback_de_interacao_inexistente_da_404(cliente):
    resposta = cliente.post("/rag/feedback", json={"interacao_id": "nao-existe", "util": True})
    assert resposta.status_code == 404


def test_feedback_com_comentario_longo_demais_da_422(cliente):
    resposta = cliente.post(
        "/rag/feedback", json={"interacao_id": "x", "util": True, "comentario": "a" * 501}
    )
    assert resposta.status_code == 422


def test_resumo_lista_as_respostas_nao_uteis(cliente, monkeypatch):
    enviar(cliente)
    boa = perguntar_e_pegar_id(cliente, monkeypatch, "Quando a chave é apagada?")
    ruim = perguntar_e_pegar_id(cliente, monkeypatch, "O que é TTL?")
    cliente.post("/rag/feedback", json={"interacao_id": boa, "util": True})
    cliente.post("/rag/feedback", json={"interacao_id": ruim, "util": False, "comentario": "vaga"})

    resumo = cliente.get("/rag/feedback/resumo").json()

    assert resumo["votos"] == 2
    assert resumo["taxa_util"] == 0.5
    assert [r["pergunta"] for r in resumo["ultimos_nao_uteis"]] == ["O que é TTL?"]
    assert resumo["ultimos_nao_uteis"][0]["comentario"] == "vaga"


def test_resumo_sem_votos(cliente):
    resumo = cliente.get("/rag/feedback/resumo").json()
    assert resumo["votos"] == 0
    assert resumo["taxa_util"] is None


# ---------- chave de API e limite de uso (o resto está em test_seguranca.py)


def test_sem_chaves_configuradas_a_api_fica_aberta(cliente, monkeypatch):
    monkeypatch.setattr(settings, "API_KEYS", "")
    assert cliente.get("/rag/feedback/resumo").status_code == 200


def test_com_chaves_so_entra_quem_manda_uma_valida(cliente, monkeypatch):
    monkeypatch.setattr(settings, "API_KEYS", "chave-a, chave-b")

    sem = cliente.get("/rag/feedback/resumo")
    errada = cliente.get("/rag/feedback/resumo", headers={"X-API-Key": "chave-c"})
    certa = cliente.get("/rag/feedback/resumo", headers={"X-API-Key": "chave-b"})

    assert (sem.status_code, errada.status_code, certa.status_code) == (401, 401, 200)
    assert sem.headers["www-authenticate"] == "ApiKey"


def test_listar_documentos_continua_publico(cliente, monkeypatch):
    monkeypatch.setattr(settings, "API_KEYS", "chave-a")
    assert cliente.get("/rag/documents").status_code == 200


def test_passou_do_limite_de_perguntas_da_429(cliente, monkeypatch):
    monkeypatch.setattr(settings, "RAG_LIMIAR_DISTANCIA", 1.5)
    monkeypatch.setattr(settings, "RATE_LIMIT_PERGUNTAS_POR_MINUTO", 2)
    monkeypatch.setattr(seguranca, "relogio", lambda: 600.0)  # o minuto não vira no meio
    enviar(cliente)

    codigos = [
        cliente.post("/rag/ask", json={"pergunta": f"Pergunta {i}?"}).status_code for i in range(3)
    ]

    assert codigos == [200, 200, 429]


# ---------- métricas e tempos por etapa


def test_ask_informa_o_tempo_de_cada_etapa(cliente, monkeypatch):
    monkeypatch.setattr(settings, "RAG_LIMIAR_DISTANCIA", 1.5)
    enviar(cliente)

    meta = cliente.post("/rag/ask", json={"pergunta": "Quando a chave é apagada?"}).json()["meta"]

    assert meta["tempo_busca_ms"] >= 0
    assert meta["tempo_llm_ms"] >= 0
    assert meta["tempo_primeiro_pedaco_ms"] is None  # só existe no streaming


def test_stream_informa_o_tempo_ate_o_primeiro_pedaco(cliente, monkeypatch):
    monkeypatch.setattr(settings, "RAG_LIMIAR_DISTANCIA", 1.5)
    enviar(cliente)

    eventos = ler_eventos(
        cliente.post("/rag/ask/stream", json={"pergunta": "Quando a chave é apagada?"}).text
    )

    assert eventos[-1][1]["meta"]["tempo_primeiro_pedaco_ms"] >= 0


def test_metrics_mostra_as_metricas_do_rag(cliente, monkeypatch):
    monkeypatch.setattr(settings, "RAG_LIMIAR_DISTANCIA", 1.5)
    enviar(cliente)
    cliente.post("/rag/ask", json={"pergunta": "Quando a chave é apagada?"})

    texto = cliente.get("/metrics").text

    assert "docassist_rag_respostas_total" in texto
    assert 'docassist_rag_etapa_segundos_bucket{etapa="busca"' in texto


# ---------- embedding fora do ar (ex.: API do Gemini sem rede)


def test_ask_com_embedding_fora_do_ar_da_503(cliente):
    enviar(cliente)
    app.dependency_overrides[obter_embedder_rag] = lambda: EmbedderForaDoAr()

    resposta = cliente.post("/rag/ask", json={"pergunta": "Quando a chave é apagada?"})

    assert resposta.status_code == 503
    assert "indisponível" in resposta.json()["detail"]


def test_stream_com_embedding_fora_do_ar_manda_evento_de_erro(cliente):
    enviar(cliente)
    app.dependency_overrides[obter_embedder_rag] = lambda: EmbedderForaDoAr()

    eventos = ler_eventos(
        cliente.post("/rag/ask/stream", json={"pergunta": "Quando a chave é apagada?"}).text
    )

    assert [nome for nome, _ in eventos] == ["erro"]
    assert "indisponível" in eventos[0][1]["detalhe"]


def test_search_com_embedding_fora_do_ar_da_503(cliente):
    enviar(cliente)
    app.dependency_overrides[obter_embedder_rag] = lambda: EmbedderForaDoAr()
    assert cliente.post("/rag/search", json={"query": "timeout"}).status_code == 503
