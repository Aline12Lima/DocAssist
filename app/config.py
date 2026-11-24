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
    RAG_TOP_K_CONTEXTO: int = 5  # trechos enviados ao LLM
    # Acima desta distância, responde "não encontrei" sem chamar o LLM.
    # Calibrado no E2 para o e5; outro modelo de embedding precisa de outro valor.
    RAG_LIMIAR_DISTANCIA: float = 0.17
    # Carrega o modelo de embedding ao subir a API, para a 1ª pergunta não demorar.
    # Desligue (false) onde a memória for curta.
    RAG_AQUECER_MODELO: bool = True
    RAG_CACHE_TTL_S: int = 86400  # respostas do /rag/ask ficam 24 h no cache
    # Reranker (fase 7, E4): a busca vetorial escolhe os candidatos e o cross-encoder
    # reordena. 20 candidatos: Recall@5 0.90 com ~2,9 s; 30 dá 0.94, mas com ~4,6 s.
    RAG_RERANKER_ATIVO: bool = True
    RAG_RERANKER_MODELO: str = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
    RAG_RERANKER_CANDIDATOS: int = 20
    # Com o reranker ligado, é esta nota (e não a distância) que decide o "não encontrei".
    # Calibrado no E4_c20: perguntas sem resposta ficaram todas abaixo de 1.5.
    RAG_LIMIAR_RERANKER: float = 2.0

    # LLM (as chaves ficam só no .env, nunca no código)
    GROQ_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    LLM_MODELOS: str = "groq:openai/gpt-oss-120b"  # ordem de tentativa, separada por vírgulas
    LLM_MAX_TOKENS: int = 800
    LLM_TEMPERATURA: float = 0.1
    LLM_TIMEOUT: float = 30.0
    # Segurança (Fase 9.4). API_KEYS vazio = API aberta, só para desenvolvimento.
    API_KEYS: str = ""  # várias chaves separadas por vírgula
    RATE_LIMIT_PERGUNTAS_POR_MINUTO: int = 10
    CONFIAR_X_FORWARDED_FOR: bool = False  # true só atrás de um proxy (ex.: Railway)
    # Juiz da Fase 8: de outra família que o modelo que responde, para não favorecer a si mesmo
    JUIZ_MODELOS: str = "gemini:gemini-3.5-flash-lite,groq:qwen/qwen3.8-27b"
    JUIZ_PROMPT_VERSAO: str = "judge_v1"
    JUIZ_MAX_TOKENS: int = 1500
    LLM_PROMPT_VERSAO: str = "answer_v2"  # arquivo em prompts/<versão>.md

    # Banco de dados
    DATABASE_URL: str = "postgresql://nlp_user:nlp_pass@postgres:5432/nlp_db"

    # Cache Redis
    REDIS_URL: str = "redis://redis:6379/0"

    class Config:
        env_file = ".env"


settings = Settings()
