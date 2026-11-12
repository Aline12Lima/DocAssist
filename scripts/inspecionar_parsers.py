"""Roda os parsers em todo o corpus e confere se as evidências do golden set sobreviveram.

Uso:
    python -m scripts.inspecionar_parsers                  # resumo de todos os documentos
    python -m scripts.inspecionar_parsers postgres-pg-isready   # mostra as seções de um documento
"""

import json
import sys
from pathlib import Path

import yaml

from app.services.rag.parsers import parse_arquivo

MANIFESTO = Path("corpus/manifest.yaml")
GOLDEN_SET = Path("evals/golden_set.jsonl")


def carregar_corpus() -> dict:
    """Devolve {doc_id: (documento do manifesto, lista de seções)}."""
    documentos = yaml.safe_load(MANIFESTO.read_text(encoding="utf-8"))
    return {
        doc["id"]: (doc, parse_arquivo(Path(doc["arquivo"]), doc["titulo"])) for doc in documentos
    }


def mostrar_documento(doc_id: str, corpus: dict):
    _, secoes = corpus[doc_id]
    for secao in secoes:
        print(f"\n=== {' › '.join(secao.caminho)}  ({len(secao.texto)} caracteres)")
        print(secao.texto[:500] + (" [...]" if len(secao.texto) > 500 else ""))


def resumo(corpus: dict):
    print(f"{'documento':34} {'seções':>6} {'bruto':>8} {'limpo':>8}")
    for doc_id, (doc, secoes) in corpus.items():
        bruto = len(Path(doc["arquivo"]).read_text(encoding="utf-8"))
        limpo = sum(len(s.texto) for s in secoes)
        print(f"{doc_id:34} {len(secoes):6} {bruto:8,} {limpo:8,}")


def conferir_evidencias(corpus: dict) -> int:
    textos = {
        doc_id: " ".join(" ".join(s.texto for s in secoes).split())
        for doc_id, (_, secoes) in corpus.items()
    }
    perdidas = 0
    for linha in GOLDEN_SET.read_text(encoding="utf-8").splitlines():
        if not linha.strip():
            continue
        pergunta = json.loads(linha)
        for evidencia in pergunta["evidencias"]:
            trecho = " ".join(evidencia["trecho"].split())
            if trecho not in textos[evidencia["doc_id"]]:
                perdidas += 1
                print(
                    f"PERDIDA  {pergunta['id']}  {evidencia['doc_id']}: \"{evidencia['trecho']}\""
                )
    return perdidas


def main():
    corpus = carregar_corpus()

    if len(sys.argv) > 1:
        mostrar_documento(sys.argv[1], corpus)
        return

    resumo(corpus)
    print()
    perdidas = conferir_evidencias(corpus)
    print(f"Evidências perdidas na limpeza: {perdidas}")
    sys.exit(1 if perdidas else 0)


if __name__ == "__main__":
    main()
