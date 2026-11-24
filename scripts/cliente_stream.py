"""Cliente do /rag/ask/stream: mostra a resposta na tela conforme ela chega.

É o lado de quem CONSOME a API: abre a conexão, lê os eventos SSE um a um e
imprime os pedaços de texto sem esperar a resposta inteira.

Uso (dentro do container, onde a API está em localhost:8000):
    python -m scripts.cliente_stream "Como o compose espera o banco ficar pronto?"
    python -m scripts.cliente_stream "..." --url http://localhost:8000
"""

import argparse
import json
import sys
import time

import httpx


def ler_eventos(resposta: httpx.Response):
    """Transforma as linhas do SSE em pares (evento, dados). Um evento termina numa linha vazia."""
    evento, dados = None, []
    for linha in resposta.iter_lines():
        if linha.startswith("event:"):
            evento = linha[len("event:") :].strip()
        elif linha.startswith("data:"):
            dados.append(linha[len("data:") :].strip())
        elif linha == "" and evento:
            yield evento, json.loads("\n".join(dados))
            evento, dados = None, []


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pergunta")
    parser.add_argument("--url", default="http://localhost:8000")
    args = parser.parse_args()

    inicio = time.perf_counter()
    primeiro_pedaco = None
    with httpx.stream(
        "POST",
        f"{args.url}/rag/ask/stream",
        json={"pergunta": args.pergunta},
        timeout=60,
    ) as resposta:
        if resposta.status_code != 200:
            resposta.read()
            sys.exit(f"Erro {resposta.status_code}: {resposta.text}")

        print("\nResposta (chegando aos pedaços):\n")
        for evento, dados in ler_eventos(resposta):
            if evento == "parcial":
                if primeiro_pedaco is None:
                    primeiro_pedaco = time.perf_counter() - inicio
                print(dados["texto"], end="", flush=True)  # flush: mostra já, sem esperar
            elif evento == "erro":
                print(f"\n\n[erro] {dados['detalhe']}")
            elif evento == "fim":
                total = time.perf_counter() - inicio
                print("\n\n--- versão final (citações conferidas) ---\n")
                print(dados["resposta"])
                if dados.get("aviso"):
                    print(f"\nAviso: {dados['aviso']}")
                print("\nFontes:")
                for citacao in dados["citacoes"]:
                    print(f"  [{citacao['n']}] {citacao['secao']}")
                meta = dados["meta"]
                if primeiro_pedaco is not None:
                    print(f"\nPrimeiro pedaço em {primeiro_pedaco:.1f} s; resposta completa em")
                    print(f"{total:.1f} s. Modelo: {meta['modelo']}.")
                    if meta.get("tempo_reranker_ms") is not None:
                        print(f"Só o reranker levou {meta['tempo_reranker_ms'] / 1000:.1f} s.")
                else:
                    origem = "cache" if meta["cache"] else "sem chamar o LLM"
                    print(f"\nResposta completa em {total:.1f} s ({origem}).")
                print(f"interacao_id: {dados.get('interacao_id')}")


if __name__ == "__main__":
    main()
