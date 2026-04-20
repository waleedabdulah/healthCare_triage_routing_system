"""
LLM client factory — supports Groq (default) and Claude (Anthropic).

Switch providers by setting LLM_PROVIDER=claude in your .env file.
Both providers implement the same LangChain chat interface so all
graph nodes work unchanged.
"""
from functools import lru_cache
from src.config.settings import get_settings


@lru_cache()
def get_llm():
    """Return the configured LLM. Raises clearly if the required API key is missing."""
    settings = get_settings()
    provider = settings.llm_provider.lower().strip()

    if provider == "claude":
        from langchain_anthropic import ChatAnthropic

        if not settings.anthropic_api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Add it to your .env file, "
                "or set LLM_PROVIDER=groq to use Groq instead."
            )

        return ChatAnthropic(
            api_key=settings.anthropic_api_key,
            model=settings.claude_model,
            temperature=0.1,
            max_tokens=1024,
            thinking={"type": "disabled"},   # keep latency predictable for triage
        )

    # Default: Groq
    from langchain_groq import ChatGroq

    if not settings.groq_api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Add it to your .env file, "
            "or set LLM_PROVIDER=claude and provide ANTHROPIC_API_KEY."
        )

    return ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        temperature=0.1,
        max_tokens=1024,
        max_retries=5,
    )


def get_model_name() -> str:
    settings = get_settings()
    provider = settings.llm_provider.lower().strip()
    return settings.claude_model if provider == "claude" else settings.groq_model
