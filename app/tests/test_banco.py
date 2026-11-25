"""Banco de dados: as opções do SQLite (nuvem) e do Postgres (local)."""

import threading

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import models  # noqa: F401  (registra as tabelas no Base)
from app.database.connection import Base, opcoes_do_banco


def test_sqlite_libera_o_uso_em_outras_threads():
    assert opcoes_do_banco("sqlite:////data/docassist.db") == {
        "connect_args": {"check_same_thread": False}
    }


def test_postgres_confere_a_conexao_antes_de_usar():
    assert opcoes_do_banco("postgresql://u:s@postgres:5432/db") == {"pool_pre_ping": True}


def test_sqlite_em_arquivo_funciona_fora_da_thread_que_abriu(tmp_path):
    url = f"sqlite:///{tmp_path / 'docassist.db'}"
    motor = create_engine(url, **opcoes_do_banco(url))
    Base.metadata.create_all(bind=motor)
    Sessao = sessionmaker(bind=motor)

    with Sessao() as sessao:  # abre e devolve uma conexão ao pool nesta thread
        sessao.execute(models.RagFeedback.__table__.select()).all()

    erros = []

    def em_outra_thread():
        try:
            with Sessao() as sessao:  # reaproveita a conexão do pool em outra thread
                sessao.execute(models.RagFeedback.__table__.select()).all()
        except Exception as erro:  # pragma: no cover - só aparece se falhar
            erros.append(erro)

    thread = threading.Thread(target=em_outra_thread)
    thread.start()
    thread.join()
    assert erros == []
    assert (tmp_path / "docassist.db").exists()
