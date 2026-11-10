"""Baixa os documentos do corpus listados em corpus/manifest.yaml."""

import sys
from pathlib import Path

import httpx
import yaml

MANIFESTO = Path("corpus/manifest.yaml")


def main():
    documentos = yaml.safe_load(MANIFESTO.read_text(encoding="utf-8"))
    print(f"{len(documentos)} documentos no manifesto\n")

    falhas = 0
    for doc in documentos:
        destino = Path(doc["arquivo"])
        destino.parent.mkdir(parents=True, exist_ok=True)

        try:
            resposta = httpx.get(doc["download"], timeout=30, follow_redirects=True)
            resposta.raise_for_status()
        except httpx.HTTPError as erro:
            print(f"ERRO  {doc['id']}: {erro}")
            falhas += 1
            continue

        destino.write_text(resposta.text, encoding="utf-8")
        print(f"ok    {doc['id']}  ({len(resposta.text):,} caracteres)")

    print(f"\n{len(documentos) - falhas} baixados, {falhas} com erro")
    if falhas:
        sys.exit(1)


if __name__ == "__main__":
    main()