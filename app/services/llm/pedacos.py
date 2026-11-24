"""Ajudantes para texto que chega aos pedaços (streaming)."""

ABRE, FECHA = "<think>", "</think>"


def sobra_parcial(texto: str, marca: str) -> int:
    """Quantos caracteres do fim de `texto` podem ser o começo de `marca`."""
    for tamanho in range(min(len(marca) - 1, len(texto)), 0, -1):
        if marca.startswith(texto[-tamanho:]):
            return tamanho
    return 0


class FiltroDePensamento:
    """Tira o "pensamento em voz alta" (<think>...</think>) de um texto que chega aos pedaços.

    A dificuldade: uma marca pode chegar partida, "<thi" num pedaço e "nk>" no outro.
    Por isso guardamos o fim do texto que ainda pode virar uma marca.
    """

    def __init__(self):
        self.guardado = ""
        self.pensando = False

    def filtrar(self, pedaco: str) -> str:
        self.guardado += pedaco
        saida = []
        while True:
            if self.pensando:
                fim = self.guardado.find(FECHA)
                if fim == -1:
                    sobra = sobra_parcial(self.guardado, FECHA)
                    self.guardado = self.guardado[len(self.guardado) - sobra :]
                    return "".join(saida)
                self.guardado = self.guardado[fim + len(FECHA) :]
                self.pensando = False
            else:
                inicio = self.guardado.find(ABRE)
                if inicio == -1:
                    sobra = sobra_parcial(self.guardado, ABRE)
                    saida.append(self.guardado[: len(self.guardado) - sobra])
                    self.guardado = self.guardado[len(self.guardado) - sobra :]
                    return "".join(saida)
                saida.append(self.guardado[:inicio])
                self.guardado = self.guardado[inicio + len(ABRE) :]
                self.pensando = True

    def terminar(self) -> str:
        """O que sobrou no fim (se não estiver dentro de um <think>)."""
        resto = "" if self.pensando else self.guardado
        self.guardado = ""
        return resto
