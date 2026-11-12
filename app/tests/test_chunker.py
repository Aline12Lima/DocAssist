"""Testes do chunker. Aqui um "token" é uma palavra, para os números serem fáceis de conferir."""

from app.services.rag.chunker import gerar_chunks, juntar_secoes_pequenas
from app.services.rag.parsers import Secao


def contar_palavras(texto: str) -> int:
    return len(texto.split())


def palavras(n: int, base: str = "p") -> str:
    return " ".join(f"{base}{i}" for i in range(n))


def test_secao_que_cabe_vira_um_chunk_com_prefixo():
    secoes = [Secao("Exit Status", ["pg_isready", "Exit Status"], "returns 0 when ready")]

    chunks = gerar_chunks(secoes, contar_palavras, limite=50, overlap=5, minimo=1)

    assert len(chunks) == 1
    assert chunks[0].texto == "pg_isready › Exit Status\n\nreturns 0 when ready"
    assert chunks[0].conteudo == "returns 0 when ready"


def test_nenhum_chunk_passa_do_limite_contando_o_prefixo():
    secoes = [
        Secao("Longa", ["Doc", "Longa"], "\n\n".join(palavras(20, f"b{i}_") for i in range(10)))
    ]

    chunks = gerar_chunks(secoes, contar_palavras, limite=60, overlap=5, minimo=1)

    assert len(chunks) > 1
    assert all(contar_palavras(c.texto) <= 60 for c in chunks)


def test_chunks_vizinhos_se_sobrepoem():
    secoes = [Secao("Longa", ["Doc"], "\n\n".join(palavras(20, f"b{i}_") for i in range(6)))]

    chunks = gerar_chunks(secoes, contar_palavras, limite=50, overlap=5, minimo=1)

    fim_do_primeiro = chunks[0].conteudo.split()[-5:]
    comeco_do_segundo = chunks[1].conteudo.split()[:5]
    assert fim_do_primeiro == comeco_do_segundo


def test_paragrafo_gigante_e_cortado_por_palavras():
    secoes = [Secao("Gigante", ["Doc"], palavras(200))]

    chunks = gerar_chunks(secoes, contar_palavras, limite=50, overlap=5, minimo=1)

    assert len(chunks) >= 4
    assert all(contar_palavras(c.texto) <= 50 for c in chunks)


def test_bloco_de_codigo_nunca_e_cortado():
    codigo = "```\n" + "\n".join(f"linha {i}" for i in range(40)) + "\n```"
    secoes = [Secao("Exemplo", ["Doc"], f"Rode assim:\n\n{codigo}\n\nE pronto.")]

    chunks = gerar_chunks(secoes, contar_palavras, limite=30, overlap=5, minimo=1)

    com_codigo = [c for c in chunks if c.tem_codigo]
    assert len(com_codigo) == 1
    assert codigo in com_codigo[0].conteudo


def test_codigo_nao_e_repetido_no_overlap():
    codigo = "```\n" + palavras(20, "c") + "\n```"
    secoes = [Secao("Exemplo", ["Doc"], f"{codigo}\n\n{palavras(30, 't')}")]

    chunks = gerar_chunks(secoes, contar_palavras, limite=30, overlap=5, minimo=1)

    assert sum("```" in c.conteudo for c in chunks) == 1


def test_secoes_pequenas_sao_juntadas_com_a_seguinte():
    secoes = [
        Secao("Args", ["TTL", "Args"], "key"),
        Secao("Examples", ["TTL", "Examples"], palavras(20)),
    ]

    resultado = juntar_secoes_pequenas(secoes, minimo=10, contar=contar_palavras)

    assert len(resultado) == 1
    assert resultado[0].caminho == ["TTL"]  # o caminho vira a parte em comum
    assert resultado[0].texto.startswith("Args\nkey\n\nExamples\n")  # subtítulos vão para o texto


def test_posicoes_sao_sequenciais_no_documento():
    secoes = [
        Secao("A", ["Doc", "A"], palavras(40, "a")),
        Secao("B", ["Doc", "B"], palavras(40, "b")),
    ]

    chunks = gerar_chunks(secoes, contar_palavras, limite=30, overlap=5, minimo=1)

    assert [c.posicao for c in chunks] == list(range(len(chunks)))
