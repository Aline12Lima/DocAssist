"""Peças falsas compartilhadas pelos testes: um embedder e um LLM que não precisam de rede."""

import hashlib

import numpy as np

from app.services.llm.base import ErroDoProvedor, RespostaLLM
from app.services.rag.embeddings import MODELOS


class EmbedderFalso:
    """Vetor = contagem de palavras em 32 posições. Textos com palavras em comum ficam perto."""

    config = MODELOS["e5small"]

    def _vetor(self, texto: str) -> list[float]:
        vetor = np.zeros(32)
        for palavra in texto.lower().split():
            vetor[int(hashlib.md5(palavra.encode()).hexdigest(), 16) % 32] += 1
        norma = np.linalg.norm(vetor)
        return (vetor / norma if norma else vetor).tolist()

    def contar_tokens(self, texto: str) -> int:
        return len(texto.split())

    def vetorizar_trechos(self, textos):
        return [self._vetor(t) for t in textos]

    def vetorizar_consulta(self, texto):
        return self._vetor(texto)


class LLMFalso:
    """Devolve as respostas da lista, uma por chamada. Um item Exception é lançado."""

    def __init__(self, *respostas):
        self.respostas = list(respostas)
        self.mensagens_recebidas = []

    def gerar(self, mensagens, max_tokens, temperatura):
        self.mensagens_recebidas.append(mensagens)
        resposta = self.respostas.pop(0)
        if isinstance(resposta, Exception):
            raise resposta
        return RespostaLLM(resposta, "falso:modelo", 100, 20)


class LLMQueFalha(LLMFalso):
    def __init__(self):
        super().__init__(ErroDoProvedor("todos falharam"))


class RedisFalso:
    """Imita o que o cache usa do Redis: get, setex e incr (sem expirar de verdade)."""

    def __init__(self):
        self.dados: dict[str, str] = {}
        self.ttls: dict[str, int] = {}

    def get(self, chave):
        return self.dados.get(chave)

    def setex(self, chave, ttl, valor):
        self.dados[chave] = valor
        self.ttls[chave] = ttl

    def incr(self, chave):
        self.dados[chave] = str(int(self.dados.get(chave, 0)) + 1)
        return int(self.dados[chave])


class RedisForaDoAr:
    def __getattr__(self, nome):
        import redis

        def falhar(*args, **kwargs):
            raise redis.ConnectionError("Redis fora do ar")

        return falhar


def sessao_de_teste():
    """Um banco SQLite em memória com todas as tabelas, para um teste só."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from app.database.connection import Base

    motor = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(motor)
    return sessionmaker(bind=motor)()
