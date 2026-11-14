"""Busca lexical com BM25: acha trechos que têm as MESMAS palavras da pergunta.

A busca vetorial entende o sentido ("apagar sozinha" ~ "expire"), mas pode errar
em termos exatos (XX, GT, :path, env_file). O BM25 faz o contrário: só conta
palavras iguais, e dá mais peso às palavras raras na coleção.

Fórmula (Okapi BM25), para cada palavra da pergunta que aparece no trecho:
    idf(palavra) * tf * (k1 + 1) / (tf + k1 * (1 - b + b * tamanho / tamanho_medio))
- tf: quantas vezes a palavra aparece no trecho;
- idf: quanto mais rara a palavra na coleção, maior o peso;
- k1: limita o ganho de repetir a mesma palavra muitas vezes;
- b: desconta trechos longos (que têm mais palavras "por acaso").
"""

import math
import re
import unicodedata
from collections import Counter

# Palavras muito comuns (português e inglês) que não ajudam a achar o trecho certo
STOPWORDS = set(
    """
    a o as os um uma uns umas de do da dos das no na nos nas em por para pra com sem
    e ou que se como qual quais quando onde porque por que é ser são foi está estão
    eu voce vc meu minha isso esse essa este esta ao aos à às mais menos ja tem ter
    the an of to in on at by for with from and or is are be was were it its this
    that these those as if then than can how what which when where why do does you
    your not no
    """.split()
)


def tokenizar(texto: str) -> list[str]:
    """Minúsculas, sem acentos, só letras/números/_ e sem stopwords."""
    sem_acento = unicodedata.normalize("NFKD", texto.lower())
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    palavras = re.findall(r"[a-z0-9_]+", sem_acento)
    return [p for p in palavras if p not in STOPWORDS and (len(p) > 1 or p.isdigit())]


def passa_no_filtro(metadados: dict, filtros: dict | None) -> bool:
    """Aceita os mesmos filtros simples que usamos no Chroma: {campo: valor} ou {"$and": [...]}."""
    if not filtros:
        return True
    if "$and" in filtros:
        return all(passa_no_filtro(metadados, condicao) for condicao in filtros["$and"])
    return all(metadados.get(campo) == valor for campo, valor in filtros.items())


class IndiceBM25:
    def __init__(self, ids, textos, metadados, k1: float = 1.5, b: float = 0.75):
        self.ids = list(ids)
        self.textos = list(textos)
        self.metadados = [m or {} for m in metadados]
        self.k1 = k1
        self.b = b
        self.contagens = [Counter(tokenizar(t)) for t in self.textos]
        self.tamanhos = [sum(c.values()) for c in self.contagens]
        self.tamanho_medio = (sum(self.tamanhos) / len(self.tamanhos)) if self.tamanhos else 0.0
        # Em quantos trechos cada palavra aparece (document frequency)
        frequencia = Counter()
        for contagem in self.contagens:
            frequencia.update(contagem.keys())
        total = len(self.textos)
        self.idf = {
            palavra: math.log((total - df + 0.5) / (df + 0.5) + 1)
            for palavra, df in frequencia.items()
        }

    @classmethod
    def da_colecao(cls, colecao, **parametros) -> "IndiceBM25":
        """Monta o índice com todos os trechos já guardados numa coleção do Chroma."""
        dados = colecao.get(include=["documents", "metadatas"])
        return cls(dados["ids"], dados["documents"], dados["metadatas"], **parametros)

    def pontuar(self, consulta: str) -> list[float]:
        palavras = set(tokenizar(consulta))
        pontos = []
        for contagem, tamanho in zip(self.contagens, self.tamanhos, strict=True):
            total = 0.0
            for palavra in palavras:
                tf = contagem.get(palavra, 0)
                if not tf:
                    continue
                normalizacao = 1 - self.b + self.b * tamanho / (self.tamanho_medio or 1)
                total += self.idf[palavra] * tf * (self.k1 + 1) / (tf + self.k1 * normalizacao)
            pontos.append(total)
        return pontos

    def buscar(self, consulta: str, k: int = 5, filtros: dict | None = None) -> list[dict]:
        """Os k trechos com maior pontuação. Trechos sem nenhuma palavra em comum ficam de fora."""
        pontos = self.pontuar(consulta)
        ordem = sorted(range(len(pontos)), key=lambda i: pontos[i], reverse=True)
        resultados = []
        for i in ordem:
            if pontos[i] <= 0 or not passa_no_filtro(self.metadados[i], filtros):
                continue
            resultados.append(
                {
                    "id": self.ids[i],
                    "texto": self.textos[i],
                    "metadados": self.metadados[i],
                    "distancia": None,  # BM25 não tem distância, só pontuação
                    "pontuacao_bm25": pontos[i],
                }
            )
            if len(resultados) == k:
                break
        return resultados
