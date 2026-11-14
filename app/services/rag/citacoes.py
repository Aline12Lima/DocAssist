"""Citações [n]: extrair da resposta do LLM e remover as que não existem.

O prompt pede citações, mas instrução não é garantia: o modelo pode escrever [7]
quando recebeu só 5 trechos. Por isso toda resposta passa por aqui.

Dentro de código (blocos ``` e `inline`), [1] é índice de lista, não citação:
essas partes ficam intactas.
"""

import re
from dataclasses import dataclass

# Aceita [1], [1][2] e também [1, 2]; guarda o espaço antes para poder removê-lo junto
CITACAO = re.compile(r"(?P<espaco>[ \t]*)\[(?P<numeros>\d+(?:\s*,\s*\d+)*)\]")
CODIGO = re.compile(r"(```.*?```|`[^`\n]*`)", re.DOTALL)
# Alguns modelos escrevem 【1】 (colchetes "orientais") em vez de [1]
COLCHETE_ORIENTAL = re.compile(r"【\s*(\d+(?:\s*,\s*\d+)*)\s*】")
# Citação grudada no fechamento de um bloco de código (```[1]) quebra o Markdown
CITACAO_NA_CERCA = re.compile(r"^([ \t]*```)[ \t]*((?:\[\d+\])+)[ \t]*$", re.MULTILINE)


@dataclass
class CitacoesValidadas:
    texto: str  # resposta sem as citações inválidas
    citados: list[int]  # números válidos, na ordem em que aparecem, sem repetir
    invalidas: list[int]  # números que não correspondem a nenhum trecho


def validar_citacoes(texto: str, total_de_trechos: int) -> CitacoesValidadas:
    citados: list[int] = []
    invalidas: list[int] = []

    def trocar(encontrado: re.Match) -> str:
        validos = []
        for parte in encontrado.group("numeros").split(","):
            numero = int(parte)
            if 1 <= numero <= total_de_trechos:
                validos.append(numero)
                if numero not in citados:
                    citados.append(numero)
            elif numero not in invalidas:
                invalidas.append(numero)
        if not validos:
            return ""  # some a citação e o espaço que vinha antes dela
        return encontrado.group("espaco") + "".join(f"[{n}]" for n in validos)

    # As partes de índice ímpar são código: ficam como estão.
    texto = CITACAO_NA_CERCA.sub(r"\1\n\2", texto)
    partes = CODIGO.split(texto)
    for i in range(0, len(partes), 2):
        partes[i] = CITACAO.sub(trocar, COLCHETE_ORIENTAL.sub(r"[\1]", partes[i]))
    return CitacoesValidadas("".join(partes).strip(), citados, invalidas)
