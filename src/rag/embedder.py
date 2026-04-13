"""
Local HuggingFace sentence-transformers embedder.
No API calls — runs entirely on CPU.
"""
from sentence_transformers import SentenceTransformer
from functools import lru_cache

EMBEDDING_MODEL = "all-MiniLM-L6-v2"


@lru_cache()
def get_embedder() -> SentenceTransformer:
    """Load and cache the embedding model."""
    return SentenceTransformer(EMBEDDING_MODEL)


def embed_text(text: str) -> list[float]:
    """Embed a single string."""
    model = get_embedder()
    return model.encode(text, normalize_embeddings=True).tolist()


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed a batch of strings."""
    model = get_embedder()
    return model.encode(texts, normalize_embeddings=True).tolist()
