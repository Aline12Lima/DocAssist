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

    def gerar_em_partes(self, mensagens, max_tokens, temperatura):
        """A mesma resposta, entregue em pedaços de 4 caracteres (como num streaming)."""
        texto = self.gerar(mensagens, max_tokens, temperatura).texto
        self.ultimo_modelo = "falso:modelo"
        for inicio in range(0, len(texto), 4):
            yield texto[inicio : inicio + 4]


class LLMQueFalha(LLMFalso):
    def __init__(self):
        super().__init__(ErroDoProvedor("todos falharam"))


class RerankerFalso:
    """Dá a cada trecho a nota do dicionário (por id); os que não estão lá ganham `padrao`."""

    nome = "falso:reranker"

    def __init__(self, notas: dict | None = None, padrao: float = 5.0):
        self.notas = notas or {}
        self.padrao = padrao
        self.ultimo_tempo_ms = 0.0
        self.candidatos_recebidos = 0

    def reordenar(self, consulta, resultados, k=5):
        self.ultimo_tempo_ms = 1.0
        self.candidatos_recebidos = len(resultados)
        pontuados = [
            {**r, "pontuacao_reranker": self.notas.get(r["id"], self.padrao)} for r in resultados
        ]
        pontuados.sort(key=lambda r: r["pontuacao_reranker"], reverse=True)
        return pontuados[:k]


class RedisFalso:
    """Imita o que usamos do Redis: get, setex, incr e expire (sem expirar de verdade)."""

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

    def expire(self, chave, segundos):
        self.ttls[chave] = segundos
        return True


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


class EmbedderForaDoAr(EmbedderFalso):
    """Indexa normalmente, mas falha ao vetorizar a pergunta (como a API do Gemini fora do ar)."""

    def vetorizar_consulta(self, texto):
        from app.services.llm.base import ErroDoProvedor

        raise ErroDoProvedor("gemini-embedding: falha de conexão (Network is unreachable)")
