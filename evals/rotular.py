"""Você dá as notas à mão, no terminal, para conferir se o juiz concorda com uma pessoa.

Sorteia N respostas (sempre as mesmas, por causa da semente), mostra cada uma e
pergunta as duas notas. As notas vão para evals/rotulos_humanos.jsonl, uma por linha,
logo depois de cada resposta: se parar no meio, rode de novo que ele continua de onde parou.

Importante: dê as suas notas SEM olhar o relatório do juiz, para não se influenciar.

Uso:
    python -m evals.rotular --respostas evals/reports/2026-11-15_F8_respostas.jsonl
"""

import argparse
import json
import random
import textwrap
from pathlib import Path

ROTULOS = Path("evals/rotulos_humanos.jsonl")

RUBRICA = """
CORREÇÃO: compare a RESPOSTA com a REFERÊNCIA.
  2 = traz o essencial da referência e não contradiz
      (resposta mais longa, com detalhes a mais e corretos, continua 2)
  1 = parcial: falta parte do essencial, é vaga ou responde a uma pergunta parecida
  0 = errada, contradiz a referência ou não responde o que foi perguntado

FIDELIDADE: para cada afirmação da RESPOSTA, procure nos TRECHOS CITADOS.
  - Tradução e paráfrase valem: resposta em português resumindo trecho em inglês é fiel.
  - Exemplos de código copiados dos trechos são fiéis.
  - Não vale o que você sabe: verdade que não está nos trechos não é fiel.
  2 = todas as afirmações aparecem nos trechos
  1 = um detalhe secundário não aparece; o principal aparece
  0 = a afirmação principal não aparece nos trechos, ou os contradiz
"""


def ler_jsonl(caminho: Path) -> list[dict]:
    if not caminho.exists():
        return []
    return [
        json.loads(linha) for linha in caminho.read_text(encoding="utf-8").splitlines() if linha
    ]


def pedir_nota(rotulo: str) -> int:
    while True:
        valor = input(f"{rotulo} (0, 1 ou 2): ").strip()
        if valor in {"0", "1", "2"}:
            return int(valor)
        print("  Digite só 0, 1 ou 2.")


def mostrar(registro: dict, posicao: int, total: int) -> None:
    largura = 100
    print("\n" + "=" * largura)
    print(f"[{posicao}/{total}] {registro['id']} ({registro['tipo']})")
    print("=" * largura)
    print(f"PERGUNTA: {registro['pergunta']}\n")
    print(f"REFERÊNCIA: {registro['resposta_referencia']}\n")
    print("RESPOSTA DO SISTEMA:")
    print(textwrap.indent(registro["resposta"], "  "))
    print("\nTRECHOS CITADOS:")
    for citacao in registro["citacoes"]:
        print(f"  [{citacao['n']}] {citacao.get('secao') or ''}")
        print(textwrap.indent(textwrap.fill(citacao["trecho"], largura - 6), "      "))
    print("-" * largura)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--respostas", required=True, type=Path, help=".jsonl do perguntar.py")
    parser.add_argument("--quantidade", type=int, default=15)
    parser.add_argument("--semente", type=int, default=7)
    args = parser.parse_args()

    candidatas = [r for r in ler_jsonl(args.respostas) if r["deve_responder"] and r["respondeu"]]
    sorteadas = random.Random(args.semente).sample(
        candidatas, min(args.quantidade, len(candidatas))
    )
    sorteadas.sort(key=lambda r: r["id"])
    feitas = {r["id"] for r in ler_jsonl(ROTULOS)}
    pendentes = [r for r in sorteadas if r["id"] not in feitas]

    print(RUBRICA)
    print(f"{len(sorteadas)} respostas sorteadas; {len(feitas & {r['id'] for r in sorteadas})} já")
    print(f"têm nota; faltam {len(pendentes)}. Ctrl+C para parar (o que já foi salvo fica).")

    for posicao, registro in enumerate(pendentes, start=1):
        mostrar(registro, posicao, len(pendentes))
        rotulo = {
            "id": registro["id"],
            "correcao": pedir_nota("Correção"),
            "fidelidade": pedir_nota("Fidelidade"),
            "comentario": input("Comentário (opcional, Enter para pular): ").strip(),
        }
        with ROTULOS.open("a", encoding="utf-8") as arquivo:
            arquivo.write(json.dumps(rotulo, ensure_ascii=False) + "\n")

    print(f"\nPronto. Suas notas estão em {ROTULOS}.")


if __name__ == "__main__":
    main()
