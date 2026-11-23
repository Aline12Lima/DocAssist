"""Testa o juiz com respostas estragadas de propósito (veja perturbacoes.py).

Para cada resposta sorteada, o juiz avalia a original e três versões com erros
conhecidos. Um juiz confiável baixa a nota das versões com erro.

Uso:
    python -m evals.testar_juiz --respostas evals/reports/2026-11-15_F8_respostas.jsonl --nome T1
    python -m evals.testar_juiz --respostas ... --nome T2 --versao judge_v2
    python -m evals.testar_juiz --respostas ... --nome T3 --modelos groq:qwen/qwen3.8-27b
"""

import argparse
import json
import time
from collections import defaultdict
from datetime import date
from pathlib import Path

from app.config import settings
from app.services.avaliacao.juiz import VereditoInvalido, julgar
from app.services.avaliacao.perturbacoes import detectou, gerar_casos
from app.services.llm.base import ErroDoProvedor
from app.services.llm.cadeia import criar_cadeia

RELATORIOS = Path("evals/reports")
ORDEM = ["original", "resposta_trocada", "afirmacao_inventada", "trechos_trocados"]
ESPERADO = {
    "original": "— (controle)",
    "resposta_trocada": "correção ≤ 1 e fidelidade ≤ 1",
    "afirmacao_inventada": "fidelidade ≤ 1",
    "trechos_trocados": "fidelidade ≤ 1",
}


def ler_jsonl(caminho: Path) -> list[dict]:
    linhas = caminho.read_text(encoding="utf-8").splitlines()
    return [json.loads(linha) for linha in linhas if linha]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--respostas", required=True, type=Path, help=".jsonl do perguntar.py")
    parser.add_argument("--nome", required=True, help="nome do relatório, ex.: T1")
    parser.add_argument("--quantidade", type=int, default=10, help="respostas sorteadas")
    parser.add_argument("--versao", default=settings.JUIZ_PROMPT_VERSAO, help="prompt do juiz")
    parser.add_argument("--modelos", default=settings.JUIZ_MODELOS, help="cadeia do juiz")
    parser.add_argument("--pausa", type=float, default=4)
    args = parser.parse_args()

    juiz = criar_cadeia(args.modelos)
    print(f"Juiz: {juiz.nome} | prompt: {args.versao}")
    casos = gerar_casos(ler_jsonl(args.respostas), args.quantidade)

    resultados, falhas = [], []
    for i, caso in enumerate(casos):
        if i and args.pausa:
            time.sleep(args.pausa)
        try:
            veredito = julgar(caso, juiz, args.versao)
        except (VereditoInvalido, ErroDoProvedor) as erro:
            falhas.append(f"{caso['id']} {caso['caso']}: {str(erro)[:150]}")
            print(f"{caso['id']}  {caso['caso']:20} falhou")
            continue
        acerto = detectou(caso["caso"], veredito.correcao, veredito.fidelidade)
        resultados.append(
            {"id": caso["id"], "caso": caso["caso"], "acerto": acerto, **veredito.como_dict()}
        )
        marca = {True: "detectou", False: "NÃO detectou", None: ""}[acerto]
        print(
            f"{caso['id']}  {caso['caso']:20} correção {veredito.correcao}  "
            f"fidelidade {veredito.fidelidade}  {marca}"
        )

    por_caso = defaultdict(list)
    for r in resultados:
        por_caso[r["caso"]].append(r)
    linhas = [
        f"# Teste do juiz {args.nome}",
        "",
        f"- **Data:** {date.today()}",
        f"- **Juiz:** {juiz.nome}",
        f"- **Prompt:** {args.versao}",
        f"- **Respostas sorteadas:** {len(casos) // 4} (4 versões de cada)",
        f"- **Falhas do juiz:** {len(falhas)}",
        "",
        "| Versão | Esperado | Casos | Detectou | Correção média | Fidelidade média |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for caso in ORDEM:
        itens = por_caso.get(caso, [])
        if not itens:
            continue
        media_c = sum(i["correcao"] for i in itens) / len(itens)
        media_f = sum(i["fidelidade"] for i in itens) / len(itens)
        if caso == "original":
            taxa = "—"
        else:
            taxa = f"{sum(i['acerto'] for i in itens)} de {len(itens)}"
        linhas.append(
            f"| {caso} | {ESPERADO[caso]} | {len(itens)} | {taxa} "
            f"| {media_c:.2f} | {media_f:.2f} |"
        )
    linhas += ["", "## Erros que o juiz não percebeu", ""]
    for r in resultados:
        if r["acerto"] is False:
            justificativa = r["justificativa"].replace("\n", " ")
            linhas.append(
                f"- **{r['id']} ({r['caso']})**: correção {r['correcao']}, "
                f"fidelidade {r['fidelidade']}. Juiz: {justificativa}"
            )
    if falhas:
        linhas += ["", "## Falhas", ""] + [f"- {f}" for f in falhas]
    relatorio = "\n".join(linhas) + "\n"

    RELATORIOS.mkdir(parents=True, exist_ok=True)
    caminho = RELATORIOS / f"{date.today()}_{args.nome}.md"
    caminho.write_text(relatorio, encoding="utf-8")
    print("\n" + relatorio.split("## Erros")[0])
    print(f"Relatório salvo em {caminho}")


if __name__ == "__main__":
    main()
