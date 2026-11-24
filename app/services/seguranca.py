"""Quem está chamando a API (autenticação) e quantas vezes pode chamar (limite de uso).

Autenticação por chave de API: o cliente manda a chave no cabeçalho X-API-Key.
- API_KEYS vazio no .env: API aberta (desenvolvimento). Cada cliente é identificado pelo IP.
- API_KEYS preenchido: sem chave válida, 401. Cada cliente é identificado pela chave.

Limite de uso com janela fixa no Redis (o padrão "rate limiter" da documentação do INCR):
uma chave por cliente e por minuto, ex. "rl:ip:1.2.3.4:29400123". Cada pedido faz INCR;
passou do limite, 429. O EXPIRE só faz a limpeza: como o minuto está no nome da chave,
um minuto novo começa sempre do zero, mesmo se o EXPIRE falhar.
"""

import hashlib
import logging
import secrets
import time
from dataclasses import dataclass

import redis
from fastapi import HTTPException, Request, Security
from fastapi.security import APIKeyHeader

from app.config import settings

logger = logging.getLogger(__name__)

# auto_error=False: a falta da chave é tratada abaixo (só é erro se houver chaves configuradas).
# Usar APIKeyHeader faz o /docs ganhar o botão "Authorize".
esquema_da_chave = APIKeyHeader(name="X-API-Key", auto_error=False)


def chaves_validas() -> list[str]:
    return [chave.strip() for chave in settings.API_KEYS.split(",") if chave.strip()]


def ip_do_cliente(request: Request) -> str:
    """O IP de quem chamou. Atrás de um proxy (Railway), o IP real vem em X-Forwarded-For.

    Só confiamos nesse cabeçalho se CONFIAR_X_FORWARDED_FOR=true: sem um proxy na frente,
    qualquer um pode mandar um X-Forwarded-For falso e fugir do limite.
    """
    encaminhado = request.headers.get("x-forwarded-for")
    if settings.CONFIAR_X_FORWARDED_FOR and encaminhado:
        return encaminhado.split(",")[0].strip()
    return request.client.host if request.client else "desconhecido"


def identificar_cliente(request: Request, chave: str | None = Security(esquema_da_chave)) -> str:
    """Dependência do FastAPI: devolve quem é o cliente ou responde 401."""
    chaves = chaves_validas()
    if not chaves:
        return f"ip:{ip_do_cliente(request)}"
    # compare_digest leva o mesmo tempo acerte ou erre, para não vazar a chave por tempo
    if not chave or not any(secrets.compare_digest(chave, valida) for valida in chaves):
        raise HTTPException(
            status_code=401,
            detail="Chave de API ausente ou inválida. Envie no cabeçalho X-API-Key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    # Nunca guardamos a chave em si: só um resumo dela, para separar os clientes
    return f"chave:{hashlib.sha256(chave.encode()).hexdigest()[:12]}"


def relogio() -> float:
    """O relógio, numa função só para os testes poderem trocar."""
    return time.time()


@dataclass
class Uso:
    permitido: bool
    usados: int
    limite: int
    espera_s: int  # segundos até o próximo minuto


def registrar_uso(cliente_redis, cliente: str, limite: int, instante: float | None = None) -> Uso:
    """Conta mais um pedido do cliente no minuto atual."""
    instante = relogio() if instante is None else instante
    minuto = int(instante // 60)
    espera = 60 - int(instante % 60)
    if cliente_redis is None:
        return Uso(True, 0, limite, espera)  # sem Redis, não há como contar: deixa passar
    chave = f"rl:{cliente}:{minuto}"
    try:
        usados = cliente_redis.incr(chave)
        if usados == 1:
            cliente_redis.expire(chave, 120)
    except redis.RedisError as erro:
        logger.warning("Limite de uso desligado, Redis indisponível: %s", erro)
        return Uso(True, 0, limite, espera)
    return Uso(usados <= limite, usados, limite, espera)
