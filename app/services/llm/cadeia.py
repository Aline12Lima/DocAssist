"""Cadeia de reserva (fallback): tenta os provedores em ordem até um responder.

Se o primeiro chegar ao limite (429) ou falhar, o próximo da lista é usado. Assim a
camada gratuita de vários provedores funciona como uma só.
"""

import logging

from app.config import settings
from app.services.llm.base import ErroDoProvedor, LLMProvider, RespostaLLM
from app.services.llm.compativel_openai import ProvedorCompativelOpenAI

logger = logging.getLogger(__name__)

URLS = {
    "groq": "https://api.groq.com/openai/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai",
}


class CadeiaDeProvedores:
    def __init__(self, provedores: list[LLMProvider]):
        if not provedores:
            raise ValueError("Nenhum provedor de LLM configurado (confira as chaves no .env)")
        self.provedores = provedores
        self.nome = " → ".join(p.nome for p in provedores)

    def gerar(self, mensagens: list[dict], max_tokens: int, temperatura: float) -> RespostaLLM:
        falhas = []
        for provedor in self.provedores:
            try:
                return provedor.gerar(mensagens, max_tokens, temperatura)
            except ErroDoProvedor as erro:
                logger.warning("LLM indisponível, tentando o próximo: %s", erro)
                falhas.append(str(erro))
        raise ErroDoProvedor("Todos os provedores falharam: " + " | ".join(falhas))


def chave_do_provedor(provedor: str) -> str:
    return {"groq": settings.GROQ_API_KEY, "gemini": settings.GEMINI_API_KEY}.get(provedor, "")


def ler_lista_de_modelos(texto: str) -> list[tuple[str, str]]:
    """'groq:modelo-a, gemini:modelo-b' -> [('groq', 'modelo-a'), ('gemini', 'modelo-b')]."""
    pares = []
    for item in texto.split(","):
        item = item.strip()
        if not item:
            continue
        provedor, _, modelo = item.partition(":")
        pares.append((provedor.strip(), modelo.strip()))
    return pares


def criar_cadeia() -> CadeiaDeProvedores:
    """Monta a cadeia a partir de LLM_MODELOS. Provedores sem chave no .env são pulados."""
    provedores = []
    for provedor, modelo in ler_lista_de_modelos(settings.LLM_MODELOS):
        chave = chave_do_provedor(provedor)
        if provedor not in URLS or not chave:
            logger.info("Pulando %s:%s (provedor desconhecido ou sem chave)", provedor, modelo)
            continue
        provedores.append(
            ProvedorCompativelOpenAI(provedor, URLS[provedor], chave, modelo, settings.LLM_TIMEOUT)
        )
    return CadeiaDeProvedores(provedores)
