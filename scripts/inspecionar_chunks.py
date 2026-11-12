"""Mostra como o corpus fica dividido em chunks e confere se as evidências ficaram inteiras.

Uso:
    python -m scripts.inspecionar_chunks                     # resumo do corpus
    python -m scripts.inspecionar_chunks redis-ttl           # mostra os chunks de um documento
    python -m scripts.inspecionar_chunks --limite 200        # testa outro tamanho
"""

import argparse
import json
from pathlib import Path

import yaml

from app.config import settings
from app.services.rag.chunker import gerar_chunks
from app.services.rag.ingest import criar_contador
from app.services.rag.parsers import parse_arquivo

MANIFESTO = Path("corpus/manifest.yaml")
GOLDEN_SET = Path("evals/golden_set.jsonl")
LIMITE_DO_MODELO = 256


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("doc_id", nargs="?")
    parser.add_argument("--limite", type=int, default=250)
    parser.add_argument("--overlap", type=int, default=30)
    parser.add_argument("--minimo", type=int, default=50)
    args = parser.parse_args()

    contar = criar_contador(settings.HF_MODEL_EMBEDDINGS)
    documentos = yaml.safe_load(MANIFESTO.read_text(encoding="utf-8"))
    corpus = {
        doc["id"]: gerar_chunks(
            parse_arquivo(Path(doc["arquivo"]), doc["titulo"]),
            contar,
            args.limite,
            args.overlap,
            args.minimo,
        )
        for doc in documentos
    }

    if args.doc_id:
        for chunk in corpus[args.doc_id]:
            print(f"\n=== chunk {chunk.posicao}  ({contar(chunk.texto)} tokens)")
            print(chunk.texto)
        return

    tamanhos = sorted(contar(c.texto) for chunks in corpus.values() for c in chunks)
    print(f"{'documento':34} {'chunks':>6}")
    for doc_id, chunks in corpus.items():
        print(f"{doc_id:34} {len(chunks):6}")
    print(f"\nTotal: {len(tamanhos)} chunks")
    print(
        f"Tokens por chunk: menor {tamanhos[0]} | mediana {tamanhos[len(tamanhos) // 2]} "
        f"| maior {tamanhos[-1]}"
    )
    print(
        f"Acima do limite do modelo ({LIMITE_DO_MODELO}): "
        f"{sum(t > LIMITE_DO_MODELO for t in tamanhos)} (blocos de código grandes)"
    )

    # Cada evidência precisa caber INTEIRA em pelo menos um chunk
    conteudos = {
        doc_id: [" ".join(c.conteudo.split()) for c in chunks] for doc_id, chunks in corpus.items()
    }
    cortadas = 0
    for linha in GOLDEN_SET.read_text(encoding="utf-8").splitlines():
        if not linha.strip():
            continue
        pergunta = json.loads(linha)
        for evidencia in pergunta["evidencias"]:
            trecho = " ".join(evidencia["trecho"].split())
            if not any(trecho in c for c in conteudos[evidencia["doc_id"]]):
                cortadas += 1
                print(
                    f"CORTADA  {pergunta['id']}  {evidencia['doc_id']}: \"{evidencia['trecho']}\""
                )
    print(f"Evidências cortadas entre dois chunks: {cortadas}")


if __name__ == "__main__":
    main()
