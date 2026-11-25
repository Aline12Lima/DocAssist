"""Envia os documentos do corpus para uma API do DocAssist, pelo POST /rag/ingest.

Serve para a nuvem: lá não existe a pasta corpus/raw (ela não vai para o GitHub), então
os documentos chegam pela própria API, como um usuário faria. Pode rodar de novo à
vontade: o que não mudou não é reprocessado.

Uso (dentro do container "api", onde estão o corpus e a chave):
    python -m scripts.enviar_corpus --url http://api-nuvem:8000

Para a nuvem, a chave de produção vem da variável DOCASSIST_CHAVE (assim ela não fica
no histórico do terminal nem aparece na tela). Da sua máquina:
    docker compose exec -e DOCASSIST_CHAVE="$(cat ~/.docassist_chave_nuvem)" api \
        python -m scripts.enviar_corpus --url https://SEU-APP.up.railway.app
"""

import argparse
import time
from pathlib import Path

import httpx
import yaml

from scripts.cliente_stream import chave_padrao

MANIFESTO = Path("corpus/manifest.yaml")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True, help="endereço da API, sem barra no final")
    parser.add_argument("--chave", default=None, help="chave de API (cabeçalho X-API-Key)")
    args = parser.parse_args()
    chave = args.chave if args.chave is not None else chave_padrao()
    cabecalhos = {"X-API-Key": chave} if chave else {}

    documentos = yaml.safe_load(MANIFESTO.read_text(encoding="utf-8"))
    total_chunks, inicio = 0, time.perf_counter()
    for doc in documentos:
        caminho = Path(doc["arquivo"])
        campos = {k: doc[k] for k in ("titulo", "fonte", "url") if doc.get(k)}
        campos["doc_id"] = doc["id"]
        with caminho.open("rb") as arquivo:
            # o Gemini tem limite por minuto: um documento pode levar até ~1 min
            resposta = httpx.post(
                f"{args.url}/rag/ingest",
                files={"arquivo": (caminho.name, arquivo)},
                data=campos,
                headers=cabecalhos,
                timeout=300,
            )
        if resposta.status_code != 200:
            print(f"{doc['id']:34} ERRO {resposta.status_code}: {resposta.text[:200]}")
            continue
        corpo = resposta.json()
        total_chunks += corpo["chunks"]
        print(
            f"{doc['id']:34} {corpo['chunks']:3} chunks ({corpo['gerados']} gerados) "
            f"em {corpo['tempo_ms'] / 1000:.1f} s"
        )
    print(f"\nTotal: {total_chunks} chunks em {time.perf_counter() - inicio:.0f} s")


if __name__ == "__main__":
    main()
