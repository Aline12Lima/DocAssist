"""Feedback das pessoas sobre as respostas (👍/👎).

É a avaliação que nenhum golden set substitui: perguntas reais, de quem usa. As respostas
com 👎 viram candidatas a novas perguntas do golden set.
"""

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.models import RagFeedback, RagInteracao


class InteracaoInexistente(LookupError):
    """O interacao_id não está no histórico."""


def registrar_feedback(
    db: Session, interacao_id: str, util: bool, comentario: str | None
) -> RagFeedback:
    """Grava o voto. Se a interação já tinha voto, troca (vale o último)."""
    if db.get(RagInteracao, interacao_id) is None:
        raise InteracaoInexistente(interacao_id)
    voto = db.query(RagFeedback).filter_by(interacao_id=interacao_id).one_or_none()
    if voto is None:
        voto = RagFeedback(interacao_id=interacao_id)
        db.add(voto)
    voto.util = util
    voto.comentario = (comentario or "").strip() or None
    db.commit()
    db.refresh(voto)
    return voto


def resumir_feedback(db: Session, limite_negativos: int = 10) -> dict:
    """Totais e as últimas respostas marcadas como não úteis, com a pergunta."""
    total = db.query(func.count(RagFeedback.id)).scalar() or 0
    uteis = db.query(func.count(RagFeedback.id)).filter(RagFeedback.util.is_(True)).scalar() or 0
    negativos = (
        db.query(RagFeedback, RagInteracao)
        .join(RagInteracao, RagFeedback.interacao_id == RagInteracao.id)
        .filter(RagFeedback.util.is_(False))
        .order_by(RagFeedback.atualizado_em.desc())
        .limit(limite_negativos)
        .all()
    )
    return {
        "votos": total,
        "uteis": uteis,
        "nao_uteis": total - uteis,
        "taxa_util": round(uteis / total, 3) if total else None,
        "ultimos_nao_uteis": [
            {
                "interacao_id": interacao.id,
                "pergunta": interacao.pergunta,
                "resposta": interacao.resposta,
                "comentario": voto.comentario,
            }
            for voto, interacao in negativos
        ],
    }
