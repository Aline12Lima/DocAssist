"""Carrega todos os documentos do manifesto na coleção principal do RAG.

Uso:
    python -m scripts.ingerir_corpus      (ou: make ingest)

Pode rodar quantas vezes quiser: os IDs são determinísticos, então nada é duplicado,
e o que não mudou nem passa pelo modelo de novo.
"""

from pathlib import Path

import yaml

from app.config import settings
from app.services.rag.documentos import colecao_principal, embedder_principal
from app.services.rag.ingest import ingerir_arquivo

MANIFESTO = Path("corpus/manifest.yaml")


def main():
    colecao = colecao_principal()
    embedder = embedder_principal()
    documentos = yaml.safe_load(MANIFESTO.read_text(encoding="utf-8"))

    print(f"Coleção: {colecao.name} | modelo: {embedder.config.nome}\n")
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
        print(
            f"{doc['id']:34} {resultado.chunks:3} chunks "
            f"({resultado.gerados} gerados, {resultado.removidos} removidos)"
        )
    print(f"\nTotal na coleção: {colecao.count()} chunks")


if __name__ == "__main__":
    main()
