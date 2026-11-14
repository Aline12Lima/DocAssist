"""Faz perguntas ao DocAssist pelo terminal, usando o mesmo pipeline do /rag/ask.

Uso:
    python -m scripts.perguntar "Como faço a API esperar o Postgres?"
    python -m scripts.perguntar --golden              # as 20 perguntas do golden set
    python -m scripts.perguntar --golden --pausa 10   # espera 10 s entre perguntas
"""

import argparse
import json
import time
from collections import Counter
from datetime import date
from pathlib import Path

from app.services.llm.cadeia import criar_cadeia
from app.services.rag.documentos import colecao_principal, embedder_principal
from app.services.rag.geracao import versao_do_prompt
from app.services.rag.pipeline import responder

GOLDEN_SET = Path("evals/golden_set.jsonl")
RELATORIOS = Path("evals/reports")


def formatar(resultado: dict) -> str:
    meta = resultado["meta"]
    linhas = [resultado["resposta"], ""]
    if resultado["aviso"]:
        linhas += [f"> Aviso: {resultado['aviso']}", ""]
    titulo = "Fontes" if resultado["encontrou_resposta"] else "Trechos mais próximos"
    linhas.append(f"**{titulo}:**")
    for citacao in resultado["citacoes"]:
        linhas.append(f"- [{citacao['n']}] {citacao['secao']} (distância {citacao['distancia']})")
    linhas += [
        "",
        f"`modelo: {meta['modelo']} | tokens: {meta['tokens_entrada']}+{meta['tokens_saida']} "
        f"| tentativas: {meta['tentativas']} | {meta['latencia_ms']} ms`",
    ]
    return "\n".join(linhas)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pergunta", nargs="?")
    parser.add_argument("--golden", action="store_true", help="roda as perguntas do golden set")
    parser.add_argument("--pausa", type=float, default=0, help="segundos entre perguntas")
    args = parser.parse_args()

    colecao, embedder = colecao_principal(), embedder_principal()
    llm = criar_cadeia()

    if not args.golden:
        if not args.pergunta:
            parser.error("informe uma pergunta ou use --golden")
        print(formatar(responder(args.pergunta, colecao, embedder, llm)))
        return

    perguntas = [
        json.loads(linha)
        for linha in GOLDEN_SET.read_text(encoding="utf-8").splitlines()
        if linha.strip()
    ]
    secoes = [f"# Respostas do golden set ({date.today()})", ""]
    modelos, respondidas, acertos_honestidade = Counter(), 0, 0
    segundas_tentativas, latencias = 0, []
    for i, pergunta in enumerate(perguntas):
        if i and args.pausa:
            time.sleep(args.pausa)
        resultado = responder(pergunta["pergunta"], colecao, embedder, llm)
        respondeu = resultado["encontrou_resposta"]
        respondidas += respondeu
        acertos_honestidade += respondeu == pergunta["deve_responder"]
        modelos[resultado["meta"]["modelo"] or "nenhum"] += 1
        segundas_tentativas += resultado["meta"]["tentativas"] > 1
        if resultado["meta"]["tentativas"]:
            latencias.append(resultado["meta"]["latencia_ms"])
        esperado = "deve responder" if pergunta["deve_responder"] else "NÃO deve responder"
        print(f"{pergunta['id']}  {'respondeu' if respondeu else 'não respondeu':14} ({esperado})")
        secoes += [
            f"## {pergunta['id']} — {pergunta['pergunta']}",
            "",
            f"*Tipo: {pergunta['tipo']} · {esperado} · referência: "
            f"{pergunta['resposta_referencia']}*",
            "",
            formatar(resultado),
            "",
        ]

    latencias.sort()
    p50 = latencias[len(latencias) // 2] if latencias else 0
    p95 = latencias[min(len(latencias) - 1, int(len(latencias) * 0.95))] if latencias else 0
    resumo = [
        "## Resumo",
        "",
        f"- Prompt: {versao_do_prompt()}",
        f"- Respondidas: {respondidas} de {len(perguntas)}",
        f"- Respondeu quando devia e recusou quando devia: {acertos_honestidade} de {len(perguntas)}",
        f"- Precisou de 2ª tentativa (sem citação na 1ª): {segundas_tentativas}",
        f"- Latência com LLM: mediana {p50} ms, p95 {p95} ms",
        f"- Modelos usados: {dict(modelos)}",
        "",
    ]
    RELATORIOS.mkdir(parents=True, exist_ok=True)
    caminho = RELATORIOS / f"{date.today()}_respostas_{versao_do_prompt()}.md"
    caminho.write_text("\n".join(secoes[:2] + resumo + secoes[2:]), encoding="utf-8")
    print("\n" + "\n".join(resumo))
    print(f"Relatório salvo em {caminho}")


if __name__ == "__main__":
    main()
