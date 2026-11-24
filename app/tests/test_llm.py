"""Testes dos provedores de LLM com respostas HTTP simuladas (nenhuma chamada de verdade)."""

import json

import httpx
import pytest

from app.config import settings
from app.services.llm.base import ErroDeLimite, ErroDoProvedor, RespostaLLM
from app.services.llm.cadeia import CadeiaDeProvedores, criar_cadeia, ler_lista_de_modelos
from app.services.llm.compativel_openai import ProvedorCompativelOpenAI
from app.services.llm.pedacos import FiltroDePensamento

MENSAGENS = [{"role": "user", "content": "oi"}]


def provedor_com_resposta(status: int, corpo: dict) -> ProvedorCompativelOpenAI:
    """Um provedor cujo servidor responde sempre `status` e `corpo`."""
    pedidos = []

    def responder(pedido: httpx.Request) -> httpx.Response:
        pedidos.append(pedido)
        return httpx.Response(status, json=corpo)

    cliente = httpx.Client(transport=httpx.MockTransport(responder))
    provedor = ProvedorCompativelOpenAI(
        "groq", "https://exemplo.test/v1", "chave", "modelo-a", cliente_http=cliente
    )
    provedor.pedidos = pedidos
    return provedor


def resposta_ok(texto: str) -> dict:
    return {
        "choices": [{"message": {"content": texto}}],
        "usage": {"prompt_tokens": 12, "completion_tokens": 3},
    }


def test_resposta_com_texto_e_tokens():
    provedor = provedor_com_resposta(200, resposta_ok("Olá [1]"))

    resposta = provedor.gerar(MENSAGENS, max_tokens=50, temperatura=0.1)

    assert resposta == RespostaLLM("Olá [1]", "groq:modelo-a", 12, 3)


def test_envia_chave_modelo_e_parametros():
    provedor = provedor_com_resposta(200, resposta_ok("ok"))

    provedor.gerar(MENSAGENS, max_tokens=50, temperatura=0.1)

    pedido = provedor.pedidos[0]
    assert pedido.url == "https://exemplo.test/v1/chat/completions"
    assert pedido.headers["Authorization"] == "Bearer chave"
    assert b'"model":"modelo-a"' in pedido.content.replace(b" ", b"")


def test_remove_o_pensamento_do_modelo():
    provedor = provedor_com_resposta(
        200, resposta_ok("<think>vou pensar...</think>\nResposta final")
    )

    assert provedor.gerar(MENSAGENS, 50, 0.1).texto == "Resposta final"


def test_429_vira_erro_de_limite():
    provedor = provedor_com_resposta(429, {"error": "rate limit"})

    with pytest.raises(ErroDeLimite):
        provedor.gerar(MENSAGENS, 50, 0.1)


def test_resposta_vazia_vira_erro():
    provedor = provedor_com_resposta(200, resposta_ok(""))

    with pytest.raises(ErroDoProvedor):
        provedor.gerar(MENSAGENS, 50, 0.1)


class ProvedorFalso:
    def __init__(self, nome: str, erro: Exception | None = None):
        self.nome = nome
        self.erro = erro
        self.chamadas = 0

    def gerar(self, mensagens, max_tokens, temperatura):
        self.chamadas += 1
        if self.erro:
            raise self.erro
        return RespostaLLM("ok", self.nome, 1, 1)


def test_cadeia_usa_o_proximo_quando_o_primeiro_chega_ao_limite():
    primeiro = ProvedorFalso("groq:a", ErroDeLimite("429"))
    segundo = ProvedorFalso("gemini:b")

    resposta = CadeiaDeProvedores([primeiro, segundo]).gerar(MENSAGENS, 50, 0.1)

    assert resposta.modelo == "gemini:b"
    assert primeiro.chamadas == 1


def test_cadeia_nao_chama_o_segundo_se_o_primeiro_responde():
    primeiro, segundo = ProvedorFalso("groq:a"), ProvedorFalso("gemini:b")

    CadeiaDeProvedores([primeiro, segundo]).gerar(MENSAGENS, 50, 0.1)

    assert segundo.chamadas == 0


def test_cadeia_falha_quando_todos_falham():
    cadeia = CadeiaDeProvedores(
        [
            ProvedorFalso("groq:a", ErroDeLimite("429")),
            ProvedorFalso("gemini:b", ErroDoProvedor("fora")),
        ]
    )

    with pytest.raises(ErroDoProvedor, match="Todos os provedores falharam"):
        cadeia.gerar(MENSAGENS, 50, 0.1)


