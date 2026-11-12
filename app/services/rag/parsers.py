"""Parsers: transformam Markdown, HTML e PDF numa lista de seções.

Todos os formatos devolvem o mesmo tipo, `Secao`, para que as próximas etapas
(chunking, embeddings) não precisem saber de onde o texto veio.
"""

import html
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from bs4 import BeautifulSoup


@dataclass
class Secao:
    titulo: str
    caminho: list[str] = field(default_factory=list)
    texto: str = ""
    pagina: int | None = None


class FormatoNaoSuportadoError(ValueError):
    """O arquivo não é Markdown, HTML nem PDF."""


# ---------------------------------------------------------------------------
# Funções comuns
# ---------------------------------------------------------------------------

TITULO = re.compile(r"^(#{1,3})\s+(.+?)\s*$")
CERCA_DE_CODIGO = ("```", "~~~")


def normalizar_espacos(texto: str) -> str:
    """Limpa espaços extras e junta linhas em branco repetidas.

    Dentro de blocos de código, a indentação é mantida: em YAML e Python ela faz parte
    do significado. Ali só os espaços do fim da linha são removidos.
    """
    linhas = []
    em_codigo = False
    for linha in texto.splitlines():
        if linha.strip().startswith(CERCA_DE_CODIGO):
            em_codigo = not em_codigo
            linhas.append(linha.strip())
        elif em_codigo:
            linhas.append(linha.rstrip())
        else:
            linhas.append(re.sub(r"[ \t]+", " ", linha).strip())
    texto = "\n".join(linhas)
    return re.sub(r"\n{3,}", "\n\n", texto).strip()


def dividir_em_secoes(texto: str, titulo_doc: str | None) -> list[Secao]:
    """Divide um texto com títulos no estilo Markdown (#, ##, ###) em seções.

    Linhas que começam com # dentro de blocos de código não são títulos.
    """
    pilha: list[tuple[int, str]] = [(0, titulo_doc)] if titulo_doc else []
    secoes: list[Secao] = []
    linhas_da_secao: list[str] = []
    em_codigo = False

    def fechar_secao():
        conteudo = normalizar_espacos("\n".join(linhas_da_secao))
        if conteudo:
            secoes.append(
                Secao(
                    titulo=pilha[-1][1] if pilha else "",
                    caminho=[titulo for _, titulo in pilha],
                    texto=conteudo,
                )
            )

    for linha in texto.splitlines():
        if linha.strip().startswith(CERCA_DE_CODIGO):
            em_codigo = not em_codigo

        encontrado = None if em_codigo else TITULO.match(linha)
        if not encontrado:
            linhas_da_secao.append(linha)
            continue

        nivel = len(encontrado.group(1))
        titulo = encontrado.group(2).strip()
        fechar_secao()
        linhas_da_secao = []

        while pilha and pilha[-1][0] >= nivel:
            pilha.pop()
        if pilha and pilha[-1][1] == titulo:
            continue  # título repetido (ex.: o H1 igual ao título do cabeçalho)
        pilha.append((nivel, titulo))

    fechar_secao()
    return secoes


# ---------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------

FRONT_MATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
SHORTCODE = re.compile(r"\{\{[<%].*?[>%]\}\}", re.DOTALL)  # Hugo: {{< ... >}}
INCLUSAO_FASTAPI = re.compile(r"^\{\*.*\*\}\s*$", re.MULTILINE)  # {* arquivo.py *}
CAIXA_DE_AVISO = re.compile(r"^///.*$", re.MULTILINE)  # /// tip ... ///
SEPARADOR_DE_ABAS = re.compile(r"^-tab-sep-\s*$", re.MULTILINE)  # abas do site do Redis
QUEBRA_DE_LINHA = re.compile(r"<br\s*/?>", re.IGNORECASE)
ANCORA = re.compile(r"\s*\{\s*#[^}]*\}\s*$")  # Título { #ancora }
LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")  # [texto](url) -> texto
TAGS_HTML = re.compile(
    r"</?(?:a|abbr|b|br|code|details|dfn|div|em|font|i|img|kbd|li|nobr|p|span|strong"
    r"|sub|summary|sup|table|tbody|td|th|thead|tr|ul)\b[^>]*>",
    re.IGNORECASE,
)


