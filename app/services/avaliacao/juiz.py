"""Juiz com LLM (LLM-as-judge): dá nota de correção e de fidelidade a uma resposta.

- Correção: a resposta bate com a resposta de referência do golden set?
- Fidelidade: o que a resposta afirma está nos trechos que ela citou?

O juiz é outro modelo, de outra família, para não favorecer as próprias respostas.
Antes de confiar nas notas dele, comparamos com notas dadas por uma pessoa
(veja concordancia.py).
"""

import json
from dataclasses import asdict, dataclass

from app.config import settings
from app.services.rag.geracao import carregar_prompt

NOTAS_VALIDAS = {0, 1, 2}
PEDIDO_DE_JSON = (
    "Sua resposta anterior não era um JSON válido. Responda SOMENTE com o objeto JSON "
    '{"correcao": 0 a 2, "fidelidade": 0 a 2, "justificativa": "..."}.'
)


class VereditoInvalido(ValueError):
    """O juiz não devolveu um JSON com as duas notas de 0 a 2."""


@dataclass
class Veredito:
    correcao: int
    fidelidade: int
    justificativa: str
    modelo: str

    def como_dict(self) -> dict:
        return asdict(self)


def montar_mensagens_do_juiz(item: dict, versao: str | None = None) -> list[dict]:
    """`item` tem pergunta, resposta_referencia, resposta e citacoes [{n, trecho}]."""
    trechos = "\n\n".join(f"[{c['n']}] {c['trecho']}" for c in item["citacoes"]) or "(nenhum)"
    conteudo = (
        f"<pergunta>\n{item['pergunta']}\n</pergunta>\n\n"
        f"<referencia>\n{item['resposta_referencia']}\n</referencia>\n\n"
        f"<resposta_do_sistema>\n{item['resposta']}\n</resposta_do_sistema>\n\n"
        f"<trechos_citados>\n{trechos}\n</trechos_citados>"
    )
    return [
        {"role": "system", "content": carregar_prompt(versao or settings.JUIZ_PROMPT_VERSAO)},
        {"role": "user", "content": conteudo},
    ]


def ler_veredito(texto: str) -> dict:
    """Acha o primeiro objeto JSON no texto (o modelo às vezes põe ```json em volta) e valida."""
    inicio = texto.find("{")
    if inicio == -1:
        raise VereditoInvalido(f"sem JSON na resposta: {texto[:120]!r}")
    try:
        dados, _ = json.JSONDecoder().raw_decode(texto[inicio:])
    except json.JSONDecodeError as erro:
        raise VereditoInvalido(f"JSON quebrado: {texto[:120]!r}") from erro
    if not isinstance(dados, dict):
        raise VereditoInvalido("o JSON não é um objeto")
    for campo in ("correcao", "fidelidade"):
        valor = dados.get(campo)
        if isinstance(valor, bool) or valor not in NOTAS_VALIDAS:
            raise VereditoInvalido(f"{campo} deve ser 0, 1 ou 2 (veio {valor!r})")
    return {
        "correcao": int(dados["correcao"]),
        "fidelidade": int(dados["fidelidade"]),
        "justificativa": str(dados.get("justificativa", "")).strip(),
    }


def julgar(item: dict, llm, versao: str | None = None) -> Veredito:
    """Pede as notas ao juiz. Se o JSON vier inválido, pede de novo uma vez."""
    mensagens = montar_mensagens_do_juiz(item, versao)
    resposta = llm.gerar(mensagens, settings.JUIZ_MAX_TOKENS, 0.0)
    try:
        dados = ler_veredito(resposta.texto)
    except VereditoInvalido:
        mensagens = mensagens + [
            {"role": "assistant", "content": resposta.texto},
            {"role": "user", "content": PEDIDO_DE_JSON},
        ]
        resposta = llm.gerar(mensagens, settings.JUIZ_MAX_TOKENS, 0.0)
        dados = ler_veredito(resposta.texto)  # se falhar de novo, o erro sobe
    return Veredito(modelo=resposta.modelo, **dados)
