"""Passa as respostas do golden set pelo juiz (LLM-as-judge) e gera um relatório.

Lê o .jsonl salvo por `python -m scripts.perguntar --golden`. Só julga as perguntas que
deviam ser respondidas e foram respondidas: a honestidade (recusar quando não há
resposta) já é medida pelo perguntar.py.

Uso:
    python -m evals.julgar --respostas evals/reports/2026-11-15_F8_respostas.jsonl --nome J1
    python -m evals.julgar --respostas ... --nome teste --limite 3   # só as 3 primeiras
    python -m evals.julgar --respostas ... --nome J2 --versao judge_v2  # outro prompt do juiz
"""

import argparse
import json
import time
from collections import defaultdict
from datetime import date
from pathlib import Path

from app.config import settings
from app.services.avaliacao.juiz import VereditoInvalido, julgar
from app.services.llm.base import ErroDoProvedor
from app.services.llm.cadeia import criar_cadeia

RELATORIOS = Path("evals/reports")


def ler_jsonl(caminho: Path) -> list[dict]:
    return [
        json.loads(linha) for linha in caminho.read_text(encoding="utf-8").splitlines() if linha
    ]


def media(valores: list[int]) -> float:
    return sum(valores) / len(valores) if valores else 0.0


def fracao_nota_maxima(valores: list[int]) -> float:
    return sum(v == 2 for v in valores) / len(valores) if valores else 0.0


def montar_relatorio(args, julgados: list[dict], falhas: list[dict], total: int) -> str:
    correcao = [j["correcao"] for j in julgados]
    fidelidade = [j["fidelidade"] for j in julgados]
    modelos = sorted({j["modelo"] for j in julgados})
    linhas = [
        f"# Juiz {args.nome}",
        "",
        f"- **Data:** {date.today()}",
        f"- **Respostas:** `{args.respostas}`",
        f"- **Prompt do juiz:** {args.versao}",
        f"- **Modelos do juiz:** {', '.join(modelos) or '—'}",
        f"- **Julgadas:** {len(julgados)} (de {total} perguntas que deviam e foram respondidas)",
        f"- **Falhas do juiz:** {len(falhas)}",
        "",
        "## Notas (0 a 2)",
        "",
        "| Métrica | Média | Nota 2 |",
        "| --- | --- | --- |",
        f"| Correção | {media(correcao):.2f} | {fracao_nota_maxima(correcao):.0%} |",
        f"| Fidelidade | {media(fidelidade):.2f} | {fracao_nota_maxima(fidelidade):.0%} |",
        "",
        "## Por tipo de pergunta",
        "",
        "| tipo | julgadas | correção média | fidelidade média |",
        "| --- | --- | --- | --- |",
    ]
    por_tipo = defaultdict(list)
    for j in julgados:
        por_tipo[j["tipo"]].append(j)
    for tipo, itens in sorted(por_tipo.items()):
        linhas.append(
            f"| {tipo} | {len(itens)} | {media([i['correcao'] for i in itens]):.2f} "
            f"| {media([i['fidelidade'] for i in itens]):.2f} |"
        )
    linhas += [
        "",
        "## Respostas que não tiraram 2 nas duas notas",
        "",
        "| id | tipo | correção | fidelidade | justificativa do juiz |",
        "| --- | --- | --- | --- | --- |",
    ]
    for j in julgados:
        if j["correcao"] < 2 or j["fidelidade"] < 2:
            justificativa = j["justificativa"].replace("|", "/").replace("\n", " ")
            linhas.append(
                f"| {j['id']} | {j['tipo']} | {j['correcao']} | {j['fidelidade']} "
                f"| {justificativa} |"
            )
    if falhas:
        linhas += ["", "## Falhas do juiz", ""]
        linhas += [f"- {f['id']}: {f['erro']}" for f in falhas]
    return "\n".join(linhas) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--respostas", required=True, type=Path, help=".jsonl do perguntar.py")
    parser.add_argument("--nome", required=True, help="nome do relatório, ex.: J1")
    parser.add_argument("--pausa", type=float, default=4, help="segundos entre chamadas")
    parser.add_argument("--limite", type=int, default=None, help="julga só as N primeiras")
    parser.add_argument("--versao", default=settings.JUIZ_PROMPT_VERSAO, help="prompt do juiz")
    parser.add_argument("--modelos", default=settings.JUIZ_MODELOS, help="cadeia do juiz")
    args = parser.parse_args()

    juiz = criar_cadeia(args.modelos)
    print(f"Juiz: {juiz.nome}")
    candidatas = [r for r in ler_jsonl(args.respostas) if r["deve_responder"] and r["respondeu"]]
    if args.limite:
        candidatas = candidatas[: args.limite]

    julgados, falhas = [], []
    for i, registro in enumerate(candidatas):
        if i and args.pausa:
            time.sleep(args.pausa)
        try:
            veredito = julgar(registro, juiz, args.versao)
        except (VereditoInvalido, ErroDoProvedor) as erro:
            falhas.append({"id": registro["id"], "erro": str(erro)[:200]})
            print(f"{registro['id']}  falhou: {str(erro)[:100]}")
            continue
        julgados.append({"id": registro["id"], "tipo": registro["tipo"], **veredito.como_dict()})
        print(f"{registro['id']}  correção {veredito.correcao}  fidelidade {veredito.fidelidade}")

    RELATORIOS.mkdir(parents=True, exist_ok=True)
    base = RELATORIOS / f"{date.today()}_{args.nome}"
    relatorio = montar_relatorio(args, julgados, falhas, len(candidatas))
    base.with_suffix(".md").write_text(relatorio, encoding="utf-8")
    base.with_suffix(".jsonl").write_text(
        "".join(json.dumps(j, ensure_ascii=False) + "\n" for j in julgados), encoding="utf-8"
    )
    print("\n" + relatorio.split("## Por tipo")[0])
    print(f"Relatório salvo em {base.with_suffix('.md')}")
    print(f"Notas do juiz em {base.with_suffix('.jsonl')}")


if __name__ == "__main__":
    main()
