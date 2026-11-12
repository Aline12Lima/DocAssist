"""Testes do Embedder com um modelo falso: conferem os prefixos e a normalização."""

import numpy as np
import pytest

from app.services.rag.embeddings import MODELOS, Embedder, obter_embedder


class TokenizadorFalso:
    def encode(self, texto, add_special_tokens=True, verbose=True):
        return texto.split()


class ModeloFalso:
    """Guarda o que recebeu, para o teste conferir os prefixos."""

    def __init__(self):
        self.recebido = []
        self.normalizado = []
        self.tokenizer = TokenizadorFalso()

    def encode(self, textos, batch_size=32, normalize_embeddings=False):
        self.recebido.append(textos)
        self.normalizado.append(normalize_embeddings)
        if isinstance(textos, str):
            return np.ones(3)
        return np.ones((len(textos), 3))


def test_e5_usa_prefixo_passage_nos_trechos():
    modelo = ModeloFalso()
    embedder = Embedder(MODELOS["e5small"], modelo)

    embedder.vetorizar_trechos(["Compose does not wait"])

    assert modelo.recebido[0] == ["passage: Compose does not wait"]


def test_e5_usa_prefixo_query_na_consulta():
    modelo = ModeloFalso()
    embedder = Embedder(MODELOS["e5small"], modelo)

    embedder.vetorizar_consulta("como subir containers")

    assert modelo.recebido[0] == "query: como subir containers"


def test_minilm_nao_usa_prefixo():
    modelo = ModeloFalso()
    embedder = Embedder(MODELOS["minilm"], modelo)

    embedder.vetorizar_trechos(["texto"])
    embedder.vetorizar_consulta("pergunta")

    assert modelo.recebido == [["texto"], "pergunta"]


def test_vetores_sempre_normalizados_e_em_lista():
    modelo = ModeloFalso()
    embedder = Embedder(MODELOS["e5small"], modelo)

    trechos = embedder.vetorizar_trechos(["a", "b"])
    consulta = embedder.vetorizar_consulta("c")

    assert modelo.normalizado == [True, True]
    assert trechos == [[1.0, 1.0, 1.0], [1.0, 1.0, 1.0]]
    assert consulta == [1.0, 1.0, 1.0]


def test_contar_tokens_nao_inclui_o_prefixo():
    embedder = Embedder(MODELOS["e5small"], ModeloFalso())

    assert embedder.contar_tokens("três palavras aqui") == 3


def test_modelo_desconhecido_e_recusado():
    with pytest.raises(ValueError):
        obter_embedder("gpt-qualquer")
