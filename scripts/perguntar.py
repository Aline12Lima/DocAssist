"""Faz perguntas ao DocAssist pelo terminal, usando o mesmo pipeline do /rag/ask.

Uso:
    python -m scripts.perguntar "Como faço a API esperar o Postgres?"
    python -m scripts.perguntar --golden              # todas as perguntas do golden set
    python -m scripts.perguntar --golden --pausa 10   # espera 10 s entre perguntas
    python -m scripts.perguntar --golden --nome E5    # nome do relatório em evals/reports
    python -m scripts.perguntar --golden --sem-reranker   # compara com a busca só vetorial

O reranker segue o .env (RAG_RERANKER_ATIVO), como no /rag/ask.
"""

import argparse
import json
import time
from collections import Counter
from datetime import date
from pathlib import Path

from app.config import settings
from app.services.llm.cadeia import criar_cadeia
from app.services.rag.documentos import colecao_principal, embedder_principal
from app.services.rag.geracao import versao_do_prompt
from app.services.rag.pipeline import responder
from app.services.rag.reranker import obter_reranker

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
        nota = citacao.get("nota_reranker")
        detalhe = f"distância {citacao['distancia']}" + (
            f", nota {nota}" if nota is not None else ""
        )
        linhas.append(f"- [{citacao['n']}] {citacao['secao']} ({detalhe})")
    linhas += [
        "",
        f"`modelo: {meta['modelo']} | tokens: {meta['tokens_entrada']}+{meta['tokens_saida']} "
        f"| tentativas: {meta['tentativas']} | {meta['latencia_ms']} ms`",
    ]
    return "\n".join(linhas)


def percentil(valores: list[int], fracao: float) -> int:
    if not valores:
        return 0
    ordenados = sorted(valores)
    return ordenados[min(len(ordenados) - 1, int(len(ordenados) * fracao))]


def porcentagem(parte: int, total: int) -> str:
    return f"{parte / total:.0%}" if total else "—"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pergunta", nargs="?")
    parser.add_argument("--golden", action="store_true", help="roda as perguntas do golden set")
    parser.add_argument("--pausa", type=float, default=0, help="segundos entre perguntas")
    parser.add_argument("--nome", help="nome do relatório (padrão: respostas_<prompt>)")
    parser.add_argument("--sem-reranker", action="store_true", help="só a busca vetorial")
    args = parser.parse_args()

    colecao, embedder = colecao_principal(), embedder_principal()
    llm = criar_cadeia()
    reranker = None
    if settings.RAG_RERANKER_ATIVO and not args.sem_reranker:
        reranker = obter_reranker(settings.RAG_RERANKER_MODELO)

    if not args.golden:
        if not args.pergunta:
            parser.error("informe uma pergunta ou use --golden")
        print(formatar(responder(args.pergunta, colecao, embedder, llm, reranker=reranker)))
        return

    perguntas = [
        json.loads(linha)
        for linha in GOLDEN_SET.read_text(encoding="utf-8").splitlines()
        if linha.strip()
    ]
    secoes = [f"# Respostas do golden set ({date.today()})", ""]
    modelos, respondidas, acertos_honestidade = Counter(), 0, 0
    segundas_tentativas, latencias, latencias_todas = 0, [], []
    sem_resposta_certas, recusas_indevidas, recusadas_sem_llm = 0, 0, 0
    for i, pergunta in enumerate(perguntas):
        if i and args.pausa:
            time.sleep(args.pausa)
        resultado = responder(pergunta["pergunta"], colecao, embedder, llm, reranker=reranker)
        respondeu = resultado["encontrou_resposta"]
        respondidas += respondeu
        acertos_honestidade += respondeu == pergunta["deve_responder"]
        sem_resposta_certas += not pergunta["deve_responder"] and not respondeu
        recusas_indevidas += pergunta["deve_responder"] and not respondeu
        recusadas_sem_llm += resultado["meta"]["tentativas"] == 0
        latencias_todas.append(resultado["meta"]["latencia_ms"])
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

    total_sem = sum(not p["deve_responder"] for p in perguntas)
    total_com = len(perguntas) - total_sem
    if reranker is not None:
        busca = (
            f"vetorial + reranker `{reranker.nome}` ({settings.RAG_RERANKER_CANDIDATOS} "
            f"candidatos, limiar de nota {settings.RAG_LIMIAR_RERANKER})"
        )
    else:
        busca = f"só vetorial (limiar de distância {settings.RAG_LIMIAR_DISTANCIA})"
    resumo = [
        "## Resumo",
        "",
        f"- Prompt: {versao_do_prompt()}",
        f"- Busca: {busca}",
        f"- Respondidas: {respondidas} de {len(perguntas)}",
        f"- Respondeu quando devia e recusou quando devia: {acertos_honestidade} de {len(perguntas)}",
        f"- Acerto nas perguntas sem resposta: {sem_resposta_certas} de {total_sem} "
        f"({porcentagem(sem_resposta_certas, total_sem)})",
        f"- Recusa indevida (devia responder e não respondeu): {recusas_indevidas} de "
        f"{total_com} ({porcentagem(recusas_indevidas, total_com)})",
        f"- Recusadas pelo limiar, sem chamar o LLM: {recusadas_sem_llm}",
        f"- Precisou de 2ª tentativa (sem citação na 1ª): {segundas_tentativas}",
        f"- Latência com LLM: mediana {percentil(latencias, 0.5)} ms, "
        f"p95 {percentil(latencias, 0.95)} ms",
        f"- Latência de todas as perguntas: mediana {percentil(latencias_todas, 0.5)} ms, "
        f"p95 {percentil(latencias_todas, 0.95)} ms",
        f"- Modelos usados: {dict(modelos)}",
        "",
    ]
    RELATORIOS.mkdir(parents=True, exist_ok=True)
    nome = args.nome or f"respostas_{versao_do_prompt()}"
    caminho = RELATORIOS / f"{date.today()}_{nome}.md"
    caminho.write_text("\n".join(secoes[:2] + resumo + secoes[2:]), encoding="utf-8")
    print("\n" + "\n".join(resumo))
    print(f"Relatório salvo em {caminho}")


if __name__ == "__main__":
    main()
