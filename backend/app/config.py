from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Core ---
    app_name: str = "AI Engineer"
    debug: bool = True
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # --- Database (PostgreSQL) ---
    database_url: str = "postgresql+asyncpg://ai_engineer:ai_engineer_dev@localhost:5432/ai_engineer"

    # --- LLM provider ---
    llm_provider: str = "gemini"  # gemini | deepseek | openrouter | ollama
    llm_model: str = "gemini-2.5-flash"
    llm_temperature: float = 0.3
    llm_max_tokens: int | None = None

    gemini_api_key: str = ""
    gemini_embedding_model: str = "text-embedding-004"

    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-chat"
    deepseek_base_url: str = "https://api.deepseek.com/v1"

    openrouter_api_key: str = ""
    openrouter_model: str = "deepseek/deepseek-chat-v3-0324:free"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_model: str = "qwen2.5-coder:7b"

    # --- Embeddings ---
    embedding_provider: str = "gemini"  # gemini | local
    embedding_dim: int = 768

    # --- Storage ---
    storage_dir: Path = BASE_DIR / "storage"
    qdrant_path: Path = BASE_DIR / "storage" / "qdrant"
    workspaces_dir: Path = BASE_DIR / "storage" / "workspaces"

    # --- Agent ---
    agent_max_iterations: int = 12
    agent_max_review_loops: int = 2
    command_timeout_seconds: int = 45

    @property
    def configured_provider(self) -> str:
        return (self.llm_provider or "gemini").lower().strip()

    def api_key_for(self, provider: str | None = None) -> str:
        p = (provider or self.configured_provider).lower()
        return {
            "gemini": self.gemini_api_key,
            "deepseek": self.deepseek_api_key,
            "openrouter": self.openrouter_api_key,
        }.get(p, "")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    settings.qdrant_path.mkdir(parents=True, exist_ok=True)
    settings.workspaces_dir.mkdir(parents=True, exist_ok=True)
    return settings


settings = get_settings()
