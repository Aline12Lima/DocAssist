import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.openapi.docs import get_redoc_html
from fastapi.responses import HTMLResponse
from prometheus_fastapi_instrumentator import Instrumentator

from app.config import settings
from app.database.connection import engine
from app.database.models import Base
from app.routers import cache, health, history, nlp, rag
from app.services.chroma_service import get_chroma_client
from app.services.redis_service import get_redis_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


API_DESCRIPTION = f"""
# {settings.APP_NAME}

Pipeline completo de processamento de linguagem natural com modelos HuggingFace,
busca semântica (RAG) e cache inteligente.

## Recursos principais

* **Análise de sentimento** — classifica textos em positivo, negativo ou neutro
* **NER (Named Entity Recognition)** — identifica pessoas, organizações e lugares
* **Tradução EN→PT** — traduz textos do inglês para o português
* **Embeddings semânticos** — gera vetores de 384 dimensões
* **RAG (busca semântica)** — encontra documentos por significado, não por palavras-chave
* **Cache Redis** — respostas até 18x mais rápidas em requisições repetidas
* **Histórico PostgreSQL** — auditoria completa de todas as operações

## Como usar

Cada endpoint tem exemplos prontos. Clique em **"Try it out"**, ajuste o payload
e clique em **"Execute"** para testar em tempo real.

## Arquitetura

Docker Compose orquestra 3 containers: API (FastAPI + Uvicorn),
banco relacional (PostgreSQL 16) e cache (Redis 7).
Modelos HuggingFace são carregados no startup e mantidos em memória.
"""

TAGS_METADATA = [
    {"name": "health", "description": "Endpoints de verificação de saúde da API"},
    {
        "name": "nlp",
        "description": "Modelos de processamento de linguagem natural (sentimento, NER, tradução, embeddings). Resultados são cacheados no Redis.",
    },
    {
        "name": "rag",
        "description": "Retrieval-Augmented Generation: adicionar documentos e buscar por similaridade semântica usando ChromaDB.",
    },
    {
        "name": "history",
        "description": "Histórico persistente de todas as operações realizadas, armazenado no PostgreSQL.",
    },
    {"name": "cache", "description": "Estatísticas e gerenciamento do cache Redis."},
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Criando tabelas no PostgreSQL...")
    Base.metadata.create_all(bind=engine)
    logger.info("Tabelas prontas.")

    # Modelos carregados sob demanda (lazy) para economizar RAM no startup
    get_chroma_client()
    get_redis_client()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description=API_DESCRIPTION,
    version=settings.APP_VERSION,
    openapi_tags=TAGS_METADATA,
    docs_url="/docs",
    redoc_url=None,
    contact={
        "name": "Aline Lima",
        "url": "https://github.com/Aline12Lima/DocAssist",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    lifespan=lifespan,
)

Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(nlp.router, prefix="/nlp", tags=["nlp"])
app.include_router(rag.router, prefix="/rag", tags=["rag"])
app.include_router(history.router, prefix="/history", tags=["history"])
app.include_router(cache.router, prefix="/cache", tags=["cache"])


@app.get("/redoc", include_in_schema=False, response_class=HTMLResponse)
async def custom_redoc():
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=app.title + " - ReDoc",
        redoc_js_url="https://cdn.redoc.ly/redoc/latest/bundles/redoc.standalone.js",
    )


@app.get("/", tags=["health"], summary="Informacoes basicas da API")
def root():
    """Retorna informacoes gerais sobre a API."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "redoc": "/redoc",
    }
