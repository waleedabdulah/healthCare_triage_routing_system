"""
LLM client factory — Groq (primary) with Ollama fallback.
Both expose the same langchain ChatModel interface.
"""
from functools import lru_cache
from langchain_groq import ChatGroq
from langchain_community.llms import Ollama
from langchain_community.chat_models import ChatOllama
from src.config.settings import get_settings


@lru_cache()
def get_llm():
    """Return the configured chat model (Groq or Ollama)."""
    settings = get_settings()

    if settings.use_groq:
        return ChatGroq(
            api_key=settings.groq_api_key,
            model=settings.groq_model,
            temperature=0.1,          # Low temp for consistent triage decisions
            max_tokens=1024,
        )

    # Ollama fallback
    return ChatOllama(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        temperature=0.1,
    )


def get_model_name() -> str:
    settings = get_settings()
    if settings.use_groq:
        return settings.groq_model
    return settings.ollama_model
