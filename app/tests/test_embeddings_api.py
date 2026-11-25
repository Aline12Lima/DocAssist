"""Testes do embedding pelo Gemini, com a API simulada (httpx.MockTransport)."""

import json
import math

import httpx
import pytest

from app.services.llm.base import ErroDeLimite, ErroDoProvedor
from app.services.rag.embeddings import MODELOS
from app.services.rag.embeddings_api import (
    EmbedderGemini,
    LimiteDeTokens,
    espera_sugerida,
    estimar_tokens,
    normalizar,
)


class Relogio:
    """Relógio de mentira: dormir só avança o tempo, sem esperar de verdade."""

    def __init__(self):
        self.agora = 0.0
        self.dormiu = []

    def __call__(self):
        return self.agora

    def dormir(self, segundos):
        self.dormiu.append(round(segundos, 1))
        self.agora += segundos


def embedder_com(respostas, recebidos, relogio=None, **opcoes):
    """Cada chamada à API devolve a próxima resposta da lista: (status, corpo)."""
    fila = list(respostas)
    relogio = relogio or Relogio()

    def responder(pedido: httpx.Request) -> httpx.Response:
        recebidos.append(pedido)
        status, corpo = fila.pop(0)
        return httpx.Response(status, json=corpo)

    cliente = httpx.Client(transport=httpx.MockTransport(responder))
    padrao = {"dimensoes": 2, "lote": 2}
    return EmbedderGemini(
        MODELOS["gemini"],
        "chave-teste",
        cliente_http=cliente,
        dormir=relogio.dormir,
        relogio=relogio,
        **{**padrao, **opcoes},
    )


def vetores(*listas):
    return {"embeddings": [{"values": v} for v in listas]}


def test_trechos_vao_em_lotes_com_task_type_de_documento():
    recebidos = []
    embedder = embedder_com([(200, vetores([3, 4], [0, 2])), (200, vetores([1, 0]))], recebidos)

    resultado = embedder.vetorizar_trechos(["a", "b", "c"])

    assert len(recebidos) == 2  # lote de 2: duas chamadas para três textos
    corpo = json.loads(recebidos[0].content)
    assert corpo["requests"][0]["taskType"] == "RETRIEVAL_DOCUMENT"
    assert corpo["requests"][0]["outputDimensionality"] == 2
    assert recebidos[0].headers["x-goog-api-key"] == "chave-teste"
    assert recebidos[0].url.path.endswith("gemini-embedding-001:batchEmbedContents")
    assert resultado[0] == pytest.approx([0.6, 0.8])  # normalizado: [3, 4] / 5


def test_lote_tambem_e_cortado_pelo_numero_de_tokens():
    embedder = embedder_com([], [], lote=50, tokens_por_lote=10)
    textos = ["uma duas tres quatro cinco"] * 3  # 7 tokens estimados cada
    assert [len(lote) for lote in embedder.lotes(textos)] == [1, 1, 1]


def test_consulta_usa_task_type_de_pergunta():
    recebidos = []
    embedder = embedder_com([(200, vetores([0, 5]))], recebidos)

    assert embedder.vetorizar_consulta("o que é TTL?") == pytest.approx([0.0, 1.0])
    assert json.loads(recebidos[0].content)["requests"][0]["taskType"] == "RETRIEVAL_QUERY"


def test_429_espera_o_tempo_sugerido_e_tenta_de_novo():
    relogio, recebidos = Relogio(), []
    sugestao = {"error": {"details": [{"retryDelay": "38s"}]}}
    embedder = embedder_com([(429, sugestao), (200, vetores([1, 0]))], recebidos, relogio)

    assert embedder.vetorizar_consulta("x") == pytest.approx([1.0, 0.0])
    assert len(recebidos) == 2
    assert relogio.dormiu == [39.0]  # os 38 s sugeridos + 1 de folga


def test_429_sem_parar_vira_erro_de_limite_com_o_motivo():
    embedder = embedder_com([(429, {"error": {"message": "Quota exceeded"}})] * 5, [])
    with pytest.raises(ErroDeLimite, match="Quota exceeded"):
        embedder.vetorizar_consulta("x")


def test_outro_erro_http_vira_erro_do_provedor():
    embedder = embedder_com([(400, {"error": "modelo errado"})], [])
    with pytest.raises(ErroDoProvedor):
        embedder.vetorizar_consulta("x")


def test_sem_chave_avisa_logo():
    with pytest.raises(ValueError):
        EmbedderGemini(MODELOS["gemini"], "")


def test_limite_de_tokens_espera_a_janela_de_um_minuto():
    relogio = Relogio()
    limite = LimiteDeTokens(100, relogio=relogio, dormir=relogio.dormir)

    limite.aguardar(60)
    limite.aguardar(30)  # 90 de 100: passa direto
    assert relogio.dormiu == []
    limite.aguardar(30)  # passaria de 100: espera o 1º envio sair da janela
    assert relogio.dormiu == [60.1]


def test_espera_sugerida_e_utilidades():
    assert espera_sugerida('{"retryDelay": "12.5s"}') == 12.5
    assert espera_sugerida("sem dica") is None
    assert math.isclose(sum(x * x for x in normalizar([1, 2, 2])), 1.0)
    assert estimar_tokens("O Compose espera o banco?") == 8  # 6 pedaços * 1,3 = 7,8 → 8


def test_falha_de_rede_passageira_tenta_de_novo():
    relogio, recebidos = Relogio(), []
    fila = [httpx.ConnectError("Network is unreachable"), (200, vetores([1, 0]))]

    def responder(pedido):
        recebidos.append(pedido)
        item = fila.pop(0)
        if isinstance(item, Exception):
            raise item
        return httpx.Response(item[0], json=item[1])

    embedder = EmbedderGemini(
        MODELOS["gemini"],
        "chave-teste",
        dimensoes=2,
        cliente_http=httpx.Client(transport=httpx.MockTransport(responder)),
        dormir=relogio.dormir,
        relogio=relogio,
    )

    assert embedder.vetorizar_consulta("x") == pytest.approx([1.0, 0.0])
    assert len(recebidos) == 2
    assert relogio.dormiu == [1]


def test_falha_de_rede_sem_parar_vira_erro_do_provedor():
    def responder(pedido):
        raise httpx.ConnectError("Network is unreachable")

    embedder = EmbedderGemini(
        MODELOS["gemini"],
        "chave-teste",
        cliente_http=httpx.Client(transport=httpx.MockTransport(responder)),
        dormir=lambda s: None,
    )
    with pytest.raises(ErroDoProvedor, match="falha de conexão"):
        embedder.vetorizar_consulta("x")