def test_ler_lista_de_modelos():
    assert ler_lista_de_modelos("groq:openai/gpt-oss-120b, gemini:flash-lite,") == [
        ("groq", "openai/gpt-oss-120b"),
        ("gemini", "flash-lite"),
    ]


def test_criar_cadeia_pula_provedor_sem_chave(monkeypatch):
    monkeypatch.setattr(settings, "LLM_MODELOS", "groq:modelo-a,gemini:modelo-b")
    monkeypatch.setattr(settings, "GROQ_API_KEY", "chave-groq")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")

    cadeia = criar_cadeia()

    assert [p.nome for p in cadeia.provedores] == ["groq:modelo-a"]


def test_criar_cadeia_sem_nenhuma_chave_avisa(monkeypatch):
    monkeypatch.setattr(settings, "GROQ_API_KEY", "")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")

    with pytest.raises(ValueError, match="Nenhum provedor"):
        criar_cadeia()


# ---------- streaming


def provedor_com_stream(status: int, linhas: list[str]) -> ProvedorCompativelOpenAI:
    corpo = "".join(f"{linha}\n\n" for linha in linhas)

    def responder(pedido: httpx.Request) -> httpx.Response:
        return httpx.Response(status, text=corpo, headers={"content-type": "text/event-stream"})

    cliente = httpx.Client(transport=httpx.MockTransport(responder))
    return ProvedorCompativelOpenAI(
        "groq", "https://exemplo.test/v1", "chave", "modelo-a", cliente_http=cliente
    )


def pedaco(texto: str) -> str:
    return "data: " + json.dumps({"choices": [{"delta": {"content": texto}}]})


def test_stream_junta_os_pedacos_e_para_no_done():
    provedor = provedor_com_stream(
        200,
        [pedaco("Olá"), ": comentário do SSE", pedaco(" mundo [1]"), "data: [DONE]", pedaco("x")],
    )
    assert list(provedor.gerar_em_partes(MENSAGENS, 50, 0.1)) == ["Olá", " mundo [1]"]


def test_stream_tira_o_pensamento_mesmo_partido():
    provedor = provedor_com_stream(
        200, [pedaco("<thi"), pedaco("nk>pensando..."), pedaco("</th"), pedaco("ink>Resposta")]
    )
    assert "".join(provedor.gerar_em_partes(MENSAGENS, 50, 0.1)) == "Resposta"


def test_stream_429_vira_erro_de_limite():
    provedor = provedor_com_stream(429, [])
    with pytest.raises(ErroDeLimite):
        list(provedor.gerar_em_partes(MENSAGENS, 50, 0.1))


class ProvedorDePedacos:
    def __init__(self, nome, pedacos, erro_depois=None):
        self.nome, self.pedacos, self.erro_depois = nome, pedacos, erro_depois

    def gerar_em_partes(self, mensagens, max_tokens, temperatura):
        yield from self.pedacos
        if self.erro_depois:
            raise self.erro_depois


def test_cadeia_troca_de_provedor_antes_do_primeiro_pedaco():
    cadeia = CadeiaDeProvedores(
        [
            ProvedorDePedacos("a", [], ErroDeLimite("a: 429")),
            ProvedorDePedacos("b", ["oi", " [1]"]),
        ]
    )
    assert list(cadeia.gerar_em_partes(MENSAGENS, 50, 0.1)) == ["oi", " [1]"]
    assert cadeia.ultimo_modelo == "b"


def test_cadeia_nao_troca_depois_que_comecou():
    cadeia = CadeiaDeProvedores(
        [
            ProvedorDePedacos("a", ["começo"], ErroDoProvedor("a: caiu")),
            ProvedorDePedacos("b", ["outro texto"]),
        ]
    )
    with pytest.raises(ErroDoProvedor):
        list(cadeia.gerar_em_partes(MENSAGENS, 50, 0.1))


def test_filtro_de_pensamento_sem_pensamento_passa_tudo():
    filtro = FiltroDePensamento()
    texto = filtro.filtrar("a < b e <th") + filtro.filtrar("e") + filtro.terminar()
    assert texto == "a < b e <the"
