"""As métricas do RAG sobem quando devem."""

from prometheus_client import REGISTRY

from app.services.metricas import classificar, registrar_resposta


def valor(nome: str, **labels) -> float:
    return REGISTRY.get_sample_value(nome, labels) or 0.0


def resultado(encontrou=True, cache=False, tentativas=1, falha=False, **tempos):
    meta = {
        "cache": cache,
        "tentativas": tentativas,
        "falha_do_llm": falha,
        "latencia_ms": 3000,
        "tokens_entrada": 100,
        "tokens_saida": 20,
        **tempos,
    }
    return {"encontrou_resposta": encontrou, "meta": meta}


def test_classifica_resultado_e_origem():
    assert classificar(resultado()) == ("respondeu", "llm")
    assert classificar(resultado(encontrou=False, tentativas=0)) == ("nao_encontrou", "sem_llm")
    assert classificar(resultado(cache=True)) == ("respondeu", "cache")
    assert classificar(resultado(encontrou=False, falha=True)) == ("falha_llm", "llm")


def test_registrar_conta_a_resposta_e_os_tempos_por_etapa():
    labels = {"rota": "ask", "resultado": "respondeu", "origem": "llm"}
    antes = valor("docassist_rag_respostas_total", **labels)
    reranker_antes = valor("docassist_rag_etapa_segundos_count", etapa="reranker")

    registrar_resposta(resultado(tempo_busca_ms=200, tempo_reranker_ms=2900), rota="ask")

    assert valor("docassist_rag_respostas_total", **labels) == antes + 1
    assert valor("docassist_rag_etapa_segundos_count", etapa="reranker") == reranker_antes + 1


def test_resposta_do_cache_nao_conta_os_tempos_antigos():
    antes = valor("docassist_rag_etapa_segundos_count", etapa="llm")
    registrar_resposta(resultado(cache=True, tempo_llm_ms=5000), rota="stream")
    assert valor("docassist_rag_etapa_segundos_count", etapa="llm") == antes
