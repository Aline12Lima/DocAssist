"""Histórico das perguntas do /rag/ask no PostgreSQL.

Se o banco falhar, a resposta ainda chega ao usuário: o registro é perdido e o erro vai
para o log. Guardar o histórico nunca pode derrubar a pergunta.
"""

import logging

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database.models import RagInteracao

logger = logging.getLogger(__name__)


def registrar_interacao(
    db: Session, resultado: dict, filtros: dict | None, index_version: int, do_cache: bool
) -> str | None:
    meta = resultado["meta"]
    interacao = RagInteracao(
        pergunta=resultado["pergunta"],
        resposta=resultado["resposta"],
        encontrou_resposta=resultado["encontrou_resposta"],
        aviso=resultado["aviso"],
        filtros=filtros,
        chunk_ids_recuperados=meta.get("chunk_ids_recuperados", []),
        chunk_ids_citados=[c["chunk_id"] for c in resultado["citacoes"]]
        if resultado["encontrou_resposta"]
        else [],
        modelo=meta["modelo"],
        prompt_version=meta["prompt_version"],
        tokens_entrada=0 if do_cache else meta["tokens_entrada"],  # do cache: nada foi gasto
        tokens_saida=0 if do_cache else meta["tokens_saida"],
        tentativas=0 if do_cache else meta["tentativas"],
        distancia_top1=meta["distancia_top1"],
        latencia_ms=meta["latencia_ms"],
        index_version=index_version,
        do_cache=do_cache,
    )
    try:
        db.add(interacao)
        db.commit()
        return interacao.id
    except SQLAlchemyError as erro:
        db.rollback()
        logger.error("Não foi possível registrar a interação: %s", erro)
        return None


def listar_interacoes(db: Session, limite: int = 20, so_sem_resposta: bool = False):
    consulta = db.query(RagInteracao)
    if so_sem_resposta:
        consulta = consulta.filter(RagInteracao.encontrou_resposta.is_(False))
    return consulta.order_by(RagInteracao.criado_em.desc()).limit(limite).all()
