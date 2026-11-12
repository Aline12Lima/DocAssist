from pydantic import BaseModel, Field


class SentimentResponse(BaseModel):
    """Resultado da análise de sentimento."""

    text: str = Field(..., description="Texto analisado")
    label: str = Field(..., description="Classificação: positive, negative ou neutral")
    score: float = Field(..., ge=0, le=1, description="Confiança da classificação (0 a 1)")

    model_config = {
        "json_schema_extra": {
            "examples": [{"text": "I love this!", "label": "positive", "score": 0.985}]
        }
    }


class EntityResponse(BaseModel):
    """Entidade nomeada individual encontrada no texto."""

    word: str = Field(..., description="Palavra ou expressão detectada")
    entity: str = Field(..., description="Tipo: PER (pessoa), ORG (organização), LOC (local), MISC")
    score: float = Field(..., description="Confiança da detecção (0 a 1)")
    start: int = Field(..., description="Posição inicial no texto original")
    end: int = Field(..., description="Posição final no texto original")


class NERResponse(BaseModel):
    """Resultado do reconhecimento de entidades nomeadas."""

    text: str = Field(..., description="Texto analisado")
    entities: list[EntityResponse] = Field(..., description="Lista de entidades encontradas")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "text": "Aline works at Google.",
                    "entities": [
                        {"word": "Aline", "entity": "PER", "score": 0.99, "start": 0, "end": 5},
                        {"word": "Google", "entity": "ORG", "score": 0.99, "start": 15, "end": 21},
                    ],
                }
            ]
        }
    }


class TranslationResponse(BaseModel):
    """Resultado da tradução."""

    original: str = Field(..., description="Texto original")
    translated: str = Field(..., description="Texto traduzido")
    source: str = Field(..., description="Idioma de origem")
    target: str = Field(..., description="Idioma de destino")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "original": "Hello world",
                    "translated": "Olá mundo",
                    "source": "en",
                    "target": "pt",
                }
            ]
        }
    }


class EmbeddingResponse(BaseModel):
    """Vetor semântico do texto."""

    text: str = Field(..., description="Texto de origem")
    embedding: list[float] = Field(..., description="Vetor numérico (384 dimensões)")
    dimensions: int = Field(..., description="Quantidade de dimensões do vetor")


class DocumentResponse(BaseModel):
    """Confirmação de documento adicionado."""

    id: str = Field(..., description="ID do documento")
    text: str = Field(..., description="Texto salvo")
    status: str = Field(default="added", description="Status da operação")


class SearchResult(BaseModel):
    """Resultado individual de busca semântica."""

    id: str = Field(..., description="ID do documento")
    text: str = Field(..., description="Conteúdo do documento")
    distance: float = Field(..., description="Distância semântica (menor = mais similar)")
    metadata: dict = Field(..., description="Metadados armazenados")


class SearchResponse(BaseModel):
    """Resultado da busca semântica."""

    query: str = Field(..., description="Consulta original")
    results: list[SearchResult] = Field(
        ..., description="Documentos encontrados, ordenados por similaridade"
    )
    total: int = Field(..., description="Quantidade de resultados retornados")


class IngestResponse(BaseModel):
    """Resultado da ingestão de um arquivo."""

    doc_id: str = Field(..., description="ID do documento na base")
    chunks: int = Field(..., description="Quantidade de chunks do documento")
    gerados: int = Field(..., description="Chunks novos ou alterados (passaram pelo modelo)")
    removidos: int = Field(..., description="Chunks antigos que deixaram de existir")
    tempo_ms: int = Field(..., description="Tempo total da ingestão")


class DocumentoInfo(BaseModel):
    """Um documento indexado."""

    doc_id: str
    titulo: str | None = None
    fonte: str | None = None
    chunks: int


class DocumentosResponse(BaseModel):
    """Lista de documentos indexados."""

    total: int
    documentos: list[DocumentoInfo]
