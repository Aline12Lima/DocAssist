"""Configurações que valem para todos os testes de app/tests.

Os testes não podem depender do .env de quem roda: no seu computador o .env tem
API_KEYS preenchido; no CI, não. Sem esta fixture, os mesmos testes passariam no CI e
falhariam na sua máquina (todo pedido daria 401). Aqui cada teste começa com a API
aberta e o limite padrão; os testes de segurança mudam isso quando precisam.
"""

import pytest

from app.config import settings


@pytest.fixture(autouse=True)
def configuracao_padrao(monkeypatch):
    monkeypatch.setattr(settings, "API_KEYS", "")
    monkeypatch.setattr(settings, "RATE_LIMIT_PERGUNTAS_POR_MINUTO", 10)
    monkeypatch.setattr(settings, "CONFIAR_X_FORWARDED_FOR", False)
