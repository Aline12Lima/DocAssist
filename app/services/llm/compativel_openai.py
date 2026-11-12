"""Provedor para qualquer API no formato da OpenAI (/chat/completions): Groq, Gemini e outros."""

import re

import httpx

from app.services.llm.base import ErroDeLimite, ErroDoProvedor, RespostaLLM

# Alguns modelos "pensam em voz alta" dentro de <think>...</think>: isso não vai para o usuário.
PENSAMENTO = re.compile(r"<think>.*?</think>", re.DOTALL)


class ProvedorCompativelOpenAI:
    def __init__(
        self,
        provedor: str,
        url_base: str,
        chave: str,
        modelo: str,
        timeout: float = 30.0,
        cliente_http: httpx.Client | None = None,
    ):
        self.nome = f"{provedor}:{modelo}"
        self.url_base = url_base.rstrip("/")
        self.modelo = modelo
        self._chave = chave
        self._http = cliente_http or httpx.Client(timeout=timeout)

    def _cabecalhos(self) -> dict:
        return {"Authorization": f"Bearer {self._chave}"}

    def gerar(self, mensagens: list[dict], max_tokens: int, temperatura: float) -> RespostaLLM:
        corpo = {
            "model": self.modelo,
            "messages": mensagens,
            "max_tokens": max_tokens,
            "temperature": temperatura,
        }
        try:
            resposta = self._http.post(
                f"{self.url_base}/chat/completions", headers=self._cabecalhos(), json=corpo
            )
        except httpx.HTTPError as erro:
            raise ErroDoProvedor(f"{self.nome}: falha de conexão ({erro})") from erro

        if resposta.status_code == 429:
            raise ErroDeLimite(f"{self.nome}: limite de uso atingido (429)")
        if resposta.status_code >= 400:
            raise ErroDoProvedor(f"{self.nome}: HTTP {resposta.status_code} {resposta.text[:200]}")

        dados = resposta.json()
        try:
            texto = dados["choices"][0]["message"].get("content") or ""
        except (KeyError, IndexError) as erro:
            raise ErroDoProvedor(f"{self.nome}: resposta em formato inesperado") from erro

        texto = PENSAMENTO.sub("", texto).strip()
        if not texto:
            raise ErroDoProvedor(f"{self.nome}: resposta vazia")

        uso = dados.get("usage") or {}
        return RespostaLLM(
            texto=texto,
            modelo=self.nome,
            tokens_entrada=uso.get("prompt_tokens", 0),
            tokens_saida=uso.get("completion_tokens", 0),
        )

    def listar_modelos(self) -> list[str]:
        """Modelos que esta chave pode usar (endpoint /models)."""
        resposta = self._http.get(f"{self.url_base}/models", headers=self._cabecalhos())
        resposta.raise_for_status()
        return sorted(m["id"] for m in resposta.json().get("data", []))
