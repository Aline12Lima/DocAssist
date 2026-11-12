"""Avalia a recuperação do DocAssist com o golden set (Recall@k e MRR).

Uso, sempre numa coleção separada da principal:
    # E0: cada documento inteiro vira um vetor
    docker compose exec -e CHROMA_COLLECTION=eval_e0 api python -m evals.run_eval --nome E0 --modo documento
    # E1: documentos divididos em chunks
    docker compose exec -e CHROMA_COLLECTION=eval_e1 api python -m evals.run_eval --nome E1 --modo chunks
"""

import argparse
import html
import json
import re
from datetime import date
from pathlib import Path

import yaml

from app.config import settings
from app.models.hf_loader import get_embeddings_model
from app.services.chroma_service import add_document, get_chroma_client, search_documents
from app.services.rag.ingest import criar_contador, ingerir_arquivo

GOLDEN_SET = Path("evals/golden_set.jsonl")
MANIFESTO = Path("corpus/manifest.yaml")
RELATORIOS = Path("evals/reports")
TOP_K = 10


def normalizar(texto: str, formato: str) -> str:
    """Mesma regra do verificador: remove tags do HTML e junta os espaços."""
    if formato == "html":
        texto = html.unescape(re.sub(r"<[^>]+>", " ", texto))
    return " ".join(texto.split())


def limpar_colecao():
    colecao = get_chroma_client()
    ids_antigos = colecao.get()["ids"]
    if ids_antigos:
        colecao.delete(ids=ids_antigos)
    return colecao


def indexar_documentos_inteiros(documentos: list[dict]) -> int:
    """E0: cada documento inteiro, sem limpeza, vira um único vetor (o sistema original)."""
    for doc in documentos:
        caminho = Path(doc["arquivo"])
        formato = "html" if caminho.suffix == ".html" else "md"
        add_document(caminho.read_text(encoding="utf-8"), {"doc_id": doc["id"], "formato": formato})
    return len(documentos)


def indexar_chunks(documentos: list[dict], colecao, limite: int, overlap: int, minimo: int) -> int:
    """E1 em diante: parsers + chunker + ingestão com IDs determinísticos."""
    modelo = get_embeddings_model()
    contar = criar_contador(settings.HF_MODEL_EMBEDDINGS)
    total = 0
    for doc in documentos:
        resultado = ingerir_arquivo(
            Path(doc["arquivo"]), doc["id"], colecao, modelo, contar, doc, limite, overlap, minimo
        )
        total += resultado.chunks
    return total


def avaliar_pergunta(pergunta: dict) -> dict:
    resultados = search_documents(pergunta["pergunta"], top_k=TOP_K)
    textos = [normalizar(r["text"], r["metadata"].get("formato", "texto")) for r in resultados]

    doc_ids = [r["metadata"].get("doc_id") for r in resultados]

    # Para cada evidência, duas posições (1, 2, 3...):
    # - trecho: o primeiro resultado que CONTÉM a frase de evidência;
    # - documento: o primeiro resultado que vem do documento certo.
    posicoes, posicoes_doc = [], []
    for evidencia in pergunta["evidencias"]:
        trecho = " ".join(evidencia["trecho"].split())
        posicoes.append(next((i + 1 for i, t in enumerate(textos) if trecho in t), None))
        posicoes_doc.append(
            next((i + 1 for i, d in enumerate(doc_ids) if d == evidencia["doc_id"]), None)
        )

    return {
        "id": pergunta["id"],
        "tipo": pergunta["tipo"],
        "deve_responder": pergunta["deve_responder"],
        "posicoes": posicoes,
        "posicoes_doc": posicoes_doc,
        "top3": [r["metadata"].get("doc_id") for r in resultados[:3]],
        "distancia_top1": resultados[0]["distance"] if resultados else None,
    }


def acertou(posicoes: list, k: int) -> bool:
    """Acerto em k: todas as evidências aparecem entre os k primeiros resultados."""
    return all(p is not None and p <= k for p in posicoes)


def rank_reciproco(posicoes: list) -> float:
    """1 / posição do primeiro resultado com alguma evidência; 0 se nenhum tiver."""
    encontradas = [p for p in posicoes if p is not None]
    return 1 / min(encontradas) if encontradas else 0.0


def media(valores: list) -> float:
    return sum(valores) / len(valores) if valores else 0.0


