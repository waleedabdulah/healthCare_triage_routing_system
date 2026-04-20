"""
LLM client factory — Groq via ChatGroq (langchain_groq).
Requires GROQ_API_KEY in .env. Raises clearly if not configured.
"""
from functools import lru_cache
from langchain_groq import ChatGroq
from src.config.settings import get_settings


@lru_cache()
def get_llm():
    """Return the Groq chat model. Raises if GROQ_API_KEY is not set."""
    settings = get_settings()

    if not settings.groq_api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Add it to your .env file."
        )

    return ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        temperature=0.1,      # Low temp for consistent triage decisions
        max_tokens=1024,
        max_retries=5,        # Retry on 429 rate-limit responses
    )


def get_model_name() -> str:
    return get_settings().groq_model
