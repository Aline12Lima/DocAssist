"""Cliente do /rag/ask/stream: mostra a resposta na tela conforme ela chega.

É o lado de quem CONSOME a API: abre a conexão, lê os eventos SSE um a um e
imprime os pedaços de texto sem esperar a resposta inteira.

Uso (dentro do container, onde a API está em localhost:8000):
    python -m scripts.cliente_stream "Como o compose espera o banco ficar pronto?"
    python -m scripts.cliente_stream "..." --url http://localhost:8000
    python -m scripts.cliente_stream "..." --chave MINHA_CHAVE

Se a API exige chave (API_KEYS no .env), o cliente manda no cabeçalho X-API-Key.
Sem --chave, usa a variável DOCASSIST_CHAVE ou, por conveniência no desenvolvimento
(o cliente roda no mesmo container que a API), a primeira chave de API_KEYS.
"""

import argparse
import json
import os
import sys
import time

import httpx

from app.config import settings


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


def chave_padrao() -> str:
    if os.environ.get("DOCASSIST_CHAVE"):
        return os.environ["DOCASSIST_CHAVE"]
    chaves = [c.strip() for c in settings.API_KEYS.split(",") if c.strip()]
    return chaves[0] if chaves else ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pergunta")
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--chave", default=None, help="chave de API (cabeçalho X-API-Key)")
    args = parser.parse_args()
    chave = args.chave if args.chave is not None else chave_padrao()
    cabecalhos = {"X-API-Key": chave} if chave else {}

    inicio = time.perf_counter()
    primeiro_pedaco = None
    with httpx.stream(
        "POST",
        f"{args.url}/rag/ask/stream",
        json={"pergunta": args.pergunta},
        headers=cabecalhos,
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
                    # O que o SERVIDOR mediu. A diferença para os tempos acima é a rede
                    # entre você e a API (incluindo o DNS da sua máquina).
                    no_servidor = [
                        f"{rotulo} {meta[campo] / 1000:.1f} s"
                        for rotulo, campo in (
                            ("busca", "tempo_busca_ms"),
                            ("LLM", "tempo_llm_ms"),
                            ("1º pedaço", "tempo_primeiro_pedaco_ms"),
                        )
                        if meta.get(campo) is not None
                    ]
                    if no_servidor:
                        print("No servidor: " + ", ".join(no_servidor) + ".")
                else:
                    origem = "cache" if meta["cache"] else "sem chamar o LLM"
                    print(f"\nResposta completa em {total:.1f} s ({origem}).")
                print(f"interacao_id: {dados.get('interacao_id')}")


if __name__ == "__main__":
    main()
