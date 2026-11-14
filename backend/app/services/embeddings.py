from functools import lru_cache
from typing import Any

from backend.app.core.config import get_settings


@lru_cache(maxsize=2)
def _load_embedding_model(model_name: str) -> Any:
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name)


class EmbeddingService:
    """Lazy, reusable sentence-transformer embeddings for future retrieval."""

    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or get_settings().hf_embedding_model

    @property
    def model(self) -> Any:
        return _load_embedding_model(self.model_name)

    def embed_text(self, text: str) -> list[float]:
        embedding = self.model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    def embed_resource_text(self, title: str, description: str | None = None) -> list[float]:
        content = title if not description else f"{title}\n{description}"
        return self.embed_text(content)


@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()
