"""Cache das respostas do /rag/ask no Redis.

A chave leva a versão do índice e a versão do prompt:

    rag:ans:<versão do índice>:<versão do prompt>:<hash da pergunta + filtros + k>

Cada ingestão ou remoção soma 1 à versão do índice. As chaves antigas deixam de ser
encontradas na hora, sem precisar apagar uma por uma, e o TTL as remove depois.

Se o Redis estiver fora do ar, o /rag/ask continua funcionando, só que sem cache.
"""

import hashlib
import json
import logging
import re

import redis

logger = logging.getLogger(__name__)

CHAVE_VERSAO_DO_INDICE = "rag:index_version"


def normalizar_pergunta(pergunta: str) -> str:
    """'  Como uso o TTL?? ' e 'como uso o ttl' viram a mesma pergunta."""
    texto = " ".join(pergunta.lower().split())
    return re.sub(r"[\s?!.]+$", "", texto)


def versao_do_indice(cliente) -> int:
    if cliente is None:
        return 0
    try:
        return int(cliente.get(CHAVE_VERSAO_DO_INDICE) or 0)
    except redis.RedisError as erro:
        logger.warning("Redis indisponível ao ler a versão do índice: %s", erro)
        return 0


def invalidar(cliente) -> None:
    """Chamado depois de toda ingestão ou remoção: as respostas antigas deixam de valer."""
    if cliente is None:
        return
    try:
        nova = cliente.incr(CHAVE_VERSAO_DO_INDICE)
        logger.info("Versão do índice agora é %s: cache de respostas invalidado", nova)
    except redis.RedisError as erro:
        logger.warning("Redis indisponível ao invalidar o cache: %s", erro)


def montar_chave(pergunta: str, filtros: dict | None, k: int, versao: int, prompt: str) -> str:
    conteudo = json.dumps(
        {"pergunta": normalizar_pergunta(pergunta), "filtros": filtros, "k": k}, sort_keys=True
    )
    resumo = hashlib.sha256(conteudo.encode("utf-8")).hexdigest()[:24]
    return f"rag:ans:{versao}:{prompt}:{resumo}"


def buscar_resposta(cliente, chave: str) -> dict | None:
    if cliente is None:
        return None
    try:
        guardada = cliente.get(chave)
    except redis.RedisError as erro:
        logger.warning("Redis indisponível ao buscar no cache: %s", erro)
        return None
    return json.loads(guardada) if guardada else None


def guardar_resposta(cliente, chave: str, resultado: dict, ttl_segundos: int) -> None:
    if cliente is None:
        return
    try:
        cliente.setex(chave, ttl_segundos, json.dumps(resultado, ensure_ascii=False))
    except redis.RedisError as erro:
        logger.warning("Redis indisponível ao guardar no cache: %s", erro)
