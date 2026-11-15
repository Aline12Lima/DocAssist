"""Busca híbrida: junta a lista da busca vetorial com a do BM25 usando RRF.

As duas buscas dão notas em escalas diferentes (distância cosseno x pontuação
BM25), então não dá para somar as notas. O Reciprocal Rank Fusion usa só a
POSIÇÃO de cada trecho em cada lista:

    nota_rrf(trecho) = soma, em cada lista onde ele aparece, de 1 / (rrf_k + posição)

Um trecho que aparece bem nas duas listas ganha de um que aparece só em uma.
O rrf_k = 60 é o valor do artigo original; ele suaviza a diferença entre o 1º e o 2º lugar.
"""

from app.services.rag.lexical import IndiceBM25
from app.services.rag.vetores import buscar


def fundir_rrf(listas: list[list[dict]], rrf_k: int = 60) -> list[dict]:
    """Funde várias listas ordenadas de resultados (dicts com "id") numa só."""
    notas: dict[str, float] = {}
    itens: dict[str, dict] = {}
    for lista in listas:
        for posicao, resultado in enumerate(lista, start=1):
            chave = resultado["id"]
            notas[chave] = notas.get(chave, 0.0) + 1 / (rrf_k + posicao)
            if chave not in itens:
                itens[chave] = dict(resultado)
            else:
                # guarda a distância do vetorial e a pontuação do BM25, venha de onde vier
                for campo in ("distancia", "pontuacao_bm25"):
                    if itens[chave].get(campo) is None and resultado.get(campo) is not None:
                        itens[chave][campo] = resultado[campo]
    ordem = sorted(notas, key=lambda chave: notas[chave], reverse=True)
    return [{**itens[chave], "nota_rrf": notas[chave]} for chave in ordem]


def buscar_hibrido(
    consulta: str,
    colecao,
    embedder,
    indice: IndiceBM25,
    k: int = 5,
    candidatos: int = 30,
    rrf_k: int = 60,
    filtros: dict | None = None,
) -> list[dict]:
    """Pega os `candidatos` melhores de cada busca, funde com RRF e devolve os k primeiros."""
    vetorial = buscar(consulta, colecao, embedder, k=candidatos, filtros=filtros)
    lexical = indice.buscar(consulta, k=candidatos, filtros=filtros)
    return fundir_rrf([vetorial, lexical], rrf_k=rrf_k)[:k]
