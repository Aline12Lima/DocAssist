import uuid

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.sql import func

from app.database.connection import Base


class NLPHistory(Base):
    __tablename__ = "nlp_history"

    id = Column(Integer, primary_key=True, index=True)
    operation = Column(String(50), nullable=False, index=True)
    input_text = Column(Text, nullable=False)
    result = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class RagInteracao(Base):
    """Cada pergunta feita ao /rag/ask: o que foi respondido, com quais trechos e a que custo."""

    __tablename__ = "rag_interacoes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    pergunta = Column(Text, nullable=False)
    resposta = Column(Text, nullable=False)
    encontrou_resposta = Column(Boolean, nullable=False, index=True)
    aviso = Column(Text, nullable=True)
    filtros = Column(JSON, nullable=True)
    chunk_ids_recuperados = Column(JSON, nullable=False, default=list)
    chunk_ids_citados = Column(JSON, nullable=False, default=list)
    modelo = Column(String(100), nullable=True, index=True)
    prompt_version = Column(String(50), nullable=False)
    tokens_entrada = Column(Integer, nullable=False, default=0)
    tokens_saida = Column(Integer, nullable=False, default=0)
    tentativas = Column(Integer, nullable=False, default=0)
    distancia_top1 = Column(Float, nullable=True)
    latencia_ms = Column(Integer, nullable=False)
    index_version = Column(Integer, nullable=False)
    do_cache = Column(Boolean, nullable=False, default=False)
    criado_em = Column(DateTime(timezone=True), server_default=func.now(), index=True)
