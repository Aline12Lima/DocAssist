"""Ingestão: arquivo -> seções -> chunks -> embeddings -> Chroma, sem duplicar.

- O ID de cada chunk é calculado a partir do documento e da posição (sha1), então
  ingerir o mesmo arquivo de novo substitui os chunks em vez de duplicar.
- Chunks que deixaram de existir (o documento ficou menor) são apagados.
- Chunks cujo texto não mudou não passam pelo modelo de novo.
"""

import hashlib
from dataclasses import dataclass
from pathlib import Path

from app.services.rag.chunker import Chunk, gerar_chunks
from app.services.rag.parsers import parse_arquivo

CAMPOS_DO_DOCUMENTO = ("titulo", "fonte", "url", "idioma", "versao", "licenca")


@dataclass
class ResultadoIngestao:
    doc_id: str
    chunks: int
    gerados: int  # chunks novos ou alterados, que passaram pelo modelo
    removidos: int


def gerar_chunk_id(doc_id: str, posicao: int) -> str:
    return hashlib.sha1(f"{doc_id}:{posicao}".encode()).hexdigest()


def gerar_hash(texto: str) -> str:
    return hashlib.sha1(texto.encode("utf-8")).hexdigest()


def montar_metadados(doc_id: str, chunk: Chunk, hash_conteudo: str, documento: dict) -> dict:
    """O Chroma só aceita str, int, float e bool nos metadados: nada de None ou listas."""
    metadados = {
        "doc_id": doc_id,
        "secao": " › ".join(chunk.caminho),
        "posicao": chunk.posicao,
        "tem_codigo": chunk.tem_codigo,
        "hash_conteudo": hash_conteudo,
    }
    if chunk.pagina is not None:
        metadados["pagina"] = chunk.pagina
    for campo in CAMPOS_DO_DOCUMENTO:
        if documento.get(campo) is not None:
            metadados[campo] = str(documento[campo])
    return metadados


def ingerir_arquivo(
    caminho: Path,
    doc_id: str,
    colecao,
    embedder,
    documento: dict | None = None,
    limite: int = 250,
    overlap: int = 30,
    minimo: int = 50,
) -> ResultadoIngestao:
    """Ingere um arquivo na coleção. O `embedder` gera os vetores e conta os tokens."""
    documento = documento or {}
    secoes = parse_arquivo(caminho, documento.get("titulo"))
    chunks = gerar_chunks(secoes, embedder.contar_tokens, limite, overlap, minimo)
    ids = [gerar_chunk_id(doc_id, chunk.posicao) for chunk in chunks]
    hashes = [gerar_hash(chunk.texto) for chunk in chunks]

    # O que já existe deste documento na coleção
    existentes = colecao.get(where={"doc_id": doc_id}, include=["metadatas"])
    hash_existente = {
        chunk_id: (metadados or {}).get("hash_conteudo")
        for chunk_id, metadados in zip(existentes["ids"], existentes["metadatas"], strict=False)
    }

    # 1. Apagar os chunks que não existem mais
    ids_atuais = set(ids)
    obsoletos = [chunk_id for chunk_id in hash_existente if chunk_id not in ids_atuais]
    if obsoletos:
        colecao.delete(ids=obsoletos)

    # 2. Gerar embedding só do que é novo ou mudou
    alterados = [
        i
        for i, (cid, h) in enumerate(zip(ids, hashes, strict=True))
        if hash_existente.get(cid) != h
    ]
    if alterados:
        textos = [chunks[i].texto for i in alterados]
        vetores = embedder.vetorizar_trechos(textos)
        colecao.upsert(
            ids=[ids[i] for i in alterados],
            embeddings=vetores,
            documents=textos,
            metadatas=[
                montar_metadados(doc_id, chunks[i], hashes[i], documento) for i in alterados
            ],
        )

    return ResultadoIngestao(doc_id, len(chunks), len(alterados), len(obsoletos))
