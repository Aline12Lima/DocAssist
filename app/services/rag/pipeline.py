"""Pipeline do /rag/ask: buscar → reordenar → decidir se dá para responder → gerar → validar.

A API nunca devolve erro 500 por causa do LLM: se ele falhar ou não citar as fontes,
a resposta traz os trechos encontrados e um aviso explicando o que aconteceu.
"""

import logging
import time
from collections.abc import Iterator

from app.config import settings
from app.services.llm.base import ErroDoProvedor
from app.services.rag.citacoes import validar_citacoes
from app.services.rag.geracao import (
    SEM_RESPOSTA,
    eh_sem_resposta,
    montar_mensagens,
    versao_do_prompt,
)
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


class Preparo:
    """O que as duas versões do /rag/ask (inteira e em streaming) fazem antes do LLM."""

    def __init__(self, pergunta, colecao, embedder, k, filtros, reranker):
        self.inicio = time.perf_counter()
        self.pergunta = pergunta
        self.trechos = recuperar(
            pergunta, colecao, embedder, k or settings.RAG_TOP_K_CONTEXTO, filtros, reranker
        )
        recuperacao_ms = (time.perf_counter() - self.inicio) * 1000
        reranker_ms = reranker.ultimo_tempo_ms if reranker is not None else 0
        self.reranker = reranker
        trechos = self.trechos
        self.meta = {
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
            "tempo_reranker_ms": int(reranker_ms) if reranker is not None else None,
            # Quanto tempo cada etapa levou (as métricas do Prometheus usam estes números)
            "tempo_busca_ms": int(recuperacao_ms - reranker_ms),
            "tempo_llm_ms": None,
            "tempo_primeiro_pedaco_ms": None,
            "chunk_ids_recuperados": [t["id"] for t in trechos],
            "falha_do_llm": False,  # True = não vale guardar no cache
            "cache": False,
        }
        self.mais_proximos = [montar_citacao(n, t) for n, t in enumerate(trechos[:3], start=1)]

    def resultado(self, resposta: str, encontrou: bool, citacoes: list, aviso: str | None = None):
        self.meta["latencia_ms"] = int((time.perf_counter() - self.inicio) * 1000)
        return {
            "pergunta": self.pergunta,
            "resposta": resposta,
            "encontrou_resposta": encontrou,
            "citacoes": citacoes,
            "aviso": aviso,
            "meta": self.meta,
        }

    def sem_llm(self, llm) -> dict | None:
        """Resposta que não precisa do LLM (nada relevante ou nenhum LLM); senão, None."""
        if abaixo_do_limiar(self.trechos, self.reranker):
            return self.resultado(
                NAO_ENCONTREI,
                False,
                self.mais_proximos,
                "Trechos mais próximos, abaixo do limiar de relevância.",
            )
        if llm is None:
            self.meta["falha_do_llm"] = True
            return self.resultado(
                FALHA_DO_LLM, False, self.mais_proximos, "Nenhum provedor de LLM configurado."
            )
        return None

    def falha(self, erro: Exception) -> dict:
        logger.error("Falha ao gerar resposta: %s", erro)
        self.meta["falha_do_llm"] = True
        return self.resultado(
            FALHA_DO_LLM,
            False,
            self.mais_proximos,
            "Os provedores de LLM não responderam (limite de uso ou indisponibilidade).",
        )

    def interpretar(self, texto: str) -> dict | None:
        """Texto do LLM → resultado final; None se ele não citou nenhum trecho válido."""
        if eh_sem_resposta(texto):
            return self.resultado(
                NAO_ENCONTREI,
                False,
                self.mais_proximos,
                "O modelo indicou que os trechos não respondem à pergunta.",
            )
        validadas = validar_citacoes(texto, len(self.trechos))
        self.meta["citacoes_invalidas"] = validadas.invalidas
        if not validadas.citados:
            return None
        citacoes = [montar_citacao(n, self.trechos[n - 1]) for n in sorted(validadas.citados)]
        aviso = None
        if validadas.invalidas:
            aviso = f"Citações inexistentes removidas: {validadas.invalidas}"
        return self.resultado(validadas.texto, True, citacoes, aviso)

    def sem_citacao(self, aviso: str) -> dict:
        todos = [montar_citacao(n, t) for n, t in enumerate(self.trechos, start=1)]
        return self.resultado(SEM_CITACAO, False, todos, aviso)


