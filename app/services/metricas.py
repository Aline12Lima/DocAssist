"""Métricas do RAG para o Prometheus (expostas em /metrics, junto com as de HTTP).

O Prometheus visita /metrics de tempos em tempos e guarda os números. Três tipos:
- Counter: só sobe (quantas respostas, quantos bloqueios). Olha-se a taxa: rate(...[5m]).
- Histogram: distribui valores em faixas (buckets), para calcular percentis, ex. o tempo
  que 95% das perguntas levam até o primeiro pedaço de texto.
- Labels: dividem a métrica, ex. resultado="respondeu" ou "nao_encontrou".

Cuidado com labels de valores livres (a pergunta, o id): cada valor diferente vira uma
série nova no Prometheus. Aqui só usamos labels com poucos valores possíveis.
"""

from prometheus_client import Counter, Histogram

FAIXAS_DE_TEMPO = (0.05, 0.1, 0.25, 0.5, 1, 2, 3, 5, 8, 13, 20, 30)

RESPOSTAS = Counter(
    "docassist_rag_respostas_total",
    "Respostas do /rag/ask e do /rag/ask/stream",
    ["rota", "resultado", "origem"],
)
TEMPO_POR_ETAPA = Histogram(
    "docassist_rag_etapa_segundos",
    "Tempo de cada etapa do pipeline do RAG",
    ["etapa"],
    buckets=FAIXAS_DE_TEMPO,
)
TOKENS = Counter("docassist_rag_tokens_total", "Tokens gastos com o LLM", ["tipo"])
BLOQUEIOS = Counter(
    "docassist_rag_limite_bloqueios_total", "Perguntas barradas pelo limite por minuto"
)
VOTOS = Counter("docassist_rag_feedback_total", "Votos de feedback", ["util"])


def classificar(resultado: dict) -> tuple[str, str]:
    """(resultado, origem) de uma resposta, para os labels."""
    meta = resultado["meta"]
    if meta.get("falha_do_llm"):
        tipo = "falha_llm"
    elif resultado["encontrou_resposta"]:
        tipo = "respondeu"
    else:
        tipo = "nao_encontrou"
    if meta.get("cache"):
        origem = "cache"
    elif meta.get("tentativas"):
        origem = "llm"
    else:
        origem = "sem_llm"  # recusada pelo limiar, antes de chamar o LLM
    return tipo, origem


def registrar_resposta(resultado: dict, rota: str) -> None:
    tipo, origem = classificar(resultado)
    RESPOSTAS.labels(rota=rota, resultado=tipo, origem=origem).inc()
    meta = resultado["meta"]
    TEMPO_POR_ETAPA.labels(etapa="total").observe(meta["latencia_ms"] / 1000)
    if origem == "cache":
        return  # os tempos guardados no cache são da primeira vez, não desta
    etapas = {
        "busca": meta.get("tempo_busca_ms"),
        "reranker": meta.get("tempo_reranker_ms"),
        "llm": meta.get("tempo_llm_ms"),
        "primeiro_pedaco": meta.get("tempo_primeiro_pedaco_ms"),
    }
    for etapa, ms in etapas.items():
        if ms is not None:
            TEMPO_POR_ETAPA.labels(etapa=etapa).observe(ms / 1000)
    TOKENS.labels(tipo="entrada").inc(meta.get("tokens_entrada") or 0)
    TOKENS.labels(tipo="saida").inc(meta.get("tokens_saida") or 0)


def registrar_bloqueio() -> None:
    BLOQUEIOS.inc()


def registrar_voto(util: bool) -> None:
    VOTOS.labels(util="sim" if util else "nao").inc()
