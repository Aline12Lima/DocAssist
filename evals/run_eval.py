"""Avalia a recuperação do DocAssist com o golden set (Recall@k e MRR).

Cada execução recria a sua própria coleção de avaliação (eval_<modo>_<modelo>),
com distância cosseno e busca exata. A coleção principal nunca é tocada.

Uso:
    python -m evals.run_eval --nome E0 --modo documento --modelo minilm
    python -m evals.run_eval --nome E1 --modo chunks --modelo minilm
    python -m evals.run_eval --nome E2 --modo chunks --modelo e5small
"""

import argparse
import html
import json
import re
from datetime import date
from pathlib import Path

import yaml

from app.services.rag.embeddings import MODELOS, obter_embedder
from app.services.rag.ingest import ingerir_arquivo
from app.services.rag.vetores import buscar, obter_colecao

GOLDEN_SET = Path("evals/golden_set.jsonl")
MANIFESTO = Path("corpus/manifest.yaml")
RELATORIOS = Path("evals/reports")
TOP_K = 10


def normalizar(texto: str, formato: str) -> str:
    """Mesma regra do verificador: remove tags do HTML e junta os espaços."""
    if formato == "html":
        texto = html.unescape(re.sub(r"<[^>]+>", " ", texto))
    return " ".join(texto.split())


def indexar_documentos_inteiros(documentos: list[dict], colecao, embedder) -> int:
    """Modo documento (E0): cada arquivo bruto, sem limpeza, vira um único vetor."""
    textos, metadados = [], []
    for doc in documentos:
        caminho = Path(doc["arquivo"])
        textos.append(caminho.read_text(encoding="utf-8"))
        formato = "html" if caminho.suffix == ".html" else "md"
        metadados.append({"doc_id": doc["id"], "formato": formato})
    colecao.upsert(
        ids=[doc["id"] for doc in documentos],
        embeddings=embedder.vetorizar_trechos(textos),
        documents=textos,
        metadatas=metadados,
    )
    return len(documentos)


def indexar_chunks(documentos: list[dict], colecao, embedder, args) -> int:
    """Modo chunks (E1 em diante): parsers + chunker + ingestão com IDs determinísticos."""
    total = 0
    for doc in documentos:
        resultado = ingerir_arquivo(
            Path(doc["arquivo"]),
            doc["id"],
            colecao,
            embedder,
            doc,
            args.limite,
            args.overlap,
            args.minimo,
        )
        total += resultado.chunks
    return total


def avaliar_pergunta(pergunta: dict, colecao, embedder) -> dict:
    resultados = buscar(pergunta["pergunta"], colecao, embedder, k=TOP_K)
    textos = [normalizar(r["texto"], r["metadados"].get("formato", "texto")) for r in resultados]
    doc_ids = [r["metadados"].get("doc_id") for r in resultados]

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
        "top3": doc_ids[:3],
        "distancia_top1": resultados[0]["distancia"] if resultados else None,
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


def montar_relatorio(args, embedder, colecao_nome, itens, resultados, metricas, distancias):
    unidade = "documentos" if args.modo == "documento" else "chunks"
    if args.modo == "documento":
        configuracao = "documento inteiro"
    else:
        configuracao = (
            f"chunks por seção (limite {args.limite} tokens com prefixo, "
            f"overlap {args.overlap}, mínimo {args.minimo})"
        )
    respondiveis = sum(r["deve_responder"] for r in resultados)
    linhas = [
        f"# Avaliação {args.nome}",
        "",
        f"- **Data:** {date.today()}",
        f"- **Configuração:** {configuracao}; só vetorial; distância cosseno; busca exata",
        f"- **Modelo de embedding:** `{embedder.config.nome}`",
        f"- **Coleção:** `{colecao_nome}` ({itens} {unidade} indexados)",
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
    parser.add_argument("--nome", required=True, help="ex.: E0, E1, E2")
    parser.add_argument("--modo", choices=["documento", "chunks"], default="chunks")
    parser.add_argument("--modelo", choices=list(MODELOS), default="minilm")
    parser.add_argument("--limite", type=int, default=250, help="tokens por chunk, com o prefixo")
    parser.add_argument("--overlap", type=int, default=30)
    parser.add_argument("--minimo", type=int, default=50)
    args = parser.parse_args()

    embedder = obter_embedder(args.modelo)
    colecao_nome = f"eval_{args.modo}_{args.modelo}"
    colecao = obter_colecao(colecao_nome, recriar=True)  # cada avaliação parte do zero

    documentos = yaml.safe_load(MANIFESTO.read_text(encoding="utf-8"))
    if args.modo == "documento":
        itens = indexar_documentos_inteiros(documentos, colecao, embedder)
    else:
        itens = indexar_chunks(documentos, colecao, embedder, args)

    perguntas = [
        json.loads(linha)
        for linha in GOLDEN_SET.read_text(encoding="utf-8").splitlines()
        if linha.strip()
    ]
    resultados = [avaliar_pergunta(p, colecao, embedder) for p in perguntas]

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
        args, embedder, colecao_nome, itens, resultados, metricas, distancias
    )
    print(relatorio)

    RELATORIOS.mkdir(parents=True, exist_ok=True)
    caminho = RELATORIOS / f"{date.today()}_{args.nome}.md"
    caminho.write_text(relatorio, encoding="utf-8")
    print(f"Relatório salvo em {caminho}")


if __name__ == "__main__":
    main()
