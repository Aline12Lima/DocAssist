import logging
import uuid

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import settings
from app.models.hf_loader import get_embeddings_model

logger = logging.getLogger(__name__)

_client = None
_collection = None


def get_chroma_client():
    global _client, _collection
    if _client is None:
        logger.info("Inicializando ChromaDB...")
        _client = chromadb.PersistentClient(
            path=settings.CHROMA_PATH,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        _collection = _client.get_or_create_collection(name=settings.CHROMA_COLLECTION)
        logger.info(f"ChromaDB pronto. Documentos: {_collection.count()}")
    return _collection


def add_document(text: str, metadata: dict = None) -> str:
    collection = get_chroma_client()
    model = get_embeddings_model()
    embedding = model.encode(text).tolist()
    doc_id = str(uuid.uuid4())
    collection.add(
        ids=[doc_id],
        embeddings=[embedding],
        documents=[text],
        metadatas=[metadata or {}],
    )
    return doc_id


def search_documents(query: str, top_k: int = 3) -> list:
    collection = get_chroma_client()
    model = get_embeddings_model()
    query_embedding = model.encode(query).tolist()
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
    )
    return [
        {
            "id": results["ids"][0][i],
            "text": results["documents"][0][i],
            "distance": results["distances"][0][i],
            "metadata": results["metadatas"][0][i],
        }
        for i in range(len(results["ids"][0]))
    ]


def count_documents() -> int:
    return get_chroma_client().count()
