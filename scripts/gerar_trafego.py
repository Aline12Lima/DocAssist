"""Manda perguntas do golden set para o /rag/ask/stream, como se fossem pessoas usando.

Serve para encher as métricas do Prometheus com dados reais e, no fim, mostra quanto
tempo cada etapa levou. A pausa entre perguntas respeita o limite por minuto da API.

Uso (dentro do container):
    python -m scripts.gerar_trafego                   # 15 perguntas, 7 s entre elas
    python -m scripts.gerar_trafego --quantidade 30 --pausa 7
"""

import argparse
import json
import random
import statistics
import time
from pathlib import Path

import httpx

from scripts.cliente_stream import chave_padrao, ler_eventos

GOLDEN_SET = Path("evals/golden_set.jsonl")


def mediana(valores: list) -> str:
    valores = [v for v in valores if v is not None]
    return f"{statistics.median(valores) / 1000:.1f} s" if valores else "—"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--quantidade", type=int, default=15)
    parser.add_argument("--pausa", type=float, default=7, help="segundos entre perguntas")
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--semente", type=int, default=3)
    args = parser.parse_args()

    linhas = GOLDEN_SET.read_text(encoding="utf-8").splitlines()
    perguntas = [json.loads(linha) for linha in linhas if linha]
    sorteadas = random.Random(args.semente).sample(perguntas, min(args.quantidade, len(perguntas)))
    cabecalhos = {"X-API-Key": chave} if (chave := chave_padrao()) else {}

    metas = []
    print(f"{'id':5} {'status':6} {'origem':8} {'1º pedaço':>10} {'total':>7}")
    for i, pergunta in enumerate(sorteadas):
        if i:
            time.sleep(args.pausa)
        with httpx.stream(
            "POST",
            f"{args.url}/rag/ask/stream",
            json={"pergunta": pergunta["pergunta"]},
            headers=cabecalhos,
            timeout=90,
        ) as resposta:
            if resposta.status_code != 200:
                print(f"{pergunta['id']:5} {resposta.status_code:<6}")
                continue
            fim = next((dados for evento, dados in ler_eventos(resposta) if evento == "fim"), None)
        if fim is None:
            print(f"{pergunta['id']:5} sem evento fim")
            continue
        meta = fim["meta"]
        metas.append(meta)
        origem = "cache" if meta["cache"] else ("llm" if meta["tentativas"] else "sem_llm")
        primeiro = meta.get("tempo_primeiro_pedaco_ms")
        primeiro_txt = f"{primeiro / 1000:.1f} s" if primeiro is not None else "—"
        print(
            f"{pergunta['id']:5} {200:<6} {origem:8} {primeiro_txt:>10} "
            f"{meta['latencia_ms'] / 1000:>5.1f} s"
        )

    novas = [m for m in metas if not m["cache"]]
    print(f"\nMedianas de {len(novas)} perguntas que não vieram do cache:")
    print(f"  busca (embedding + Chroma): {mediana([m.get('tempo_busca_ms') for m in novas])}")
    print(f"  reranker:                   {mediana([m.get('tempo_reranker_ms') for m in novas])}")
    print(f"  LLM (até o fim do texto):   {mediana([m.get('tempo_llm_ms') for m in novas])}")
    print(
        f"  até o 1º pedaço na tela:    "
        f"{mediana([m.get('tempo_primeiro_pedaco_ms') for m in novas])}"
    )
    print(f"  total:                      {mediana([m['latencia_ms'] for m in novas])}")


if __name__ == "__main__":
    main()
