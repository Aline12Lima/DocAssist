"""Operações sobre os documentos da coleção principal do RAG (usadas pela API)."""

import hashlib
import re
import tempfile
import unicodedata
from pathlib import Path

from app.config import settings
from app.services.rag.embeddings import MODELOS, obter_embedder
from app.services.rag.ingest import ResultadoIngestao, ingerir_arquivo
from app.services.rag.vetores import nome_da_colecao, obter_colecao

EXTENSOES_ACEITAS = {".md", ".markdown", ".html", ".htm", ".pdf"}


def embedder_principal():
    return obter_embedder(settings.RAG_EMBEDDING_MODEL)


def colecao_principal():
    apelido = MODELOS[settings.RAG_EMBEDDING_MODEL].apelido
    return obter_colecao(nome_da_colecao(apelido))


def gerar_doc_id(nome_arquivo: str) -> str:
    """'Guia Rápido.md' -> 'guia-rapido'."""
    base = unicodedata.normalize("NFKD", Path(nome_arquivo).stem)
    base = base.encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", base).strip("-") or "documento"


def doc_id_de_texto(texto: str) -> str:
    """O mesmo texto gera sempre o mesmo ID: reenviar não duplica."""
    return "texto-" + hashlib.sha1(texto.encode("utf-8")).hexdigest()[:12]


def ingerir_conteudo(
    conteudo: bytes, extensao: str, doc_id: str, colecao, embedder, documento: dict
) -> ResultadoIngestao:
    """Salva o conteúdo num arquivo temporário e passa pela ingestão normal."""
    with tempfile.TemporaryDirectory() as pasta:
        caminho = Path(pasta) / f"documento{extensao}"
        caminho.write_bytes(conteudo)
        return ingerir_arquivo(
            caminho,
            doc_id,
            colecao,
            embedder,
            documento,
            settings.RAG_CHUNK_LIMITE,
            settings.RAG_CHUNK_OVERLAP,
            settings.RAG_CHUNK_MINIMO,
        )


def listar_documentos(colecao) -> list[dict]:
    """Agrupa os chunks por documento."""
    documentos: dict[str, dict] = {}
    for metadados in colecao.get(include=["metadatas"])["metadatas"]:
        metadados = metadados or {}
        doc_id = metadados.get("doc_id", "?")
        info = documentos.setdefault(
            doc_id,
            {
                "doc_id": doc_id,
                "titulo": metadados.get("titulo"),
                "fonte": metadados.get("fonte"),
                "chunks": 0,
            },
        )
        info["chunks"] += 1
    return sorted(documentos.values(), key=lambda d: d["doc_id"])


def remover_documento(colecao, doc_id: str) -> int:
    ids = colecao.get(where={"doc_id": doc_id})["ids"]
    if ids:
        colecao.delete(ids=ids)
    return len(ids)
