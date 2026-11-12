"""Testes dos parsers de Markdown, HTML e PDF."""

from pathlib import Path

import pymupdf
import pytest

from app.services.rag.parsers import (
    FormatoNaoSuportadoError,
    parse_arquivo,
    parse_html,
    parse_markdown,
    parse_pdf,
)

# ---------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------

MARKDOWN_DOCKER = """---
title: Control startup and shutdown order in Compose
weight: 30
---

You can control the order of service startup.

## Control startup

On startup, Compose does not wait until a container is "ready".

### Example

```bash
# isto é um comentário, não um título
docker compose up
```
"""


def test_markdown_usa_titulo_do_cabecalho_yaml():
    secoes = parse_markdown(MARKDOWN_DOCKER)

    assert secoes[0].caminho == ["Control startup and shutdown order in Compose"]
    assert "weight" not in secoes[0].texto  # o cabeçalho YAML não vira texto


def test_markdown_divide_por_titulos_e_monta_caminho():
    secoes = parse_markdown(MARKDOWN_DOCKER)

    assert [s.titulo for s in secoes] == [
        "Control startup and shutdown order in Compose",
        "Control startup",
        "Example",
    ]
    assert secoes[2].caminho == [
        "Control startup and shutdown order in Compose",
        "Control startup",
        "Example",
    ]


def test_markdown_ignora_hashtag_dentro_de_bloco_de_codigo():
    secoes = parse_markdown(MARKDOWN_DOCKER)

    assert len(secoes) == 3
    assert "# isto é um comentário" in secoes[2].texto


def test_markdown_remove_sujeira_dos_sites():
    texto = """# Query Parameters { #query-parameters }

{* ../../docs_src/query_params/tutorial001_py310.py hl[9] *}

/// tip

Use [Pydantic](https://pydantic.dev) with **all** its <dfn title="x">power</dfn>.

///

{{< clients-example set="cmds" step="ttl" >}}
> TTL mykey
{{< /clients-example >}}
"""
    secoes = parse_markdown(texto)

    assert secoes[0].titulo == "Query Parameters"
    assert "{*" not in secoes[0].texto
    assert "///" not in secoes[0].texto
    assert "{{<" not in secoes[0].texto
    assert "Use Pydantic with all its power." in secoes[0].texto
    assert "> TTL mykey" in secoes[0].texto  # o conteúdo do shortcode fica


def test_markdown_sem_titulos_vira_uma_secao():
    secoes = parse_markdown("Só um parágrafo.", titulo_doc="Nota")

    assert len(secoes) == 1
    assert secoes[0].caminho == ["Nota"]
    assert secoes[0].texto == "Só um parágrafo."


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------

HTML_POSTGRES = """<html>
<head><title>PostgreSQL: Documentation: 16: pg_isready</title></head>
<body>
<div id="pgNavbar"><a href="/">Home</a> Download Support</div>
<div id="docContent">
  <div class="navheader">Prev Up Next</div>
  <h2>Description</h2>
  <p><span class="application">pg_isready</span> is a utility for checking the connection
     status of a server.</p>
  <h2>Examples</h2>
  <pre class="screen">$ pg_isready
# comentário dentro do código
/tmp:5432 - accepting connections</pre>
  <div class="navfooter">Prev Home Next</div>
</div>
<script>console.log("analytics")</script>
</body></html>
"""


def test_html_usa_titulo_da_pagina_e_divide_por_h2():
    secoes = parse_html(HTML_POSTGRES)

    assert [s.titulo for s in secoes] == ["Description", "Examples"]
    assert secoes[0].caminho == ["PostgreSQL: Documentation: 16: pg_isready", "Description"]


def test_html_remove_menu_navegacao_e_scripts():
    texto_completo = " ".join(s.texto for s in parse_html(HTML_POSTGRES))

    for sujeira in ("Download Support", "Prev Up Next", "Prev Home Next", "analytics"):
        assert sujeira not in texto_completo


def test_html_mantem_frase_inteira_e_codigo():
    secoes = parse_html(HTML_POSTGRES)
    descricao = " ".join(secoes[0].texto.split())

    assert "pg_isready is a utility for checking the connection status of a server." in descricao
    assert "# comentário dentro do código" in secoes[1].texto
    assert len(secoes) == 2  # o "#" dentro do <pre> não virou título


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------


def criar_pdf(paginas: list[str], titulo: str = "Manual de teste") -> bytes:
    documento = pymupdf.open()
    for texto in paginas:
        pagina = documento.new_page()
        pagina.insert_text((72, 72), texto)
    documento.set_metadata({"title": titulo})
    conteudo = documento.tobytes()
    documento.close()
    return conteudo


def test_pdf_vira_uma_secao_por_pagina():
    secoes = parse_pdf(criar_pdf(["Primeira página.", "Segunda página."]))

    assert [s.pagina for s in secoes] == [1, 2]
    assert secoes[1].caminho == ["Manual de teste", "Página 2"]
    assert secoes[1].texto == "Segunda página."


def test_pdf_desfaz_hifenizacao_no_fim_da_linha():
    secoes = parse_pdf(criar_pdf(["A conexão foi estabe-\nlecida."]))

    assert "estabelecida" in secoes[0].texto


# ---------------------------------------------------------------------------
# Entrada única
# ---------------------------------------------------------------------------


def test_parse_arquivo_escolhe_parser_pela_extensao(tmp_path: Path):
    arquivo = tmp_path / "nota.md"
    arquivo.write_text("# Nota\n\nTexto.", encoding="utf-8")

    secoes = parse_arquivo(arquivo)

    assert secoes[0].titulo == "Nota"


def test_parse_arquivo_recusa_formato_desconhecido(tmp_path: Path):
    arquivo = tmp_path / "planilha.xlsx"
    arquivo.write_bytes(b"nada")

    with pytest.raises(FormatoNaoSuportadoError):
        parse_arquivo(arquivo)
