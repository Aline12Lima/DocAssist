"""Carrega todos os documentos do manifesto na coleção principal do RAG.

Uso:
    python -m scripts.ingerir_corpus      (ou: make ingest)

Pode rodar quantas vezes quiser: os IDs são determinísticos, então nada é duplicado,
e o que não mudou nem passa pelo modelo de novo.
"""

from pathlib import Path

import yaml

from app.config import settings
from app.services.rag.cache import invalidar
from app.services.rag.documentos import colecao_principal, embedder_principal
from app.services.rag.ingest import ingerir_arquivo
from app.services.redis_service import get_redis_client

MANIFESTO = Path("corpus/manifest.yaml")


def main():
    colecao = colecao_principal()
    embedder = embedder_principal()
    documentos = yaml.safe_load(MANIFESTO.read_text(encoding="utf-8"))

    print(f"Coleção: {colecao.name} | modelo: {embedder.config.nome}\n")
    houve_mudanca = False
    for doc in documentos:
        resultado = ingerir_arquivo(
            Path(doc["arquivo"]),
            doc["id"],
            colecao,
            embedder,
            doc,
            settings.RAG_CHUNK_LIMITE,
            settings.RAG_CHUNK_OVERLAP,
            settings.RAG_CHUNK_MINIMO,
        )
        houve_mudanca = houve_mudanca or bool(resultado.gerados or resultado.removidos)
        print(
            f"{doc['id']:34} {resultado.chunks:3} chunks "
            f"({resultado.gerados} gerados, {resultado.removidos} removidos)"
        )
    print(f"\nTotal na coleção: {colecao.count()} chunks")
    if houve_mudanca:
        try:
            invalidar(get_redis_client())
            print("A base mudou: o cache de respostas foi invalidado.")
        except Exception as erro:  # noqa: BLE001 - sem Redis, não há cache para invalidar
            print(f"Redis indisponível ({erro}); nada a invalidar.")


if __name__ == "__main__":
    main()
