"""
ResearchMind AI – Application Settings
Reads environment variables via pydantic-settings.
"""
from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ─────────────────────────────────────────────────────────
    app_name: str = "ResearchMind AI"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: str = "development"

    # ── API Server ──────────────────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False

    # ── Database ────────────────────────────────────────────────────────────
    database_url: str = Field(
        default="postgresql+asyncpg://researchmind:researchmind_secret@localhost:5432/researchmind_db"
    )

    # ── LLM (Groq) ─────────────────────────────────────────────
    groq_api_key: str = Field(default="")
    llm_model: str = "llama-3.3-70b-versatile"   # Groq model name
    embedding_model: str = "all-MiniLM-L6-v2"  # sentence-transformers model
    embedding_dimensions: int = 384       # all-MiniLM-L6-v2 dimension

    # ── Search ─────────────────────────────────────────────────────────────
    tavily_api_key: str = Field(default="")
    max_search_results_per_query: int = 10

    # ── Agent Limits ────────────────────────────────────────────────────────
    max_agent_iterations: int = 3

    # ── CORS – stored as a raw string, parsed into a list via property ──────
    # Using str (not List[str]) avoids pydantic-settings trying to JSON-decode
    # a comma-separated value from the .env file.
    allowed_origins_str: str = Field(
        default="http://localhost:3000",
        alias="allowed_origins",
    )

    @property
    def allowed_origins(self) -> List[str]:
        """Returns CORS origins as a list, splitting on commas."""
        return [o.strip() for o in self.allowed_origins_str.split(",") if o.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings singleton – call this everywhere instead of importing Settings directly."""
    return Settings()
