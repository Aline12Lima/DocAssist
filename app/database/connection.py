from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings


def opcoes_do_banco(url: str) -> dict:
    """Opções do create_engine que dependem do banco.

    O SQLite (usado na nuvem, Fase 9.6c) guarda tudo num arquivo e, por padrão, só deixa
    a conexão ser usada pela thread que a abriu. O FastAPI atende cada requisição numa
    thread do pool, e o streaming grava o histórico em outra; por isso desligamos essa
    checagem. O Postgres não precisa de nada disso.
    """
    if url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    return {"pool_pre_ping": True}


engine = create_engine(settings.DATABASE_URL, **opcoes_do_banco(settings.DATABASE_URL))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
