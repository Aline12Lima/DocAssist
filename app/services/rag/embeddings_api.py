"""Embeddings por API (Gemini): o mesmo papel do Embedder, sem PyTorch na máquina.

Para o deploy gratuito (Fase 9.6): o plano grátis da Railway dá 0,5 GB de RAM por
serviço, e o PyTorch com os modelos locais passa de 1,5 GB. Trocando o modelo local por
uma API, a aplicação cabe na memória; em troca, cada embedding vira uma chamada de rede.

Diferenças em relação ao e5:
- No lugar dos prefixos "query: " e "passage: ", o Gemini recebe um taskType:
  RETRIEVAL_QUERY para a pergunta e RETRIEVAL_DOCUMENT para os trechos.
- O vetor completo tem 3072 números; pedimos menos (outputDimensionality) para ocupar
  menos espaço. O vetor cortado não vem normalizado, então normalizamos aqui.
- Não há tokenizador local: o tamanho dos trechos é estimado (contar_tokens).
- O plano grátis tem limite de tokens por minuto (~30 mil): os lotes são pequenos e o
  próprio cliente espera para não passar do limite (LimiteDeTokens).
"""

import logging
import math
import re
import time

import httpx

from app.services.llm.base import ErroDeLimite, ErroDoProvedor

URL_GEMINI = "https://generativelanguage.googleapis.com/v1beta"
logger = logging.getLogger(__name__)


def normalizar(vetor: list[float]) -> list[float]:
    norma = math.sqrt(sum(x * x for x in vetor)) or 1.0
    return [x / norma for x in vetor]


def estimar_tokens(texto: str) -> int:
    """Estimativa sem tokenizador: palavras e sinais, com uma folga de 30%.

    Tokenizadores de subpalavras partem palavras longas ou raras em pedaços; a folga
    aproxima isso. É uma estimativa: serve para o chunker cortar trechos de tamanho
    parecido com os do e5, não para cobrar tokens.
    """
    return math.ceil(len(re.findall(r"\w+|[^\w\s]", texto)) * 1.3)


def espera_sugerida(corpo: str) -> float | None:
    """No 429, o Gemini costuma dizer quanto esperar: {"retryDelay": "38s"}."""
    achado = re.search(r'"retryDelay":\s*"(\d+(?:\.\d+)?)s"', corpo)
    return float(achado.group(1)) if achado else None


class LimiteDeTokens:
    """Limite de uso do lado do CLIENTE: não mandar mais que N tokens por minuto.

    É o espelho do limite que a nossa API aplica (Fase 9.4): lá recusamos quem passa
    do limite; aqui, nós esperamos antes de passar do limite de quem nos atende.
    Guarda (instante, tokens) dos envios do último minuto.
    """

    def __init__(self, por_minuto: int, relogio=time.monotonic, dormir=time.sleep):
        self.por_minuto = por_minuto
        self.relogio = relogio
        self.dormir = dormir
        self.envios: list[tuple[float, int]] = []

    def aguardar(self, tokens: int) -> None:
        while True:
            agora = self.relogio()
            self.envios = [(t, n) for t, n in self.envios if agora - t < 60]
            usados = sum(n for _, n in self.envios)
            if not self.envios or usados + tokens <= self.por_minuto:
                self.envios.append((agora, tokens))
                return
            # espera o envio mais antigo sair da janela de 60 s
            self.dormir(60 - (agora - self.envios[0][0]) + 0.1)


class EmbedderGemini:
    def __init__(
        self,
        config,
        chave: str,
        dimensoes: int = 768,
        lote: int = 50,
        tokens_por_minuto: int = 25_000,
        tokens_por_lote: int = 8_000,
        cliente_http: httpx.Client | None = None,
        tentativas: int = 5,
        espera_inicial: float = 5.0,
        dormir=time.sleep,
        relogio=time.monotonic,
    ):
        if not chave:
            raise ValueError("GEMINI_API_KEY vazio: o embedding pelo Gemini precisa da chave")
        self.config = config
        self.chave = chave
        self.dimensoes = dimensoes
        self.lote = lote
        self.tokens_por_lote = tokens_por_lote
        self.tentativas = tentativas
        self.espera_inicial = espera_inicial
        self.dormir = dormir
        self.limite = LimiteDeTokens(tokens_por_minuto, relogio=relogio, dormir=dormir)
        self._http = cliente_http or httpx.Client(timeout=30.0)

    def _pedido(self, texto: str, tipo: str) -> dict:
        return {
            "model": f"models/{self.config.nome}",
            "content": {"parts": [{"text": texto}]},
            "taskType": tipo,
            "outputDimensionality": self.dimensoes,
        }

    def _chamar(self, textos: list[str], tipo: str) -> list[list[float]]:
        """Um lote numa chamada só. No 429 (limite de uso), espera e tenta de novo."""
        self.limite.aguardar(sum(estimar_tokens(t) for t in textos))
        url = f"{URL_GEMINI}/models/{self.config.nome}:batchEmbedContents"
        corpo = {"requests": [self._pedido(t, tipo) for t in textos]}
        espera = self.espera_inicial
        for tentativa in range(self.tentativas):
            try:
                resposta = self._http.post(url, headers={"x-goog-api-key": self.chave}, json=corpo)
            except httpx.TransportError as erro:
                # falha de rede passageira (ex.: "Network is unreachable"): tenta de novo logo
                if tentativa == self.tentativas - 1:
                    raise ErroDoProvedor(f"gemini-embedding: falha de conexão ({erro})") from erro
                logger.warning("Embedding: falha de rede (%s), tentando de novo", erro)
                self.dormir(2**tentativa)  # 1 s, 2 s, 4 s...
                continue
            if resposta.status_code == 429:
                if tentativa == self.tentativas - 1:
                    raise ErroDeLimite(
                        f"gemini-embedding: limite de uso atingido (429) {resposta.text[:300]}"
                    )
                # o que o Gemini sugerir; senão, espera exponencial: 5 s, 10 s, 20 s...
                logger.warning("Embedding: limite de uso (429), esperando para tentar de novo")
                self.dormir(min(espera_sugerida(resposta.text) or espera, 90) + 1)
                espera *= 2
                continue
            if resposta.status_code >= 400:
                raise ErroDoProvedor(
                    f"gemini-embedding: HTTP {resposta.status_code} {resposta.text[:300]}"
                )
            return [normalizar(e["values"]) for e in resposta.json()["embeddings"]]
        raise ErroDeLimite("gemini-embedding: limite de uso atingido (429)")

    def lotes(self, textos: list[str]):
        """Lotes de até `lote` textos e `tokens_por_lote` tokens estimados."""
        atual, tokens = [], 0
        for texto in textos:
            n = estimar_tokens(texto)
            if atual and (len(atual) == self.lote or tokens + n > self.tokens_por_lote):
                yield atual
                atual, tokens = [], 0
            atual.append(texto)
            tokens += n
        if atual:
            yield atual

    def vetorizar_trechos(self, textos: list[str]) -> list[list[float]]:
        vetores = []
        for parte in self.lotes(textos):
            vetores += self._chamar(parte, "RETRIEVAL_DOCUMENT")
        return vetores

    def vetorizar_consulta(self, texto: str) -> list[float]:
        return self._chamar([texto], "RETRIEVAL_QUERY")[0]

    def contar_tokens(self, texto: str) -> int:
        return estimar_tokens(texto)
