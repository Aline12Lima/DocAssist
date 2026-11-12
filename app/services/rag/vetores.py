"""Coleções do Chroma para o RAG: uma por modelo, com distância cosseno e busca exata.

- Vetores de modelos diferentes não podem ser comparados: cada modelo tem a sua coleção.
- hnsw:search_ef alto faz o índice examinar candidatos suficientes. Num corpus pequeno, a
  busca fica praticamente exata e não varia entre execuções (o problema visto no E1).
"""

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import settings

CONFIG_HNSW = {
    "hnsw:space": "cosine",
    "hnsw:construction_ef": 200,
    "hnsw:search_ef": 200,
}

_cliente = None


def obter_cliente():
    global _cliente
    if _cliente is None:
        _cliente = chromadb.PersistentClient(
            path=settings.CHROMA_PATH,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _cliente


def nome_da_colecao(apelido_modelo: str, versao: str = "v1") -> str:
    return f"docs_{apelido_modelo}_{versao}"


def obter_colecao(nome: str, recriar: bool = False, cliente=None):
    """Abre (ou cria) a coleção. Com recriar=True, apaga tudo e começa do zero."""
    cliente = cliente or obter_cliente()
    if recriar:
        try:
            cliente.delete_collection(nome)
        except ValueError:
            pass  # a coleção ainda não existia
    return cliente.get_or_create_collection(nome, metadata=CONFIG_HNSW)


def buscar(consulta: str, colecao, embedder, k: int = 5, filtros: dict | None = None) -> list[dict]:
    """Busca os k trechos mais próximos da consulta. Distância cosseno: menor = mais parecido."""
    resposta = colecao.query(
        query_embeddings=[embedder.vetorizar_consulta(consulta)],
        n_results=k,
        where=filtros or None,
        include=["documents", "metadatas", "distances"],
    )
    return [
        {"id": i, "texto": texto, "metadados": meta or {}, "distancia": distancia}
        for i, texto, meta, distancia in zip(
            resposta["ids"][0],
            resposta["documents"][0],
            resposta["metadatas"][0],
            resposta["distances"][0],
            strict=True,
        )
    ]
