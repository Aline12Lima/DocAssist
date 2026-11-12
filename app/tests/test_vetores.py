"""Testes das coleções com um Chroma em memória e vetores escolhidos à mão."""

import chromadb
import pytest
from chromadb.config import Settings as ChromaSettings

from app.services.rag.vetores import buscar, nome_da_colecao, obter_colecao


@pytest.fixture
def cliente():
    cliente = chromadb.EphemeralClient(ChromaSettings(anonymized_telemetry=False))
    yield cliente
    for colecao in cliente.list_collections():
        cliente.delete_collection(colecao.name)


class EmbedderFixo:
    """A consulta vira sempre o vetor [1, 0, 0]."""

    def vetorizar_consulta(self, texto):
        return [1.0, 0.0, 0.0]


def adicionar_tres(colecao):
    colecao.upsert(
        ids=["perto", "meio", "longe"],
        embeddings=[[1.0, 0.1, 0.0], [1.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
        documents=["trecho perto", "trecho meio", "trecho longe"],
        metadatas=[{"doc_id": "a"}, {"doc_id": "b"}, {"doc_id": "a"}],
    )


def test_nome_da_colecao_inclui_o_modelo():
    assert nome_da_colecao("e5small") == "docs_e5small_v1"


def test_colecao_usa_cosseno_e_busca_exata(cliente):
    colecao = obter_colecao("docs_teste_v1", cliente=cliente)

    assert colecao.metadata["hnsw:space"] == "cosine"
    assert colecao.metadata["hnsw:search_ef"] >= 100


def test_buscar_ordena_do_mais_parecido_para_o_menos(cliente):
    colecao = obter_colecao("docs_teste_v1", cliente=cliente)
    adicionar_tres(colecao)

    resultados = buscar("qualquer", colecao, EmbedderFixo(), k=3)

    assert [r["id"] for r in resultados] == ["perto", "meio", "longe"]
    assert resultados[0]["distancia"] < resultados[1]["distancia"] < resultados[2]["distancia"]
    assert resultados[2]["distancia"] == pytest.approx(1.0)  # ortogonal: cosseno 0


def test_buscar_com_filtro_por_documento(cliente):
    colecao = obter_colecao("docs_teste_v1", cliente=cliente)
    adicionar_tres(colecao)

    resultados = buscar("qualquer", colecao, EmbedderFixo(), k=3, filtros={"doc_id": "a"})

    assert [r["id"] for r in resultados] == ["perto", "longe"]


def test_recriar_apaga_o_conteudo(cliente):
    adicionar_tres(obter_colecao("docs_teste_v1", cliente=cliente))

    colecao = obter_colecao("docs_teste_v1", recriar=True, cliente=cliente)

    assert colecao.count() == 0
