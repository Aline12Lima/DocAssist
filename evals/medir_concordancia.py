"""Compara as suas notas (evals/rotulos_humanos.jsonl) com as do juiz.

Uso:
    python -m evals.medir_concordancia --juiz evals/reports/2026-11-15_J1.jsonl --nome C1
"""

import argparse
import json
from datetime import date
from pathlib import Path

from app.services.avaliacao.concordancia import medir_concordancia

ROTULOS = Path("evals/rotulos_humanos.jsonl")
RELATORIOS = Path("evals/reports")


def ler_jsonl(caminho: Path) -> list[dict]:
    return [
        json.loads(linha) for linha in caminho.read_text(encoding="utf-8").splitlines() if linha
    ]


def formatar(valor, porcentagem: bool = True) -> str:
    if valor is None:
        return "—"
    return f"{valor:.0%}" if porcentagem else f"{valor:.2f}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--juiz", required=True, type=Path, help=".jsonl do evals.julgar")
    parser.add_argument("--nome", required=True, help="nome do relatório, ex.: C1")
    args = parser.parse_args()

    humano = {r["id"]: r for r in ler_jsonl(ROTULOS)}
    juiz = {r["id"]: r for r in ler_jsonl(args.juiz)}
    ids = sorted(humano.keys() & juiz.keys())
    if not ids:
        raise SystemExit("Nenhuma pergunta com nota sua E do juiz. Confira os arquivos.")

    linhas = [
        f"# Concordância {args.nome}: você × juiz",
        "",
        f"- **Data:** {date.today()}",
        f"- **Juiz:** `{args.juiz}`",
        f"- **Respostas comparadas:** {len(ids)}",
        "",
        "| Nota | Exata | Até 1 ponto | Kappa |",
        "| --- | --- | --- | --- |",
    ]
    for campo, nome in (("correcao", "Correção"), ("fidelidade", "Fidelidade")):
        m = medir_concordancia([humano[i][campo] for i in ids], [juiz[i][campo] for i in ids])
        linhas.append(
            f"| {nome} | {formatar(m['exata'])} | {formatar(m['ate_um'])} "
            f"| {formatar(m['kappa'], porcentagem=False)} |"
        )
    linhas += [
        "",
        "## Onde vocês discordaram",
        "",
        "| id | correção (você/juiz) | fidelidade (você/juiz) | seu comentário | juiz |",
        "| --- | --- | --- | --- | --- |",
    ]
    for i in ids:
        h, j = humano[i], juiz[i]
        if h["correcao"] != j["correcao"] or h["fidelidade"] != j["fidelidade"]:
            justificativa = j["justificativa"].replace("|", "/").replace("\n", " ")
            comentario = h.get("comentario", "").replace("|", "/")
            linhas.append(
                f"| {i} | {h['correcao']}/{j['correcao']} | {h['fidelidade']}/{j['fidelidade']} "
                f"| {comentario} | {justificativa} |"
            )
    relatorio = "\n".join(linhas) + "\n"
    RELATORIOS.mkdir(parents=True, exist_ok=True)
    caminho = RELATORIOS / f"{date.today()}_{args.nome}.md"
    caminho.write_text(relatorio, encoding="utf-8")
    print(relatorio)
    print(f"Relatório salvo em {caminho}")


if __name__ == "__main__":
    main()
