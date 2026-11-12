from typing import Literal

from pydantic import BaseModel, Field


class TextRequest(BaseModel):
    """Texto de entrada para análise NLP genérica."""

    text: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Texto a ser analisado (1 a 5000 caracteres)",
        examples=["I absolutely love this new project!"],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"text": "I absolutely love this new project!"},
                {"text": "This is the worst experience I've had."},
                {"text": "Aline Silva works at Google in São Paulo."},
            ]
        }
    }


class TranslationRequest(BaseModel):
    """Texto em inglês para tradução para português."""

    text: str = Field(
        ..., min_length=1, max_length=5000, description="Texto em inglês a ser traduzido"
    )
    source: Literal["en"] = Field(
        default="en", description="Idioma de origem (atualmente apenas 'en' suportado)"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"text": "Hello, how are you today?", "source": "en"},
                {"text": "Machine learning is fascinating.", "source": "en"},
            ]
        }
    }


class DocumentRequest(BaseModel):
    """Documento a ser adicionado ao banco vetorial para busca semântica."""

    text: str = Field(..., min_length=1, description="Conteúdo do documento")
    metadata: dict = Field(default={}, description="Metadados livres (categoria, autor, data etc)")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "text": "FastAPI é um framework Python moderno e muito rápido.",
                    "metadata": {"tema": "tecnologia", "autor": "docs"},
                }
            ]
        }
    }


class SearchRequest(BaseModel):
    """Consulta de busca semântica no banco vetorial."""

    query: str = Field(..., min_length=1, description="Texto de busca (pergunta ou palavras-chave)")
    top_k: int = Field(
        default=3, ge=1, le=20, description="Quantidade de resultados a retornar (1 a 20)"
    )
    doc_id: str | None = Field(default=None, description="Buscar só neste documento")
    fonte: str | None = Field(default=None, description="Buscar só nesta fonte (ex.: docker)")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"query": "como fazer a API esperar o banco ficar pronto?", "top_k": 3},
                {"query": "o que o TTL retorna?", "top_k": 5, "fonte": "redis"},
            ]
        }
    }
