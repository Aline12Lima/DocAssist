"""Quanto o juiz concorda com uma pessoa? Antes de usar as notas do juiz, medimos isto.

- Concordância exata: as duas notas são iguais.
- Até 1 ponto: a diferença é no máximo 1 (numa escala de 0 a 2).
- Kappa de Cohen: a concordância descontando a que aconteceria por acaso.
  1 = perfeita; 0 = igual ao acaso; abaixo de 0 = pior que o acaso.
  Referência comum: acima de 0,6 é concordância boa; acima de 0,8, muito boa.
  Com poucas avaliações (15, por exemplo), o kappa varia muito: leia junto com a exata.
"""

from collections import Counter


def kappa_de_cohen(a: list[int], b: list[int]) -> float | None:
    """Kappa entre duas listas de notas do mesmo tamanho. None se não der para calcular."""
    if len(a) != len(b) or not a:
        return None
    total = len(a)
    observada = sum(x == y for x, y in zip(a, b, strict=True)) / total
    contagem_a, contagem_b = Counter(a), Counter(b)
    esperada = sum(contagem_a[c] * contagem_b[c] for c in set(a) | set(b)) / total**2
    if esperada == 1:
        return 1.0 if observada == 1 else None  # todos deram sempre a mesma nota
    return (observada - esperada) / (1 - esperada)


def medir_concordancia(humano: list[int], juiz: list[int]) -> dict:
    total = len(humano)
    if total == 0 or total != len(juiz):
        return {"total": total, "exata": None, "ate_um": None, "kappa": None}
    pares = list(zip(humano, juiz, strict=True))
    return {
        "total": total,
        "exata": sum(h == j for h, j in pares) / total,
        "ate_um": sum(abs(h - j) <= 1 for h, j in pares) / total,
        "kappa": kappa_de_cohen(humano, juiz),
    }
