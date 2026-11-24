"""Ajuda a escolher o limiar de distância a partir de um relatório do run_eval.

Lê a tabela "Por pergunta" (coluna "distância do 1º") e mostra, para cada limiar
possível, o que aconteceria se a busca recusasse tudo acima dele:
- acerto nas perguntas sem resposta (recusadas, como deviam);
- recusa indevida (perguntas com resposta recusadas por engano).

Lembre: o limiar não precisa pegar todas as perguntas sem resposta. O que passar dele
ainda vai para o LLM, que também pode responder "não encontrei". Por isso preferimos
um limiar com pouca recusa indevida.

Uso:
    python -m evals.calibrar_limiar evals/reports/2026-11-24_E7_gemini.md
"""

import argparse
import re
from pathlib import Path


def ler_distancias(caminho: Path) -> tuple[list[tuple[str, float]], list[tuple[str, float]]]:
    com, sem = [], []
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        celulas = [c.strip() for c in linha.strip().strip("|").split("|")]
        if len(celulas) < 5 or not re.fullmatch(r"q\d+", celulas[0]):
            continue
        try:
            distancia = float(celulas[4])
        except ValueError:
            continue
        destino = sem if celulas[1] == "sem_resposta" else com
        destino.append((celulas[0], distancia))
    return com, sem


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("relatorio", type=Path)
    args = parser.parse_args()

    com, sem = ler_distancias(args.relatorio)
    print(f"{len(com)} perguntas com resposta, {len(sem)} sem resposta\n")
    print("Com resposta, as 5 de MAIOR distância (seriam as primeiras recusadas por engano):")
    for id_, d in sorted(com, key=lambda x: -x[1])[:5]:
        print(f"  {id_}  {d:.3f}")
    print("Sem resposta, todas, da MENOR para a maior distância:")
    for id_, d in sorted(sem, key=lambda x: x[1]):
        print(f"  {id_}  {d:.3f}")

    print("\n limiar | sem resposta recusadas | recusa indevida")
    todas = sorted({d for _, d in com + sem})
    candidatos = [round((a + b) / 2, 3) for a, b in zip(todas, todas[1:], strict=False)]
    for limiar in candidatos:
        acerto = sum(d > limiar for _, d in sem)
        indevida = sum(d > limiar for _, d in com)
        if acerto == 0 or indevida > len(com) * 0.2:
            continue  # não ajuda, ou recusa demais
        print(
            f" {limiar:.3f} | {acerto:2d} de {len(sem)} ({acerto / len(sem):4.0%})"
            f"        | {indevida:2d} de {len(com)} ({indevida / len(com):4.0%})"
        )


if __name__ == "__main__":
    main()
