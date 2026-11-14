"""Testes do histórico de interações com SQLite em memória."""

from app.services.rag.historico import listar_interacoes, registrar_interacao
from app.tests.fakes import sessao_de_teste


def resultado(encontrou: bool = True) -> dict:
    return {
        "pergunta": "O que o TTL retorna?",
        "resposta": "Retorna -1 [1]." if encontrou else "Não encontrei.",
        "encontrou_resposta": encontrou,
        "aviso": None,
        "citacoes": [{"n": 1, "chunk_id": "abc"}],
        "meta": {
            "modelo": "groq:modelo",
            "prompt_version": "answer_v2",
            "tokens_entrada": 1000,
            "tokens_saida": 50,
            "tentativas": 1,
            "distancia_top1": 0.11,
            "latencia_ms": 900,
            "chunk_ids_recuperados": ["abc", "def"],
        },
    }


def test_registra_e_lista_interacao():
    db = sessao_de_teste()

    interacao_id = registrar_interacao(db, resultado(), {"fonte": "redis"}, 3, do_cache=False)

    [salva] = listar_interacoes(db)
    assert salva.id == interacao_id
    assert salva.chunk_ids_citados == ["abc"]
    assert salva.chunk_ids_recuperados == ["abc", "def"]
    assert salva.filtros == {"fonte": "redis"}
    assert salva.index_version == 3
    assert salva.tokens_entrada == 1000


def test_resposta_do_cache_nao_conta_tokens():
    db = sessao_de_teste()

    registrar_interacao(db, resultado(), None, 1, do_cache=True)

    [salva] = listar_interacoes(db)
    assert salva.do_cache is True
    assert salva.tokens_entrada == 0
    assert salva.tentativas == 0


def test_sem_resposta_nao_tem_citados_e_pode_ser_filtrada():
    db = sessao_de_teste()
    registrar_interacao(db, resultado(encontrou=True), None, 1, do_cache=False)
    registrar_interacao(db, resultado(encontrou=False), None, 1, do_cache=False)

    sem_resposta = listar_interacoes(db, so_sem_resposta=True)

    assert len(sem_resposta) == 1
    assert sem_resposta[0].chunk_ids_citados == []


def test_falha_no_banco_nao_derruba_a_resposta():
    class SessaoQuebrada:
        def add(self, *_):
            from sqlalchemy.exc import OperationalError

            raise OperationalError("insert", {}, Exception("banco fora do ar"))

        def rollback(self):
            pass

    assert registrar_interacao(SessaoQuebrada(), resultado(), None, 1, do_cache=False) is None
