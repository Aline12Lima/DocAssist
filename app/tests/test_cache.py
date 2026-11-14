"""Testes do cache de respostas com um Redis falso."""

from app.services.rag.cache import (
    buscar_resposta,
    guardar_resposta,
    invalidar,
    montar_chave,
    normalizar_pergunta,
    versao_do_indice,
)
from app.tests.fakes import RedisFalso, RedisForaDoAr


def test_normaliza_maiusculas_espacos_e_pontuacao_final():
    assert normalizar_pergunta("  Como uso o   TTL?? ") == "como uso o ttl"
    assert normalizar_pergunta("como uso o ttl") == "como uso o ttl"


def test_mesma_pergunta_escrita_diferente_tem_a_mesma_chave():
    a = montar_chave("Como uso o TTL?", None, 5, 1, "answer_v2")
    b = montar_chave("como uso o ttl", None, 5, 1, "answer_v2")

    assert a == b


def test_chave_muda_com_indice_prompt_filtro_e_k():
    base = montar_chave("pergunta", None, 5, 1, "answer_v2")

    assert montar_chave("pergunta", None, 5, 2, "answer_v2") != base  # base mudou
    assert montar_chave("pergunta", None, 5, 1, "answer_v1") != base  # prompt mudou
    assert montar_chave("pergunta", {"fonte": "redis"}, 5, 1, "answer_v2") != base
    assert montar_chave("pergunta", None, 3, 1, "answer_v2") != base


def test_guardar_e_buscar_com_ttl():
    redis = RedisFalso()

    guardar_resposta(redis, "rag:ans:x", {"resposta": "ok ç"}, 86400)

    assert buscar_resposta(redis, "rag:ans:x") == {"resposta": "ok ç"}
    assert redis.ttls["rag:ans:x"] == 86400


def test_invalidar_soma_um_na_versao():
    redis = RedisFalso()

    assert versao_do_indice(redis) == 0
    invalidar(redis)
    invalidar(redis)
    assert versao_do_indice(redis) == 2


def test_redis_fora_do_ar_nao_derruba_nada():
    redis = RedisForaDoAr()

    assert versao_do_indice(redis) == 0
    assert buscar_resposta(redis, "rag:ans:x") is None
    guardar_resposta(redis, "rag:ans:x", {}, 10)
    invalidar(redis)


def test_sem_redis_configurado():
    assert versao_do_indice(None) == 0
    assert buscar_resposta(None, "rag:ans:x") is None
