"""Reranker: reordena os candidatos lendo a pergunta e o trecho JUNTOS.

A busca vetorial (bi-encoder) transforma pergunta e trecho em vetores SEPARADOS e
compara os vetores. É rápido, mas a pergunta nunca "vê" o trecho.

O cross-encoder recebe o par (pergunta, trecho) de uma vez e devolve uma nota de
relevância. É bem mais preciso, mas lento demais para os 226 trechos a cada
pergunta. Por isso o uso em duas etapas:
    1. a busca rápida escolhe ~30 candidatos;
    2. o cross-encoder dá nota a esses 30 e reordena.

O modelo padrão foi treinado no mMARCO (MS MARCO traduzido para vários idiomas,
incluindo português), então funciona com pergunta em português e trecho em inglês.
"""

import time

MODELO_PADRAO = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"


def quantizar(modelo_torch):
    """Quantização dinâmica para int8 (Fase 9.5, experimento E6).

    Os pesos das camadas Linear (quase todo o cálculo de um transformer) passam de
    float32 (4 bytes por número) para int8 (1 byte). A conta fica mais barata na CPU,
    em troca de um pouco de precisão. "Dinâmica" porque a escala das ativações é
    calculada na hora, sem precisar de dados de calibração.
    """
    import torch

    return torch.quantization.quantize_dynamic(modelo_torch, {torch.nn.Linear}, dtype=torch.qint8)


class Reranker:
    def __init__(
        self,
        nome: str = MODELO_PADRAO,
        modelo=None,
        max_tokens: int = 512,
        quantizado: bool = False,
    ):
        self.modelo_base = nome
        self.quantizado = quantizado
        # o nome vai para o meta e para a chave do cache: int8 e float32 não se misturam
        self.nome = f"{nome}:int8" if quantizado else nome
        self.max_tokens = max_tokens
        self._modelo = modelo  # nos testes, um modelo falso entra aqui
        self._pronto = False
        self.ultimo_tempo_ms = 0.0

    @property
    def modelo(self):
        if self._modelo is None:
            from sentence_transformers import CrossEncoder  # carrega só quando usar

            self._modelo = CrossEncoder(self.modelo_base, max_length=self.max_tokens)
        if not self._pronto:
            if self.quantizado and hasattr(self._modelo, "model"):
                self._modelo.model = quantizar(self._modelo.model)
            self._pronto = True
        return self._modelo

    def reordenar(self, consulta: str, resultados: list[dict], k: int = 5) -> list[dict]:
        """Dá uma nota a cada (pergunta, trecho) e devolve os k de nota mais alta."""
        if not resultados:
            self.ultimo_tempo_ms = 0.0
            return []
        inicio = time.perf_counter()
        pares = [(consulta, r["texto"]) for r in resultados]
        notas = self.modelo.predict(pares, batch_size=32, show_progress_bar=False)
        self.ultimo_tempo_ms = (time.perf_counter() - inicio) * 1000
        pontuados = [
            {**r, "pontuacao_reranker": float(nota)}
            for r, nota in zip(resultados, notas, strict=True)
        ]
        pontuados.sort(key=lambda r: r["pontuacao_reranker"], reverse=True)
        return pontuados[:k]


_rerankers: dict[tuple[str, bool], Reranker] = {}


def obter_reranker(nome: str = MODELO_PADRAO, quantizado: bool | None = None) -> Reranker:
    """Devolve o Reranker do modelo, carregado uma vez só.

    Sem dizer `quantizado`, segue o .env (RAG_RERANKER_QUANTIZADO).
    """
    if quantizado is None:
        from app.config import settings

        quantizado = settings.RAG_RERANKER_QUANTIZADO
    chave = (nome, quantizado)
    if chave not in _rerankers:
        _rerankers[chave] = Reranker(nome, quantizado=quantizado)
    return _rerankers[chave]
