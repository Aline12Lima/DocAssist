"""Testes do juiz (com LLM falso) e da medida de concordância."""

import pytest

from app.services.avaliacao.concordancia import kappa_de_cohen, medir_concordancia
from app.services.avaliacao.juiz import (
    VereditoInvalido,
    julgar,
    ler_veredito,
    montar_mensagens_do_juiz,
)
from app.services.avaliacao.perturbacoes import (
    detectou,
    documento_principal,
    escolher_outro,
    gerar_casos,
)
from app.tests.fakes import LLMFalso

ITEM = {
    "pergunta": "O que faz a opção XX do EXPIRE?",
    "resposta_referencia": "Só define a expiração se a chave já tiver uma.",
    "resposta": "Define a expiração apenas se a chave já tem uma [1].",
    "citacoes": [{"n": 1, "trecho": "XX -- Set expiry only when the key has an existing expiry"}],
}


def test_le_json_simples():
    texto = '{"correcao": 2, "fidelidade": 1, "justificativa": "ok"}'
    assert ler_veredito(texto) == {"correcao": 2, "fidelidade": 1, "justificativa": "ok"}


def test_le_json_com_cercas_e_texto_em_volta():
    texto = 'Aqui está:\n```json\n{"correcao": 1, "fidelidade": 2, "justificativa": "x"}\n```'
    assert ler_veredito(texto)["correcao"] == 1


@pytest.mark.parametrize(
    "texto",
    [
        "sem json nenhum",
        '{"correcao": 3, "fidelidade": 1}',
        '{"correcao": "2", "fidelidade": 1}',
        '{"correcao": true, "fidelidade": 1}',
        '{"fidelidade": 1}',
        '{"correcao": 2, "fidelidade": ',
    ],
)
def test_recusa_veredito_invalido(texto):
    with pytest.raises(VereditoInvalido):
        ler_veredito(texto)


def test_mensagens_levam_referencia_resposta_e_trechos():
    mensagens = montar_mensagens_do_juiz(ITEM)
    assert "Correção" in mensagens[0]["content"]  # o prompt judge_v1
    usuario = mensagens[1]["content"]
    assert ITEM["resposta_referencia"] in usuario
    assert ITEM["resposta"] in usuario
    assert "[1] XX -- Set expiry" in usuario


def test_julgar_devolve_as_notas_e_o_modelo():
    llm = LLMFalso('{"correcao": 2, "fidelidade": 2, "justificativa": "Bate com a referência."}')
    veredito = julgar(ITEM, llm)
    assert (veredito.correcao, veredito.fidelidade) == (2, 2)
    assert veredito.modelo == "falso:modelo"


def test_julgar_pede_de_novo_quando_o_json_vem_quebrado():
    llm = LLMFalso("Nota: correção 2", '{"correcao": 2, "fidelidade": 1, "justificativa": "x"}')
    veredito = julgar(ITEM, llm)
    assert veredito.fidelidade == 1
    assert "JSON" in llm.mensagens_recebidas[1][-1]["content"]


def test_julgar_desiste_depois_da_segunda_tentativa():
    with pytest.raises(VereditoInvalido):
        julgar(ITEM, LLMFalso("nada", "ainda nada"))


def test_kappa_perfeito_e_igual_ao_acaso():
    assert kappa_de_cohen([0, 1, 2, 2], [0, 1, 2, 2]) == pytest.approx(1.0)
    # metade igual, com as mesmas proporções de notas: kappa 0
    assert kappa_de_cohen([0, 0, 1, 1], [0, 1, 0, 1]) == pytest.approx(0.0)


def test_concordancia_exata_e_ate_um_ponto():
    resultado = medir_concordancia([2, 2, 1, 0], [2, 1, 1, 2])
    assert resultado["total"] == 4
    assert resultado["exata"] == pytest.approx(0.5)
    assert resultado["ate_um"] == pytest.approx(0.75)


def test_concordancia_sem_dados():
    assert medir_concordancia([], [])["kappa"] is None


# ---------- respostas estragadas (perturbacoes.py)


def registros_de_exemplo():
    registros = []
    for i, doc in enumerate(["redis-ttl", "fastapi-body", "docker-compose-networking", "pg"]):
        registros.append(
            {
                "id": f"q{i:02d}",
                "deve_responder": True,
                "respondeu": True,
                "resposta": f"resposta {i} [1].",
                "citacoes": [{"n": 1, "doc_id": doc, "trecho": f"trecho {i}"}],
            }
        )
    registros.append({**registros[0], "id": "q99", "respondeu": False})  # fica de fora
    return registros


def test_gera_quatro_versoes_por_resposta():
    casos = gerar_casos(registros_de_exemplo(), quantidade=2)
    assert len(casos) == 8
    assert [c["caso"] for c in casos[:4]] == [
        "original",
        "resposta_trocada",
        "afirmacao_inventada",
        "trechos_trocados",
    ]
    assert all(c["id"] != "q99" for c in casos)


def test_versoes_estragadas_mudam_so_o_que_deviam():
    original, trocada, inventada, trechos = gerar_casos(registros_de_exemplo(), quantidade=1)
    assert trocada["resposta"] != original["resposta"]
    assert trocada["citacoes"] == original["citacoes"]
    assert inventada["resposta"].startswith(original["resposta"].rstrip())
    assert inventada["resposta"].endswith("[1].")
    assert trechos["resposta"] == original["resposta"]
    assert trechos["citacoes"][0]["n"] == 1
    assert trechos["citacoes"][0]["doc_id"] != original["citacoes"][0]["doc_id"]


def test_escolhe_sempre_outro_documento():
    registros = registros_de_exemplo()[:4]
    for i in range(4):
        assert documento_principal(escolher_outro(registros, i)) != documento_principal(
            registros[i]
        )


def test_criterio_de_deteccao():
    assert detectou("resposta_trocada", 0, 0) is True
    assert detectou("resposta_trocada", 2, 0) is False
    assert detectou("afirmacao_inventada", 2, 1) is True
    assert detectou("trechos_trocados", 2, 2) is False
    assert detectou("original", 2, 2) is None


def test_judge_v2_aceita_a_lista_de_afirmacoes():
    texto = (
        '{"afirmacoes": [{"afirmacao": "x", "apoiada": false}], "responde_a_pergunta": "sim", '
        '"contradiz_referencia": false, "correcao": 2, "fidelidade": 1, "justificativa": "y"}'
    )
    assert ler_veredito(texto)["fidelidade"] == 1
    assert "Passo 1" in montar_mensagens_do_juiz(ITEM, "judge_v2")[0]["content"]
