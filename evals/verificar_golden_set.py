"""Confere o golden set: formato, ids e se cada trecho de evidência existe no documento."""

import html
import json
import re
import sys
from pathlib import Path

import yaml

GOLDEN_SET = Path("evals/golden_set.jsonl")
MANIFESTO = Path("corpus/manifest.yaml")
CAMPOS = {"id", "pergunta", "tipo", "evidencias", "resposta_referencia", "deve_responder"}
TIPOS = {"factual", "procedimento", "termo_exato", "dois_docs", "sem_resposta"}


def texto_normalizado(caminho: Path) -> str:
    """Lê o documento e junta tudo numa linha só, com um espaço entre as palavras."""
    texto = caminho.read_text(encoding="utf-8")
    if caminho.suffix == ".html":
        texto = html.unescape(re.sub(r"<[^>]+>", " ", texto))
    return " ".join(texto.split())


def main():
    manifesto = yaml.safe_load(MANIFESTO.read_text(encoding="utf-8"))
    arquivos = {doc["id"]: Path(doc["arquivo"]) for doc in manifesto}
    textos = {}
    ids = set()
    com_erro = 0

    linhas = [linha for linha in GOLDEN_SET.read_text(encoding="utf-8").splitlines() if linha.strip()]

    for numero, linha in enumerate(linhas, start=1):
        problemas = []
        try:
            pergunta = json.loads(linha)
        except json.JSONDecodeError as erro:
            print(f"ERRO linha {numero}: JSON inválido ({erro})")
            com_erro += 1
            continue

        faltando = CAMPOS - pergunta.keys()
        if faltando:
            problemas.append(f"campos faltando: {sorted(faltando)}")
        if pergunta.get("id") in ids:
            problemas.append("id repetido")
        ids.add(pergunta.get("id"))
        if pergunta.get("tipo") not in TIPOS:
            problemas.append(f"tipo inválido: {pergunta.get('tipo')}")
        if pergunta.get("deve_responder") and not pergunta.get("evidencias"):
            problemas.append("deve_responder é true, mas não há evidências")

        for evidencia in pergunta.get("evidencias", []):
            doc_id = evidencia["doc_id"]
            if doc_id not in arquivos:
                problemas.append(f"doc_id não existe no manifesto: {doc_id}")
                continue
            if doc_id not in textos:
                textos[doc_id] = texto_normalizado(arquivos[doc_id])
            trecho = " ".join(evidencia["trecho"].split())
            if trecho not in textos[doc_id]:
                problemas.append(f'trecho não encontrado em {doc_id}: "{evidencia["trecho"]}"')

        situacao = "ok  " if not problemas else "ERRO"
        print(f"{situacao} {pergunta.get('id')}  ({pergunta.get('tipo')})")
        for problema in problemas:
            print(f"       - {problema}")
        if problemas:
            com_erro += 1

    print(f"\n{len(linhas)} perguntas, {com_erro} com problema")
    sys.exit(1 if com_erro else 0)


if __name__ == "__main__":
    main()