def responder(
    pergunta: str,
    colecao,
    embedder,
    llm,
    k: int | None = None,
    filtros: dict | None = None,
    reranker=None,
) -> dict:
    preparo = Preparo(pergunta, colecao, embedder, k, filtros, reranker)

    # 1. Nada relevante o bastante (ou nenhum LLM): responde sem gastar uma chamada
    rapido = preparo.sem_llm(llm)
    if rapido:
        return rapido

    # 2. Gerar; se vier sem citações, tentar mais uma vez com a regra reforçada
    inicio_llm = time.perf_counter()
    for reforco in (False, True):
        try:
            gerada = llm.gerar(
                montar_mensagens(pergunta, preparo.trechos, reforco),
                settings.LLM_MAX_TOKENS,
                settings.LLM_TEMPERATURA,
            )
        except ErroDoProvedor as erro:
            return preparo.falha(erro)
        finally:
            preparo.meta["tempo_llm_ms"] = int((time.perf_counter() - inicio_llm) * 1000)

        preparo.meta["tentativas"] += 1
        preparo.meta["modelo"] = gerada.modelo
        preparo.meta["tokens_entrada"] += gerada.tokens_entrada
        preparo.meta["tokens_saida"] += gerada.tokens_saida

        final = preparo.interpretar(gerada.texto)
        if final:
            return final

    return preparo.sem_citacao("O modelo respondeu duas vezes sem citar as fontes.")


class SegurarSentinela:
    """Segura o começo do texto enquanto ele ainda pode ser "NÃO ENCONTRADO".

    Assim a pessoa não vê "NÃO ENC..." aparecer na tela para depois virar
    "Não encontrei essa informação nos documentos".
    """

    def __init__(self):
        self.guardado = ""
        self.liberado = False

    def receber(self, pedaco: str) -> str:
        if self.liberado:
            return pedaco
        self.guardado += pedaco
        inicio = self.guardado.lstrip().upper()
        if SEM_RESPOSTA.startswith(inicio) or inicio.startswith(SEM_RESPOSTA):
            return ""
        self.liberado = True
        texto, self.guardado = self.guardado, ""
        return texto


def responder_em_partes(
    pergunta: str,
    colecao,
    embedder,
    llm,
    k: int | None = None,
    filtros: dict | None = None,
    reranker=None,
) -> Iterator[dict]:
    """Versão em streaming do responder. Produz eventos:

    - {"evento": "parcial", "dados": {"texto": "..."}}: pedaços da resposta, conforme o
      modelo escreve. É uma prévia: as citações ainda não foram conferidas.
    - {"evento": "fim", "dados": {...}}: o resultado final, igual ao do /rag/ask.
      O texto do "fim" é o oficial e substitui a prévia.

    Diferenças para o responder: não há segunda tentativa (a pessoa já leu a primeira) e
    os tokens ficam 0 (as APIs não informam o uso no streaming sem configuração extra).
    """
    preparo = Preparo(pergunta, colecao, embedder, k, filtros, reranker)
    rapido = preparo.sem_llm(llm)
    if rapido:
        yield {"evento": "fim", "dados": rapido}
        return

    segurar = SegurarSentinela()
    partes = []
    inicio_llm = time.perf_counter()
    try:
        for pedaco in llm.gerar_em_partes(
            montar_mensagens(pergunta, preparo.trechos),
            settings.LLM_MAX_TOKENS,
            settings.LLM_TEMPERATURA,
        ):
            partes.append(pedaco)
            visivel = segurar.receber(pedaco)
            if visivel:
                if preparo.meta["tempo_primeiro_pedaco_ms"] is None:
                    # desde o início do pedido: é o que a pessoa espera olhando a tela
                    preparo.meta["tempo_primeiro_pedaco_ms"] = int(
                        (time.perf_counter() - preparo.inicio) * 1000
                    )
                yield {"evento": "parcial", "dados": {"texto": visivel}}
    except ErroDoProvedor as erro:
        preparo.meta["tempo_llm_ms"] = int((time.perf_counter() - inicio_llm) * 1000)
        yield {"evento": "fim", "dados": preparo.falha(erro)}
        return

    preparo.meta["tempo_llm_ms"] = int((time.perf_counter() - inicio_llm) * 1000)

    preparo.meta["tentativas"] = 1
    preparo.meta["modelo"] = getattr(llm, "ultimo_modelo", None)
    final = preparo.interpretar("".join(partes).strip())
    if final is None:
        final = preparo.sem_citacao("O modelo respondeu sem citar as fontes.")
    yield {"evento": "fim", "dados": final}
