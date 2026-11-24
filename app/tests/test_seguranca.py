"""Testes da chave de API e do limite de perguntas por minuto."""

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.routers.rag import obter_redis_rag
from app.services.seguranca import registrar_uso
from app.tests.fakes import RedisFalso, RedisForaDoAr

# ---------- registrar_uso (a contagem em si)


def test_conta_ate_o_limite_e_bloqueia_o_seguinte():
    redis = RedisFalso()
    usos = [registrar_uso(redis, "ip:1", limite=3, instante=600.0) for _ in range(4)]
    assert [u.permitido for u in usos] == [True, True, True, False]
    assert usos[-1].usados == 4


def test_minuto_novo_comeca_do_zero():
    redis = RedisFalso()
    for _ in range(3):
        registrar_uso(redis, "ip:1", limite=3, instante=600.0)
    assert registrar_uso(redis, "ip:1", limite=3, instante=659.0).permitido is False
    assert registrar_uso(redis, "ip:1", limite=3, instante=660.0).permitido is True


def test_clientes_diferentes_tem_contas_separadas():
    redis = RedisFalso()
    registrar_uso(redis, "ip:1", limite=1, instante=600.0)
    assert registrar_uso(redis, "ip:2", limite=1, instante=600.0).permitido is True


def test_espera_ate_o_proximo_minuto_e_expire_so_na_primeira_vez():
    redis = RedisFalso()
    uso = registrar_uso(redis, "ip:1", limite=5, instante=615.0)
    assert uso.espera_s == 45
    assert redis.ttls == {"rl:ip:1:10": 120}


@pytest.mark.parametrize("cliente_redis", [None, RedisForaDoAr()])
def test_sem_redis_deixa_passar(cliente_redis):
    assert registrar_uso(cliente_redis, "ip:1", limite=1, instante=600.0).permitido is True


# ---------- na API (os testes com a base e o LLM falsos estão em test_rag_api.py)


@pytest.fixture
def cliente():
    redis = RedisFalso()
    app.dependency_overrides[obter_redis_rag] = lambda: redis
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_rotas_publicas_nao_pedem_chave(cliente, monkeypatch):
    monkeypatch.setattr(settings, "API_KEYS", "chave-a")
    assert cliente.get("/chat").status_code == 200
    assert cliente.get("/health/").status_code == 200


def test_429_traz_quanto_esperar(cliente, monkeypatch):
    monkeypatch.setattr(settings, "API_KEYS", "")
    monkeypatch.setattr(settings, "RATE_LIMIT_PERGUNTAS_POR_MINUTO", 0)
    resposta = cliente.post("/rag/ask/stream", json={"pergunta": "Oi?"})
    assert resposta.status_code == 429
    assert 1 <= int(resposta.headers["retry-after"]) <= 60
