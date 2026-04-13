"""
ChromaDB vector store wrapper for triage protocol retrieval.
"""
import chromadb
from chromadb.config import Settings as ChromaSettings
from src.rag.embedder import embed_text, embed_batch
from src.config.settings import get_settings
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)

COLLECTION_NAME = "triage_protocols"


class TriageVectorStore:
    def __init__(self, db_path: str):
        self._client = chromadb.PersistentClient(
            path=db_path,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            f"ChromaDB collection '{COLLECTION_NAME}' loaded — "
            f"{self._collection.count()} documents"
        )

    def add_documents(
        self,
        ids: list[str],
        texts: list[str],
        metadatas: list[dict],
    ) -> None:
        """Embed and upsert documents into the collection."""
        embeddings = embed_batch(texts)
        self._collection.upsert(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        logger.info(f"Upserted {len(ids)} documents into ChromaDB")

    def query(
        self,
        query_text: str,
        n_results: int = 5,
        where: dict | None = None,
    ) -> list[dict]:
        """
        Query the collection and return formatted results.
        Each result: {id, text, metadata, distance}
        """
        query_embedding = embed_text(query_text)

        kwargs = {
            "query_embeddings": [query_embedding],
            "n_results": min(n_results, self._collection.count() or 1),
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            kwargs["where"] = where

        try:
            results = self._collection.query(**kwargs)
        except Exception as e:
            logger.warning(f"ChromaDB query with filter failed ({e}), retrying without filter")
            kwargs.pop("where", None)
            results = self._collection.query(**kwargs)

        output = []
        ids = results.get("ids", [[]])[0]
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        dists = results.get("distances", [[]])[0]

        for doc_id, text, meta, dist in zip(ids, docs, metas, dists):
            output.append({
                "id": doc_id,
                "text": text,
                "metadata": meta,
                "distance": dist,
            })

        return output

    def count(self) -> int:
        return self._collection.count()


@lru_cache()
def get_vector_store() -> TriageVectorStore:
    settings = get_settings()
    return TriageVectorStore(db_path=settings.chroma_db_path)
