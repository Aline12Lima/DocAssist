"""Testes da ingestão com uma coleção e um embedder falsos (sem Chroma e sem modelo)."""

from pathlib import Path

import numpy as np

from app.services.rag.ingest import gerar_chunk_id, ingerir_arquivo


class ColecaoFalsa:
    """Imita o que a ingestão usa do Chroma: get, upsert e delete."""

    def __init__(self):
        self.registros: dict[str, dict] = {}

    def get(self, where=None, include=None):
        ids = [i for i, r in self.registros.items() if r["metadata"]["doc_id"] == where["doc_id"]]
        return {"ids": ids, "metadatas": [self.registros[i]["metadata"] for i in ids]}

    def upsert(self, ids, embeddings, documents, metadatas):
        for i, vetor, texto, meta in zip(ids, embeddings, documents, metadatas, strict=True):
            self.registros[i] = {"vetor": vetor, "texto": texto, "metadata": meta}

    def delete(self, ids):
        for i in ids:
            del self.registros[i]


class EmbedderFalso:
    """Imita o Embedder: conta palavras como tokens e devolve vetores de zeros."""

    def __init__(self):
        self.textos_processados = 0

    def contar_tokens(self, texto: str) -> int:
        return len(texto.split())

    def vetorizar_trechos(self, textos):
        self.textos_processados += len(textos)
        return np.zeros((len(textos), 3)).tolist()


def escrever(tmp_path: Path, secoes: int) -> Path:
    arquivo = tmp_path / "doc.md"
    corpo = "\n\n".join(f"## Seção {i}\n\n" + " ".join(["palavra"] * 30) for i in range(secoes))
    arquivo.write_text(f"# Documento\n\n{corpo}", encoding="utf-8")
    return arquivo


def ingerir(arquivo, colecao, embedder):
    return ingerir_arquivo(
        arquivo, "doc-teste", colecao, embedder, {"titulo": "Documento"}, limite=60
    )


def test_ingerir_duas_vezes_nao_duplica(tmp_path):
    colecao, embedder = ColecaoFalsa(), EmbedderFalso()
    arquivo = escrever(tmp_path, secoes=4)

    primeira = ingerir(arquivo, colecao, embedder)
    segunda = ingerir(arquivo, colecao, embedder)

    assert len(colecao.registros) == primeira.chunks == segunda.chunks
    assert segunda.gerados == 0  # nada mudou: o modelo nem foi chamado de novo
    assert embedder.textos_processados == primeira.chunks


def test_documento_menor_apaga_chunks_que_sobraram(tmp_path):
    colecao, embedder = ColecaoFalsa(), EmbedderFalso()
    ingerir(escrever(tmp_path, secoes=5), colecao, embedder)

    resultado = ingerir(escrever(tmp_path, secoes=2), colecao, embedder)

    assert resultado.removidos > 0
    assert len(colecao.registros) == resultado.chunks


def test_ids_sao_deterministicos():
    assert gerar_chunk_id("redis-ttl", 3) == gerar_chunk_id("redis-ttl", 3)
    assert gerar_chunk_id("redis-ttl", 3) != gerar_chunk_id("redis-ttl", 4)


def test_metadados_nao_tem_valores_nulos(tmp_path):
    colecao, embedder = ColecaoFalsa(), EmbedderFalso()
    ingerir(escrever(tmp_path, secoes=2), colecao, embedder)

    for registro in colecao.registros.values():
        meta = registro["metadata"]
        assert meta["doc_id"] == "doc-teste"
        assert meta["titulo"] == "Documento"
        assert "pagina" not in meta  # Markdown não tem página: o campo nem aparece
        assert all(v is not None for v in meta.values())
