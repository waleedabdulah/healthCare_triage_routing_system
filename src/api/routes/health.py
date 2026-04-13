from fastapi import APIRouter
from src.rag.vector_store import get_vector_store
from src.database.connection import get_engine
from sqlmodel import text, Session

router = APIRouter()


@router.get("/health")
def health_check():
    status = {"status": "ok", "services": {}}

    # Check ChromaDB
    try:
        store = get_vector_store()
        count = store.count()
        status["services"]["chromadb"] = {"status": "ok", "documents": count}
    except Exception as e:
        status["services"]["chromadb"] = {"status": "error", "error": str(e)}
        status["status"] = "degraded"

    # Check SQLite
    try:
        with Session(get_engine()) as session:
            session.exec(text("SELECT 1"))
        status["services"]["sqlite"] = {"status": "ok"}
    except Exception as e:
        status["services"]["sqlite"] = {"status": "error", "error": str(e)}
        status["status"] = "degraded"

    return status