def separar_front_matter(texto: str) -> tuple[dict, str]:
    """Separa o cabeçalho YAML (entre ---) do corpo do Markdown."""
    encontrado = FRONT_MATTER.match(texto)
    if not encontrado:
        return {}, texto
    try:
        metadados = yaml.safe_load(encontrado.group(1)) or {}
    except yaml.YAMLError:
        metadados = {}
    return (metadados if isinstance(metadados, dict) else {}), texto[encontrado.end() :]


def limpar_markdown(texto: str) -> str:
    texto = SHORTCODE.sub("", texto)
    texto = INCLUSAO_FASTAPI.sub("", texto)
    texto = CAIXA_DE_AVISO.sub("", texto)
    texto = SEPARADOR_DE_ABAS.sub("", texto)
    texto = QUEBRA_DE_LINHA.sub(" ", texto)
    texto = TAGS_HTML.sub("", texto)
    texto = LINK.sub(r"\1", texto)
    texto = texto.replace("**", "")
    texto = html.unescape(texto)
    linhas = [
        ANCORA.sub("", linha) if TITULO.match(linha) else linha for linha in texto.splitlines()
    ]
    return "\n".join(linhas)


def parse_markdown(texto: str, titulo_doc: str | None = None) -> list[Secao]:
    metadados, corpo = separar_front_matter(texto)
    titulo_doc = titulo_doc or metadados.get("title")
    return dividir_em_secoes(limpar_markdown(corpo), titulo_doc)


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------

BLOCOS_HTML = ["p", "div", "li", "dt", "dd", "tr", "table", "ul", "ol", "dl", "blockquote"]


def parse_html(texto: str, titulo_doc: str | None = None) -> list[Secao]:
    sopa = BeautifulSoup(texto, "html.parser")
    if not titulo_doc and sopa.title:
        titulo_doc = sopa.title.get_text(strip=True)

    # Só a parte principal da página: o PostgreSQL usa <div id="docContent">.
    conteudo = sopa.find(id="docContent") or sopa.find("main") or sopa.body or sopa

    for tag in conteudo.find_all(["script", "style", "nav", "header", "footer"]):
        tag.decompose()
    for tag in conteudo.find_all(class_=["navheader", "navfooter"]):
        tag.decompose()

    # Títulos viram linhas "## Título"; blocos de código ganham cercas ```.
    for nivel in (1, 2, 3):
        for titulo in conteudo.find_all(f"h{nivel}"):
            titulo.replace_with(f"\n\n{'#' * nivel} {titulo.get_text(' ', strip=True)}\n\n")
    for bloco in conteudo.find_all("pre"):
        bloco.replace_with(f"\n```\n{bloco.get_text()}\n```\n")
    for bloco in conteudo.find_all(BLOCOS_HTML):
        bloco.append("\n")
    for quebra in conteudo.find_all("br"):
        quebra.replace_with("\n")

    return dividir_em_secoes(conteudo.get_text(), titulo_doc)


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------

HIFENIZACAO = re.compile(r"(\w)-\n(\w)")  # "conexõ-\nes" -> "conexões"


def parse_pdf(conteudo: bytes, titulo_doc: str | None = None) -> list[Secao]:
    """PDF não marca títulos: cada página vira uma seção."""
    import pymupdf  # importado aqui para não pesar quem não usa PDF

    secoes = []
    with pymupdf.open(stream=conteudo, filetype="pdf") as documento:
        titulo_doc = titulo_doc or (documento.metadata or {}).get("title") or None
        for numero, pagina in enumerate(documento, start=1):
            texto = normalizar_espacos(HIFENIZACAO.sub(r"\1\2", pagina.get_text()))
            if not texto:
                continue
            nome = f"Página {numero}"
            caminho = [titulo_doc, nome] if titulo_doc else [nome]
            secoes.append(Secao(titulo=nome, caminho=caminho, texto=texto, pagina=numero))
    return secoes


# ---------------------------------------------------------------------------
# Entrada única
# ---------------------------------------------------------------------------


def parse_arquivo(caminho: Path, titulo_doc: str | None = None) -> list[Secao]:
    """Escolhe o parser pela extensão do arquivo."""
    sufixo = caminho.suffix.lower()
    if sufixo in (".md", ".markdown"):
        return parse_markdown(caminho.read_text(encoding="utf-8"), titulo_doc)
    if sufixo in (".html", ".htm"):
        return parse_html(caminho.read_text(encoding="utf-8"), titulo_doc)
    if sufixo == ".pdf":
        return parse_pdf(caminho.read_bytes(), titulo_doc)
    raise FormatoNaoSuportadoError(f"Formato não suportado: {sufixo}. Aceitos: PDF, MD, HTML")
