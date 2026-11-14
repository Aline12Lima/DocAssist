"""Testes do reranker com um cross-encoder falso (sem baixar modelo)."""

from app.services.rag.reranker import Reranker


class CrossEncoderFalso:
    """Nota = quantas palavras da pergunta aparecem no trecho."""

    def __init__(self):
        self.chamadas = 0

    def predict(self, pares, batch_size=32, show_progress_bar=False):
        self.chamadas += 1
        return [
            float(sum(p in trecho.lower().split() for p in pergunta.lower().split()))
            for pergunta, trecho in pares
        ]


def candidatos():
    return [
        {"id": "a", "texto": "redis persistence rdb snapshots", "distancia": 0.10},
        {"id": "b", "texto": "expire sets a timeout on key", "distancia": 0.15},
        {"id": "c", "texto": "the key expire timeout is deleted", "distancia": 0.20},
    ]


def test_reordena_pela_nota_e_corta_em_k():
    reranker = Reranker(modelo=CrossEncoderFalso())
    resultado = reranker.reordenar("key expire timeout deleted", candidatos(), k=2)
    assert [r["id"] for r in resultado] == ["c", "b"]
    assert resultado[0]["pontuacao_reranker"] == 4.0
    assert resultado[0]["distancia"] == 0.20  # o resto do resultado é mantido


def test_lista_vazia_nao_chama_o_modelo():
    modelo = CrossEncoderFalso()
    reranker = Reranker(modelo=modelo)
    assert reranker.reordenar("qualquer coisa", [], k=5) == []
    assert modelo.chamadas == 0


def test_mede_o_tempo_da_ultima_chamada():
    reranker = Reranker(modelo=CrossEncoderFalso())
    reranker.reordenar("expire", candidatos(), k=1)
    assert reranker.ultimo_tempo_ms >= 0.0
