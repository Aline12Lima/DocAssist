"""Chunker: divide as seções em pedaços que cabem no modelo de embedding.

Regras:
- seções pequenas demais são juntadas à seguinte;
- seções grandes são divididas por parágrafos, com sobreposição (overlap);
- blocos de código nunca são cortados no meio;
- cada chunk começa com o prefixo "Documento › Seção", que conta no limite.
"""

from collections.abc import Callable
from dataclasses import dataclass

from app.services.rag.parsers import Secao

ContadorDeTokens = Callable[[str], int]
CERCA_DE_CODIGO = ("```", "~~~")


@dataclass
class Chunk:
    texto: str  # prefixo + conteúdo: é isto que vira vetor
    conteudo: str  # só o conteúdo, sem o prefixo
    caminho: list[str]
    posicao: int
    pagina: int | None = None
    tem_codigo: bool = False


def montar_prefixo(caminho: list[str]) -> str:
    return " › ".join(caminho)


def eh_codigo(bloco: str) -> bool:
    return bloco.lstrip().startswith(CERCA_DE_CODIGO)


# ---------------------------------------------------------------------------
# 1. Juntar seções pequenas
# ---------------------------------------------------------------------------


def prefixo_comum(a: list[str], b: list[str]) -> list[str]:
    comum = []
    for x, y in zip(a, b, strict=False):
        if x != y:
            break
        comum.append(x)
    return comum


def mesclar(a: Secao, b: Secao) -> Secao:
    """Une duas seções. O caminho vira a parte em comum; os subtítulos entram no texto."""
    comum = prefixo_comum(a.caminho, b.caminho)

    def rotular(secao: Secao) -> str:
        return secao.texto if secao.caminho == comum else f"{secao.titulo}\n{secao.texto}"

    return Secao(
        titulo=comum[-1] if comum else a.titulo,
        caminho=comum or a.caminho,
        texto=f"{rotular(a)}\n\n{rotular(b)}",
        pagina=a.pagina,
    )


def juntar_secoes_pequenas(
    secoes: list[Secao], minimo: int, contar: ContadorDeTokens
) -> list[Secao]:
    resultado: list[Secao] = []
    acumulada: Secao | None = None
    for secao in secoes:
        if acumulada is None:
            acumulada = secao
        elif contar(acumulada.texto) < minimo:
            acumulada = mesclar(acumulada, secao)
        else:
            resultado.append(acumulada)
            acumulada = secao
    if acumulada is not None:
        resultado.append(acumulada)
    return resultado


# ---------------------------------------------------------------------------
# 2. Dividir uma seção em blocos (parágrafos e blocos de código)
# ---------------------------------------------------------------------------


def dividir_em_blocos(texto: str) -> list[str]:
    """Separa nas linhas em branco, mas mantém cada bloco de código inteiro."""
    blocos: list[str] = []
    atual: list[str] = []
    em_codigo = False
    for linha in texto.splitlines():
        if linha.strip().startswith(CERCA_DE_CODIGO):
            em_codigo = not em_codigo
        if not linha.strip() and not em_codigo:
            if atual:
                blocos.append("\n".join(atual))
                atual = []
            continue
        atual.append(linha)
    if atual:
        blocos.append("\n".join(atual))
    return blocos


def cortar_por_palavras(bloco: str, limite: int, contar: ContadorDeTokens) -> list[str]:
    """Corta um parágrafo grande demais em pedaços de até `limite` tokens."""
    partes: list[str] = []
    atual: list[str] = []
    for palavra in bloco.split():
        if atual and contar(" ".join([*atual, palavra])) > limite:
            partes.append(" ".join(atual))
            atual = []
        atual.append(palavra)
    if atual:
        partes.append(" ".join(atual))
    return partes


def cauda(bloco: str, overlap: int, contar: ContadorDeTokens) -> str:
    """As últimas palavras de um bloco, até `overlap` tokens. Código não é repetido."""
    if overlap <= 0 or eh_codigo(bloco):
        return ""
    palavras = bloco.split()
    inicio = len(palavras)
    while inicio > 0 and contar(" ".join(palavras[inicio - 1 :])) <= overlap:
        inicio -= 1
    return " ".join(palavras[inicio:])


# ---------------------------------------------------------------------------
# 3. Empacotar os blocos em chunks
# ---------------------------------------------------------------------------


def empacotar(blocos: list[str], limite: int, overlap: int, contar: ContadorDeTokens) -> list[str]:
    pedacos: list[str] = []
    atual: list[str] = []
    for bloco in blocos:
        if atual and contar("\n\n".join([*atual, bloco])) > limite:
            pedacos.append("\n\n".join(atual))
            repeticao = cauda(atual[-1], overlap, contar)
            cabe = repeticao and contar(f"{repeticao}\n\n{bloco}") <= limite
            atual = [repeticao] if cabe else []
        atual.append(bloco)
    if atual:
        pedacos.append("\n\n".join(atual))
    return pedacos


def gerar_chunks(
    secoes: list[Secao],
    contar: ContadorDeTokens,
    limite: int = 250,
    overlap: int = 30,
    minimo: int = 50,
) -> list[Chunk]:
    """Transforma as seções de um documento em chunks numerados (posição 0, 1, 2...)."""
    chunks: list[Chunk] = []
    for secao in juntar_secoes_pequenas(secoes, minimo, contar):
        prefixo = montar_prefixo(secao.caminho)
        espaco = max(limite - contar(prefixo) - 2, 32)  # o prefixo também ocupa tokens

        blocos: list[str] = []
        for bloco in dividir_em_blocos(secao.texto):
            if contar(bloco) <= espaco or eh_codigo(bloco):
                blocos.append(bloco)  # código grande demais vira um chunk só, inteiro
            else:
                blocos.extend(cortar_por_palavras(bloco, max(espaco - overlap, 16), contar))

        for conteudo in empacotar(blocos, espaco, overlap, contar):
            chunks.append(
                Chunk(
                    texto=f"{prefixo}\n\n{conteudo}" if prefixo else conteudo,
                    conteudo=conteudo,
                    caminho=secao.caminho,
                    posicao=len(chunks),
                    pagina=secao.pagina,
                    tem_codigo="```" in conteudo,
                )
            )
    return chunks
