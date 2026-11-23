"""Respostas estragadas de propósito, para testar se o juiz percebe os erros.

Se o juiz dá 2 para tudo, ou as respostas são ótimas, ou o juiz é bonzinho demais.
Para separar os dois casos, pegamos respostas reais e criamos versões com erros
conhecidos. Um bom juiz tem que baixar a nota delas:

- resposta_trocada: a resposta de OUTRA pergunta (de outro documento), com os trechos
  originais. Não responde o que foi perguntado e não está nos trechos.
  Esperado: correção ≤ 1 e fidelidade ≤ 1.
- afirmacao_inventada: a resposta certa + uma frase inventada, com citação [n] para
  parecer apoiada. Esperado: fidelidade ≤ 1.
- trechos_trocados: a resposta certa, mas com os trechos de outra pergunta. O que ela
  afirma não está nesses trechos. Esperado: fidelidade ≤ 1.
- original: a resposta real, sem mudança (controle). Não há nota "certa": serve para
  ver se o juiz não ficou rigoroso demais.
"""

import random
from itertools import cycle

INVENCOES = [
    "Além disso, esse comportamento só funciona quando a variável de ambiente "
    "LEGACY_MODE=1 está definida",
    "Vale lembrar que esse recurso foi removido na versão 3.0 e hoje exige um plugin pago",
    "Por padrão, essa configuração também reinicia o servidor a cada 15 minutos",
]


def documento_principal(registro: dict) -> str | None:
    citacoes = registro.get("citacoes") or []
    return citacoes[0].get("doc_id") if citacoes else None


def escolher_outro(registros: list[dict], indice: int) -> dict:
    """Um registro de outro documento, começando do meio da lista (sempre o mesmo)."""
    doc = documento_principal(registros[indice])
    total = len(registros)
    for passo in range(total // 2, total + total // 2):
        candidato = registros[(indice + passo) % total]
        if documento_principal(candidato) != doc:
            return candidato
    raise ValueError("todas as respostas citam o mesmo documento")


def gerar_casos(registros: list[dict], quantidade: int = 10, semente: int = 11) -> list[dict]:
    """Para cada resposta sorteada, a original e as três versões estragadas."""
    validos = [r for r in registros if r.get("deve_responder") and r.get("respondeu")]
    validos = [r for r in validos if r.get("citacoes")]
    sorteados = random.Random(semente).sample(validos, min(quantidade, len(validos)))
    casos = []
    for posicao, registro in enumerate(sorteados):
        outro = escolher_outro(validos, validos.index(registro))
        primeira = registro["citacoes"][0]["n"]
        invencao = INVENCOES[posicao % len(INVENCOES)]
        casos += [
            {**registro, "caso": "original"},
            {**registro, "caso": "resposta_trocada", "resposta": outro["resposta"]},
            {
                **registro,
                "caso": "afirmacao_inventada",
                "resposta": f"{registro['resposta'].rstrip()}\n\n{invencao} [{primeira}].",
            },
            {
                **registro,
                "caso": "trechos_trocados",
                "citacoes": [
                    {**citacao, "n": original["n"]}  # mesmos números, textos de outra pergunta
                    for original, citacao in zip(registro["citacoes"], cycle(outro["citacoes"]))
                ],
            },
        ]
    return casos


def detectou(caso: str, correcao: int, fidelidade: int) -> bool | None:
    """O juiz baixou a nota como devia? None para o controle (não há resposta certa)."""
    if caso == "resposta_trocada":
        return correcao <= 1 and fidelidade <= 1
    if caso in ("afirmacao_inventada", "trechos_trocados"):
        return fidelidade <= 1
    return None