def montar_relatorio(nome, descricao, itens, unidade, resultados, metricas, distancias) -> str:
    respondiveis = sum(r["deve_responder"] for r in resultados)
    linhas = [
        f"# Avaliação {nome}",
        "",
        f"- **Data:** {date.today()}",
        f"- **Configuração:** {descricao}",
        f"- **Modelo de embedding:** `{settings.HF_MODEL_EMBEDDINGS}`",
        f"- **Coleção:** `{settings.CHROMA_COLLECTION}` ({itens} {unidade} indexados)",
        f"- **Perguntas:** {len(resultados)} ({respondiveis} com resposta, "
        f"{len(resultados) - respondiveis} sem resposta)",
        "",
        "## Métricas",
        "",
        "| Métrica | Valor |",
        "| --- | --- |",
    ]
    for nome_metrica, valor in metricas.items():
        linhas.append(f"| {nome_metrica} | {valor:.2f} |")
    linhas += [
        f"| Distância média do 1º resultado, perguntas com resposta | {distancias['com']:.3f} |",
        f"| Distância média do 1º resultado, perguntas sem resposta | {distancias['sem']:.3f} |",
        "",
        "## Por pergunta",
        "",
        "| id | tipo | posição das evidências | 3 primeiros documentos | distância do 1º |",
        "| --- | --- | --- | --- | --- |",
    ]
    for r in resultados:
        posicoes = ", ".join(str(p) if p else "—" for p in r["posicoes"]) or "sem evidência"
        linhas.append(
            f"| {r['id']} | {r['tipo']} | {posicoes} | {', '.join(r['top3'])} "
            f"| {r['distancia_top1']:.3f} |"
        )
    return "\n".join(linhas) + "\n"


def main():
    parser = argparse.ArgumentParser(description="Avalia a recuperação com o golden set.")
    parser.add_argument("--nome", default="E0")
    parser.add_argument("--modo", choices=["documento", "chunks"], default="documento")
    parser.add_argument("--limite", type=int, default=250, help="tokens por chunk, com o prefixo")
    parser.add_argument("--overlap", type=int, default=30)
    parser.add_argument("--minimo", type=int, default=50)
    parser.add_argument("--descricao", default=None)
    args = parser.parse_args()

    if settings.CHROMA_COLLECTION == "documents":
        raise SystemExit("Pare: use uma coleção separada, por exemplo -e CHROMA_COLLECTION=eval_e1")

    documentos = yaml.safe_load(MANIFESTO.read_text(encoding="utf-8"))
    colecao = limpar_colecao()  # cada avaliação parte de uma coleção vazia

    if args.modo == "documento":
        itens, unidade = indexar_documentos_inteiros(documentos), "documentos"
        descricao = args.descricao or "MiniLM, documento inteiro, só vetorial (distância L2)"
    else:
        itens = indexar_chunks(documentos, colecao, args.limite, args.overlap, args.minimo)
        unidade = "chunks"
        descricao = args.descricao or (
            f"MiniLM, chunks por seção (limite {args.limite} tokens com prefixo, "
            f"overlap {args.overlap}, mínimo {args.minimo}), só vetorial (distância L2)"
        )

    perguntas = [
        json.loads(linha)
        for linha in GOLDEN_SET.read_text(encoding="utf-8").splitlines()
        if linha.strip()
    ]
    resultados = [avaliar_pergunta(p) for p in perguntas]

    com_resposta = [r for r in resultados if r["deve_responder"]]
    sem_resposta = [r for r in resultados if not r["deve_responder"]]

    # "trecho" é a métrica principal; "documento" permite comparar com o E0
    metricas = {}
    for nivel, campo in (("trecho", "posicoes"), ("documento", "posicoes_doc")):
        for k in (1, 3, 5):
            metricas[f"Recall@{k} ({nivel})"] = media([acertou(r[campo], k) for r in com_resposta])
        metricas[f"MRR ({nivel})"] = media([rank_reciproco(r[campo]) for r in com_resposta])
    distancias = {
        "com": media([r["distancia_top1"] for r in com_resposta]),
        "sem": media([r["distancia_top1"] for r in sem_resposta]),
    }

    relatorio = montar_relatorio(
        args.nome, descricao, itens, unidade, resultados, metricas, distancias
    )
    print(relatorio)

    RELATORIOS.mkdir(parents=True, exist_ok=True)
    caminho = RELATORIOS / f"{date.today()}_{args.nome}.md"
    caminho.write_text(relatorio, encoding="utf-8")
    print(f"Relatório salvo em {caminho}")


if __name__ == "__main__":
    main()
