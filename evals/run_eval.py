"""Avalia a recuperação do DocAssist com o golden set (Recall@k e MRR).

Uso, sempre numa coleção separada da principal:
    docker compose exec -e CHROMA_COLLECTION=eval_e0 api python -m evals.run_eval --nome E0
"""

import argparse
import html
import json
import re
from datetime import date
from pathlib import Path

import yaml

from app.config import settings
from app.services.chroma_service import add_document, get_chroma_client, search_documents

GOLDEN_SET = Path("evals/golden_set.jsonl")
MANIFESTO = Path("corpus/manifest.yaml")
RELATORIOS = Path("evals/reports")
TOP_K = 10


def normalizar(texto: str, formato: str) -> str:
    """Mesma regra do verificador: remove tags do HTML e junta os espaços."""
    if formato == "html":
        texto = html.unescape(re.sub(r"<[^>]+>", " ", texto))
    return " ".join(texto.split())


def indexar_corpus() -> int:
    """E0: cada documento inteiro vira um único vetor, como o sistema faz hoje."""
    colecao = get_chroma_client()

    # O add_document usa uuid4: sem limpar antes, cada execução duplicaria tudo (lacuna L4).
    ids_antigos = colecao.get()["ids"]
    if ids_antigos:
        colecao.delete(ids=ids_antigos)

    documentos = yaml.safe_load(MANIFESTO.read_text(encoding="utf-8"))
    for doc in documentos:
        caminho = Path(doc["arquivo"])
        formato = "html" if caminho.suffix == ".html" else "md"
        texto = caminho.read_text(encoding="utf-8")
        add_document(texto, {"doc_id": doc["id"], "formato": formato})
    return len(documentos)


def avaliar_pergunta(pergunta: dict) -> dict:
    resultados = search_documents(pergunta["pergunta"], top_k=TOP_K)
    textos = [normalizar(r["text"], r["metadata"].get("formato", "md")) for r in resultados]

    # Para cada evidência: a posição (1, 2, 3...) do primeiro resultado que contém o trecho.
    posicoes = []
    for evidencia in pergunta["evidencias"]:
        trecho = " ".join(evidencia["trecho"].split())
        posicao = next((i + 1 for i, texto in enumerate(textos) if trecho in texto), None)
        posicoes.append(posicao)

    return {
        "id": pergunta["id"],
        "tipo": pergunta["tipo"],
        "deve_responder": pergunta["deve_responder"],
        "posicoes": posicoes,
        "top3": [r["metadata"].get("doc_id") for r in resultados[:3]],
        "distancia_top1": resultados[0]["distance"] if resultados else None,
    }


def acertou(resultado: dict, k: int) -> bool:
    """Acerto em k: todas as evidências aparecem entre os k primeiros resultados."""
    return all(p is not None and p <= k for p in resultado["posicoes"])


def rank_reciproco(resultado: dict) -> float:
    """1 / posição do primeiro resultado com alguma evidência; 0 se nenhum tiver."""
    encontradas = [p for p in resultado["posicoes"] if p is not None]
    return 1 / min(encontradas) if encontradas else 0.0


def media(valores: list) -> float:
    return sum(valores) / len(valores) if valores else 0.0


def montar_relatorio(nome, descricao, n_docs, resultados, metricas, distancias) -> str:
    respondiveis = sum(r["deve_responder"] for r in resultados)
    linhas = [
        f"# Avaliação {nome}",
        "",
        f"- **Data:** {date.today()}",
        f"- **Configuração:** {descricao}",
        f"- **Modelo de embedding:** `{settings.HF_MODEL_EMBEDDINGS}`",
        f"- **Coleção:** `{settings.CHROMA_COLLECTION}` ({n_docs} documentos indexados)",
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
    parser.add_argument("--descricao", default="MiniLM, documento inteiro, só vetorial (distância L2)")
    args = parser.parse_args()

    if settings.CHROMA_COLLECTION == "documents":
        raise SystemExit("Pare: use uma coleção separada, por exemplo -e CHROMA_COLLECTION=eval_e0")

    n_docs = indexar_corpus()
    perguntas = [
        json.loads(linha)
        for linha in GOLDEN_SET.read_text(encoding="utf-8").splitlines()
        if linha.strip()
    ]
    resultados = [avaliar_pergunta(p) for p in perguntas]

    com_resposta = [r for r in resultados if r["deve_responder"]]
    sem_resposta = [r for r in resultados if not r["deve_responder"]]

    metricas = {f"Recall@{k}": media([acertou(r, k) for r in com_resposta]) for k in (1, 3, 5)}
    metricas["MRR"] = media([rank_reciproco(r) for r in com_resposta])
    distancias = {
        "com": media([r["distancia_top1"] for r in com_resposta]),
        "sem": media([r["distancia_top1"] for r in sem_resposta]),
    }

    relatorio = montar_relatorio(args.nome, args.descricao, n_docs, resultados, metricas, distancias)
    print(relatorio)

    RELATORIOS.mkdir(parents=True, exist_ok=True)
    caminho = RELATORIOS / f"{date.today()}_{args.nome}.md"
    caminho.write_text(relatorio, encoding="utf-8")
    print(f"Relatório salvo em {caminho}")


if __name__ == "__main__":
    main()
