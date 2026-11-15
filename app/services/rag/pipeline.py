"""Pipeline do /rag/ask: buscar → reordenar → decidir se dá para responder → gerar → validar.

A API nunca devolve erro 500 por causa do LLM: se ele falhar ou não citar as fontes,
a resposta traz os trechos encontrados e um aviso explicando o que aconteceu.
"""

import logging
import time

from app.config import settings
from app.services.llm.base import ErroDoProvedor
from app.services.rag.citacoes import validar_citacoes
from app.services.rag.geracao import eh_sem_resposta, montar_mensagens, versao_do_prompt
from app.services.rag.vetores import buscar

logger = logging.getLogger(__name__)

NAO_ENCONTREI = "Não encontrei essa informação nos documentos carregados."
FALHA_DO_LLM = "Não foi possível gerar a resposta agora. Veja abaixo os trechos encontrados."
SEM_CITACAO = (
    "A resposta gerada não indicou as fontes, por isso não foi exibida. "
    "Veja abaixo os trechos encontrados."
)


def montar_citacao(n: int, trecho: dict) -> dict:
    metadados = trecho["metadados"]
    return {
        "n": n,
        "chunk_id": trecho["id"],
        "doc_id": metadados.get("doc_id"),
        "titulo": metadados.get("titulo"),
        "secao": metadados.get("secao"),
        "pagina": metadados.get("pagina"),
        "url": metadados.get("url"),
        "trecho": trecho["texto"],
        "distancia": round(trecho["distancia"], 4),
        "nota_reranker": arredondar(trecho.get("pontuacao_reranker"), 2),
    }


def arredondar(valor, casas: int):
    return round(valor, casas) if valor is not None else None


def assinatura_da_recuperacao(reranker) -> str:
    """Resume a configuração da busca; entra na chave do cache (mudou a busca, muda a chave)."""
    if reranker is None:
        return f"vetorial:{settings.RAG_LIMIAR_DISTANCIA}"
    return (
        f"reranker:{reranker.nome}:{settings.RAG_RERANKER_CANDIDATOS}:"
        f"{settings.RAG_LIMIAR_RERANKER}"
    )


def recuperar(pergunta, colecao, embedder, k: int, filtros, reranker) -> list[dict]:
    """Sem reranker: os k mais próximos. Com reranker: N candidatos, reordenados, os k melhores."""
    if reranker is None:
        return buscar(pergunta, colecao, embedder, k=k, filtros=filtros)
    candidatos = buscar(
        pergunta,
        colecao,
        embedder,
        k=max(settings.RAG_RERANKER_CANDIDATOS, k),
        filtros=filtros,
    )
    return reranker.reordenar(pergunta, candidatos, k=k)


def abaixo_do_limiar(trechos: list[dict], reranker) -> bool:
    """O melhor trecho é fraco demais para valer uma chamada ao LLM?"""
    if not trechos:
        return True
    if reranker is not None:
        return trechos[0]["pontuacao_reranker"] < settings.RAG_LIMIAR_RERANKER
    return trechos[0]["distancia"] > settings.RAG_LIMIAR_DISTANCIA


def responder(
    pergunta: str,
    colecao,
    embedder,
    llm,
    k: int | None = None,
    filtros: dict | None = None,
    reranker=None,
) -> dict:
    inicio = time.perf_counter()
    trechos = recuperar(
        pergunta, colecao, embedder, k or settings.RAG_TOP_K_CONTEXTO, filtros, reranker
    )
    meta = {
        "modelo": None,
        "prompt_version": versao_do_prompt(),
        "tokens_entrada": 0,
        "tokens_saida": 0,
        "tentativas": 0,
        "citacoes_invalidas": [],
        "distancia_top1": round(trechos[0]["distancia"], 4) if trechos else None,
        "reranker": reranker.nome if reranker is not None else None,
        "nota_reranker_top1": arredondar(trechos[0].get("pontuacao_reranker"), 2)
        if trechos
        else None,
        "tempo_reranker_ms": int(reranker.ultimo_tempo_ms) if reranker is not None else None,
        "chunk_ids_recuperados": [t["id"] for t in trechos],
        "falha_do_llm": False,  # True = não vale guardar no cache
        "cache": False,
    }
    mais_proximos = [montar_citacao(n, t) for n, t in enumerate(trechos[:3], start=1)]

    def resultado(resposta: str, encontrou: bool, citacoes: list, aviso: str | None = None):
        meta["latencia_ms"] = int((time.perf_counter() - inicio) * 1000)
        return {
            "pergunta": pergunta,
            "resposta": resposta,
            "encontrou_resposta": encontrou,
            "citacoes": citacoes,
            "aviso": aviso,
            "meta": meta,
        }

    # 1. Nada relevante o bastante: "não encontrei", sem gastar uma chamada ao LLM
    if abaixo_do_limiar(trechos, reranker):
        return resultado(
            NAO_ENCONTREI,
            False,
            mais_proximos,
            "Trechos mais próximos, abaixo do limiar de relevância.",
        )
    if llm is None:
        meta["falha_do_llm"] = True
        return resultado(FALHA_DO_LLM, False, mais_proximos, "Nenhum provedor de LLM configurado.")

    # 2. Gerar; se vier sem citações, tentar mais uma vez com a regra reforçada
    for reforco in (False, True):
        try:
            gerada = llm.gerar(
                montar_mensagens(pergunta, trechos, reforco),
                settings.LLM_MAX_TOKENS,
                settings.LLM_TEMPERATURA,
            )
        except ErroDoProvedor as erro:
            logger.error("Falha ao gerar resposta: %s", erro)
            meta["falha_do_llm"] = True
            return resultado(
                FALHA_DO_LLM,
                False,
                mais_proximos,
                "Os provedores de LLM não responderam (limite de uso ou indisponibilidade).",
            )

        meta["tentativas"] += 1
        meta["modelo"] = gerada.modelo
        meta["tokens_entrada"] += gerada.tokens_entrada
        meta["tokens_saida"] += gerada.tokens_saida

        if eh_sem_resposta(gerada.texto):
            return resultado(
                NAO_ENCONTREI,
                False,
                mais_proximos,
                "O modelo indicou que os trechos não respondem à pergunta.",
            )

        validadas = validar_citacoes(gerada.texto, len(trechos))
        meta["citacoes_invalidas"] = validadas.invalidas
        if validadas.citados:
            citacoes = [montar_citacao(n, trechos[n - 1]) for n in sorted(validadas.citados)]
            aviso = None
            if validadas.invalidas:
                aviso = f"Citações inexistentes removidas: {validadas.invalidas}"
            return resultado(validadas.texto, True, citacoes, aviso)

    todos = [montar_citacao(n, t) for n, t in enumerate(trechos, start=1)]
    return resultado(
        SEM_CITACAO, False, todos, "O modelo respondeu duas vezes sem citar as fontes."
    )
