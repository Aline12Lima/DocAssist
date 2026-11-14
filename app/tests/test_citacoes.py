"""Testes da validação de citações [n]."""

from app.services.rag.citacoes import validar_citacoes


def test_extrai_citacoes_na_ordem_sem_repetir():
    resultado = validar_citacoes("Use healthcheck [2]. Depois depends_on [1][2].", 3)

    assert resultado.citados == [2, 1]
    assert resultado.invalidas == []


def test_aceita_citacoes_separadas_por_virgula():
    resultado = validar_citacoes("Isso funciona [1, 3].", 3)

    assert resultado.citados == [1, 3]
    assert resultado.texto == "Isso funciona [1][3]."


def test_remove_citacao_que_nao_existe():
    resultado = validar_citacoes("Afirmação certa [1]. Afirmação inventada [7].", 5)

    assert resultado.citados == [1]
    assert resultado.invalidas == [7]
    assert resultado.texto == "Afirmação certa [1]. Afirmação inventada."


def test_zero_tambem_e_invalido():
    assert validar_citacoes("Texto [0].", 5).invalidas == [0]


def test_sem_citacoes():
    resultado = validar_citacoes("Resposta sem nenhuma fonte.", 5)

    assert resultado.citados == []
    assert resultado.texto == "Resposta sem nenhuma fonte."


def test_nao_confunde_lista_de_codigo_com_citacao():
    resultado = validar_citacoes('Use `test: ["CMD", "pg_isready"]` [1].', 2)

    assert resultado.citados == [1]
    assert '["CMD", "pg_isready"]' in resultado.texto


def test_nao_mexe_no_espaco_antes_de_pontuacao_no_codigo():
    texto = "Exemplo [1]:\n\n```yaml\nweb:\n  build: .\n```"

    assert "build: ." in validar_citacoes(texto, 2).texto


def test_aceita_colchetes_orientais():
    resultado = validar_citacoes("Ele espera o healthcheck【1】【3】.", 3)

    assert resultado.citados == [1, 3]
    assert resultado.texto == "Ele espera o healthcheck[1][3]."


def test_indice_dentro_de_codigo_nao_e_citacao():
    texto = "Use `lista[1]` e `x[0]`, como no trecho [2].\n\n```python\nprint(itens[3])\n```"

    resultado = validar_citacoes(texto, 2)

    assert resultado.citados == [2]
    assert resultado.invalidas == []
    assert "`lista[1]`" in resultado.texto
    assert "itens[3]" in resultado.texto
