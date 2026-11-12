"""O que todo provedor de LLM precisa oferecer, e os erros que ele pode devolver."""

from dataclasses import dataclass
from typing import Protocol


@dataclass
class RespostaLLM:
    texto: str
    modelo: str  # "provedor:modelo" que de fato respondeu
    tokens_entrada: int
    tokens_saida: int


class ErroDoProvedor(Exception):
    """O provedor falhou (fora do ar, resposta inválida, chave errada...)."""


class ErroDeLimite(ErroDoProvedor):
    """O provedor recusou por limite de uso (HTTP 429). Vale tentar o próximo."""


class LLMProvider(Protocol):
    nome: str

    def gerar(self, mensagens: list[dict], max_tokens: int, temperatura: float) -> RespostaLLM: ...
