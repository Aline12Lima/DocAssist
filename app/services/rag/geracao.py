"""Montagem das mensagens para o LLM: o prompt versionado + os trechos numerados."""

from functools import lru_cache
from pathlib import Path

PASTA_DE_PROMPTS = Path(__file__).resolve().parents[3] / "prompts"
VERSAO_DO_PROMPT = "answer_v1"
SEM_RESPOSTA = "NÃO ENCONTRADO"
REFORCO_DE_CITACAO = (
    "Sua resposta anterior não tinha citações. Responda de novo seguindo a regra 2: "
    "depois de cada afirmação, cite o trecho com [n]."
)


@lru_cache
def carregar_prompt(versao: str = VERSAO_DO_PROMPT) -> str:
    return (PASTA_DE_PROMPTS / f"{versao}.md").read_text(encoding="utf-8").strip()


def montar_contexto(trechos: list[dict]) -> str:
    """Numera os trechos a partir de 1. O texto de cada chunk já começa com 'Documento › Seção'."""
    blocos = [f"[{n}] {trecho['texto']}" for n, trecho in enumerate(trechos, start=1)]
    return "<trechos>\n" + "\n\n".join(blocos) + "\n</trechos>"


def montar_mensagens(pergunta: str, trechos: list[dict], reforco: bool = False) -> list[dict]:
    conteudo = f"{montar_contexto(trechos)}\n\nPergunta: {pergunta}"
    if reforco:
        conteudo += f"\n\n{REFORCO_DE_CITACAO}"
    return [
        {"role": "system", "content": carregar_prompt()},
        {"role": "user", "content": conteudo},
    ]


def eh_sem_resposta(texto: str) -> bool:
    return texto.strip().rstrip(".").upper() == SEM_RESPOSTA
