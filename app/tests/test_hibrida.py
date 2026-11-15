"""Testes do BM25, do RRF e da busca híbrida (Chroma em memória, sem rede)."""

import chromadb
import pytest
from chromadb.config import Settings as ChromaSettings

from app.services.rag.hibrida import buscar_hibrido, fundir_rrf
from app.services.rag.lexical import IndiceBM25, passa_no_filtro, tokenizar
from app.services.rag.vetores import obter_colecao
from app.tests.fakes import EmbedderFalso

TEXTOS = [
    "EXPIRE › Optional arguments XX Set the expiry only when the key already has an expiry",
    "EXPIRE › Optional arguments NX Set the expiry only when the key has no expiry",
    "TTL Returns the remaining time to live of a key that has a timeout",
    "Networking Each service registers its name with an internal DNS server",
]
METADADOS = [
    {"doc_id": "redis-expire", "fonte": "redis"},
    {"doc_id": "redis-expire", "fonte": "redis"},
    {"doc_id": "redis-ttl", "fonte": "redis"},
    {"doc_id": "docker-compose-networking", "fonte": "docker"},
]
IDS = ["xx", "nx", "ttl", "rede"]


@pytest.fixture
def indice():
    return IndiceBM25(IDS, TEXTOS, METADADOS)


def test_tokenizar_tira_acentos_stopwords_e_pontuacao():
    assert tokenizar("Como a opção XX funciona no EXPIRE?") == ["opcao", "xx", "funciona", "expire"]


def test_tokenizar_mantem_underscore_e_numeros():
    assert tokenizar("service_healthy na porta 5432") == ["service_healthy", "porta", "5432"]


def test_bm25_poe_o_termo_raro_em_primeiro(indice):
    resultados = indice.buscar("O que faz a opção XX do EXPIRE?", k=2)
    assert resultados[0]["id"] == "xx"
    assert resultados[0]["distancia"] is None
    assert resultados[0]["pontuacao_bm25"] > resultados[1]["pontuacao_bm25"]


def test_bm25_ignora_trechos_sem_palavra_em_comum(indice):
    assert indice.buscar("kubernetes ingress", k=5) == []


def test_bm25_respeita_filtros(indice):
    resultados = indice.buscar("expiry key", k=5, filtros={"doc_id": "redis-ttl"})
    assert [r["id"] for r in resultados] == ["ttl"]


def test_filtro_com_and():
    meta = {"doc_id": "a", "fonte": "redis"}
    assert passa_no_filtro(meta, {"$and": [{"doc_id": "a"}, {"fonte": "redis"}]})
    assert not passa_no_filtro(meta, {"$and": [{"doc_id": "a"}, {"fonte": "docker"}]})
    assert passa_no_filtro(meta, None)


def test_rrf_premia_quem_aparece_nas_duas_listas():
    vetorial = [{"id": "a", "distancia": 0.1}, {"id": "b", "distancia": 0.2}]
    lexical = [{"id": "b", "distancia": None, "pontuacao_bm25": 3.0}, {"id": "c"}]
    fundidos = fundir_rrf([vetorial, lexical])
    assert [r["id"] for r in fundidos] == ["b", "a", "c"]
    assert fundidos[0]["distancia"] == 0.2  # veio do vetorial
    assert fundidos[0]["pontuacao_bm25"] == 3.0  # veio do BM25
    assert fundidos[0]["nota_rrf"] == pytest.approx(1 / 62 + 1 / 61)


def test_busca_hibrida_com_chroma_em_memoria():
    cliente = chromadb.EphemeralClient(ChromaSettings(anonymized_telemetry=False))
    try:
        colecao = obter_colecao("teste_hibrida", cliente=cliente)
        embedder = EmbedderFalso()
        colecao.upsert(
            ids=IDS,
            embeddings=embedder.vetorizar_trechos(TEXTOS),
            documents=TEXTOS,
            metadatas=METADADOS,
        )
        indice = IndiceBM25.da_colecao(colecao)
        assert len(indice.ids) == 4

        resultados = buscar_hibrido("opção XX do EXPIRE", colecao, embedder, indice, k=2)
        assert resultados[0]["id"] == "xx"
        assert len(resultados) == 2
        assert all("nota_rrf" in r for r in resultados)
    finally:
        cliente.delete_collection("teste_hibrida")
