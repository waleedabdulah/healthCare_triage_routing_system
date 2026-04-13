from src.models.state import TriageState
from src.rag.vector_store import get_vector_store
import logging

logger = logging.getLogger(__name__)


def rag_retrieval_node(state: TriageState) -> dict:
    """
    Retrieves relevant triage protocol chunks from ChromaDB
    based on the patient's extracted symptoms.
    """
    symptoms = state.get("extracted_symptoms", [])
    red_flags = state.get("red_flags_detected", [])

    if not symptoms and not red_flags:
        logger.warning("rag_retrieval called with no symptoms or red flags")
        return {"rag_context": []}

    # Build query string
    query_parts = symptoms + red_flags
    query = ", ".join(query_parts)

    try:
        store = get_vector_store()

        # If red flags detected → pre-filter to emergency protocols
        if red_flags:
            results = store.query(
                query_text=query,
                n_results=5,
                where={"urgency_category": "EMERGENCY"},
            )
            # If not enough results with filter, do a broad search too
            if len(results) < 3:
                broad_results = store.query(query_text=query, n_results=5)
                # Merge and deduplicate
                seen_ids = {r["id"] for r in results}
                for r in broad_results:
                    if r["id"] not in seen_ids:
                        results.append(r)
                        seen_ids.add(r["id"])
        else:
            results = store.query(query_text=query, n_results=5)

        logger.info(f"RAG retrieved {len(results)} chunks for query: {query[:80]}")
        return {"rag_context": results}

    except Exception as e:
        logger.error(f"rag_retrieval error: {e}")
        return {"rag_context": []}
