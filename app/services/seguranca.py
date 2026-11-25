"""Quem está chamando a API (autenticação) e quantas vezes pode chamar (limite de uso).

Autenticação por chave de API: o cliente manda a chave no cabeçalho X-API-Key.
- API_KEYS vazio no .env: API aberta (desenvolvimento). Cada cliente é identificado pelo IP.
- API_KEYS preenchido: sem chave válida, 401. Cada cliente é identificado pela chave.
- DEMO_PUBLICO=true (Fase 10): quem chega SEM chave ainda pode perguntar e votar, como
  visitante. Uma chave publicada no README não protegeria nada, então o visitante não
  precisa de chave: o que protege é o limite. O visitante tem limite menor por minuto
  (contado por IP) e um teto diário somando todos os visitantes, que protege a cota
  gratuita do Groq e do Gemini. Ingerir, apagar e ver o histórico continuam exigindo a
  chave de administração (API_KEYS).

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


ADMIN = "admin"
DEMO = "demo"


def _separar(texto: str) -> list[str]:
    return [chave.strip() for chave in texto.split(",") if chave.strip()]


def chaves_validas() -> list[str]:
    return _separar(settings.API_KEYS)


def _confere(chave: str | None, lista: list[str]) -> bool:
    # compare_digest leva o mesmo tempo acerte ou erre, para não vazar a chave por tempo
    return bool(chave) and any(secrets.compare_digest(chave, valida) for valida in lista)


@dataclass
class Cliente:
    id: str  # usado na contagem do limite; nunca contém a chave em si
    papel: str  # ADMIN (tudo) ou DEMO (visitante: só perguntar e votar)


def ip_do_cliente(request: Request) -> str:
    """O IP de quem chamou. Atrás de um proxy (Railway), o IP real vem em X-Forwarded-For.

    Só confiamos nesse cabeçalho se CONFIAR_X_FORWARDED_FOR=true: sem um proxy na frente,
    qualquer um pode mandar um X-Forwarded-For falso e fugir do limite.
    """
    if settings.CONFIAR_X_FORWARDED_FOR:
        # A Railway sobrescreve o X-Real-IP na borda com o IP de quem conectou; um valor
        # mandado pelo próprio cliente não sobrevive. Por isso ele vem antes do X-Forwarded-For.
        real = request.headers.get("x-real-ip")
        if real:
            return real.strip()
        encaminhado = request.headers.get("x-forwarded-for")
        if encaminhado:
            return encaminhado.split(",")[0].strip()
    return request.client.host if request.client else "desconhecido"


def identificar_quem_pergunta(
    request: Request, chave: str | None = Security(esquema_da_chave)
) -> Cliente:
    """Dependência das rotas de perguntar e votar: aceita a chave e, na demo, o visitante."""
    chaves = chaves_validas()
    if not chaves:
        return Cliente(f"ip:{ip_do_cliente(request)}", ADMIN)
    if _confere(chave, chaves):
        # Nunca guardamos a chave em si: só um resumo dela, para separar os clientes
        return Cliente(f"chave:{hashlib.sha256(chave.encode()).hexdigest()[:12]}", ADMIN)
    if not chave and settings.DEMO_PUBLICO:
        # Visitante sem chave: o limite é contado por IP. Chave ERRADA continua dando 401,
        # para quem digitou a chave errada perceber, em vez de virar visitante sem saber.
        return Cliente(f"demo:ip:{ip_do_cliente(request)}", DEMO)
    raise HTTPException(
        status_code=401,
        detail="Chave de API ausente ou inválida. Envie no cabeçalho X-API-Key.",
        headers={"WWW-Authenticate": "ApiKey"},
    )


def identificar_cliente(request: Request, chave: str | None = Security(esquema_da_chave)) -> str:
    """Dependência das rotas administrativas (ingerir, apagar, ver histórico): só com chave."""
    cliente = identificar_quem_pergunta(request, chave)
    if cliente.papel == DEMO:
        raise HTTPException(
            status_code=401,
            detail="Esta ação exige a chave de administração. Visitantes só perguntam e votam.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return cliente.id


def relogio() -> float:
    """O relógio, numa função só para os testes poderem trocar."""
    return time.time()


@dataclass
class Uso:
    permitido: bool
    usados: int
    limite: int
    espera_s: int  # segundos até o próximo minuto


def _contar(cliente_redis, prefixo: str, limite: int, janela_s: int, instante: float) -> Uso:
    """Janela fixa: uma chave por janela (minuto ou dia), com o número da janela no nome."""
    janela = int(instante // janela_s)
    espera = janela_s - int(instante % janela_s)
    if cliente_redis is None:
        return Uso(True, 0, limite, espera)  # sem Redis, não há como contar: deixa passar
    chave = f"{prefixo}:{janela}"
    try:
        usados = cliente_redis.incr(chave)
        if usados == 1:
            cliente_redis.expire(chave, 2 * janela_s)
    except redis.RedisError as erro:
        logger.warning("Limite de uso desligado, Redis indisponível: %s", erro)
        return Uso(True, 0, limite, espera)
    return Uso(usados <= limite, usados, limite, espera)


def registrar_uso(cliente_redis, cliente: str, limite: int, instante: float | None = None) -> Uso:
    """Conta mais um pedido do cliente no minuto atual."""
    instante = relogio() if instante is None else instante
    return _contar(cliente_redis, f"rl:{cliente}", limite, 60, instante)


def registrar_uso_do_dia(
    cliente_redis, grupo: str, limite: int, instante: float | None = None
) -> Uso:
    """Conta mais um pedido do grupo (ex.: todos os visitantes da demo) no dia atual, em UTC."""
    instante = relogio() if instante is None else instante
    return _contar(cliente_redis, f"rl:{grupo}:dia", limite, 86_400, instante)
