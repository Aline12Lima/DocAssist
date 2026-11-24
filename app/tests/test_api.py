from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data


def test_health():
    response = client.get("/health/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_sentiment_positive():
    mock_result = [{"label": "positive", "score": 0.98}]
    with patch("app.routers.nlp.get_sentiment_model") as mock_model:
        mock_model.return_value = MagicMock(return_value=mock_result)
        with patch("app.routers.nlp.get_cached", return_value=None):
            with patch("app.routers.nlp.set_cached"):
                with patch("app.routers.nlp.save_history"):
                    response = client.post(
                        "/nlp/sentiment",
                        json={"text": "I love this!"},
                    )
    assert response.status_code == 200
    data = response.json()
    assert data["label"] == "positive"
    assert data["score"] == 0.98


def test_sentiment_negative():
    mock_result = [{"label": "negative", "score": 0.94}]
    with patch("app.routers.nlp.get_sentiment_model") as mock_model:
        mock_model.return_value = MagicMock(return_value=mock_result)
        with patch("app.routers.nlp.get_cached", return_value=None):
            with patch("app.routers.nlp.set_cached"):
                with patch("app.routers.nlp.save_history"):
                    response = client.post(
                        "/nlp/sentiment",
                        json={"text": "I hate this!"},
                    )
    assert response.status_code == 200
    data = response.json()
    assert data["label"] == "negative"


def test_sentiment_empty_text_returns_422():
    """Texto vazio deve ser rejeitado pela validação de min_length."""
    response = client.post("/nlp/sentiment", json={"text": ""})
    assert response.status_code == 422


def test_sentiment_missing_field():
    response = client.post("/nlp/sentiment", json={})
    assert response.status_code == 422


def test_pagina_do_chat():
    resposta = client.get("/chat")
    assert resposta.status_code == 200
    assert resposta.headers["content-type"].startswith("text/html")
    assert "DocAssist" in resposta.text
    assert "/rag/ask/stream" in resposta.text
