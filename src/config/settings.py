from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # LLM
    groq_api_key: str = ""
    groq_model: str = "llama-3.1-8b-instant"
    use_ollama: bool = False
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    # App
    app_env: str = "development"
    log_level: str = "INFO"

    # Paths
    chroma_db_path: str = "./data/chroma_db"
    sqlite_db_path: str = "./data/triage_audit.db"

    # MCP
    mcp_server_script: str = "./src/mcp/server.py"

    # CORS
    allowed_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    @property
    def use_groq(self) -> bool:
        return bool(self.groq_api_key) and not self.use_ollama

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
