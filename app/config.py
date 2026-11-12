from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "DocAssist API"
    APP_VERSION: str = "0.2.0"
    APP_ENV: str = "development"

    # Modelos HuggingFace
    HF_MODEL_SENTIMENT: str = "cardiffnlp/twitter-roberta-base-sentiment-latest"
    HF_MODEL_NER: str = "dbmdz/bert-large-cased-finetuned-conll03-english"
    HF_MODEL_TRANSLATION: str = "Helsinki-NLP/opus-mt-tc-big-en-pt"
    HF_MODEL_EMBEDDINGS: str = "sentence-transformers/all-MiniLM-L6-v2"
    HF_CACHE_DIR: str = "./models"

    # Banco vetorial
    CHROMA_PATH: str = "./chroma_data"
    CHROMA_COLLECTION: str = "documents"

    # RAG
    RAG_EMBEDDING_MODEL: str = "e5small"  # minilm | e5small
    RAG_CHUNK_LIMITE: int = 250  # tokens por chunk, com o prefixo
    RAG_CHUNK_OVERLAP: int = 30
    RAG_CHUNK_MINIMO: int = 50
    RAG_MAX_UPLOAD_MB: int = 10

    # Banco de dados
    DATABASE_URL: str = "postgresql://nlp_user:nlp_pass@postgres:5432/nlp_db"

    # Cache Redis
    REDIS_URL: str = "redis://redis:6379/0"

    class Config:
        env_file = ".env"


settings = Settings()
