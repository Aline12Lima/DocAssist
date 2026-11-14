"""Testes dos endpoints do RAG com um Chroma em memória e um modelo falso."""

import chromadb
import pytest
from chromadb.config import Settings as ChromaSettings
from fastapi.testclient import TestClient

from app.config import settings
from app.database.connection import get_db
from app.main import app
from app.routers.rag import obter_colecao_rag, obter_embedder_rag, obter_llm_rag, obter_redis_rag
from app.services.rag.vetores import obter_colecao
from app.tests.fakes import EmbedderFalso, LLMFalso, LLMQueFalha, RedisFalso, sessao_de_teste

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
