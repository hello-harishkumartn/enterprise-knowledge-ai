"""Central application settings.

Every environment-dependent value (DB, auth, LLM providers, retrieval knobs)
lives here so the rest of the codebase never reads `os.environ` directly.
"""
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Environment -----------------------------------------------------
    ENV: Literal["development", "test", "production"] = "development"

    # --- Database ----------------------------------------------------------
    DATABASE_URL: str = "postgresql+psycopg://ekai:ekai@localhost:5432/ekai"

    # --- Auth ----------------------------------------------------------
    JWT_SECRET: str = "dev-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 12

    # --- LLM providers ----------------------------------------------------
    # Comma separated, tried in order. "mock" is always a safe last resort
    # for local dev/CI so the app works with zero external dependencies.
    LLM_PROVIDER_ORDER: str = "gemini,ollama,mock"

    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta"

    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2"

    LLM_TIMEOUT_SECONDS: float = 30.0
    LLM_MAX_OUTPUT_TOKENS: int = 800

    # --- Embeddings / reranking ----------------------------------------
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIM: int = 384
    RERANKER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # --- Retrieval tuning (kept explicit & visible, not buried) -----------
    RETRIEVAL_TOP_K_VECTOR: int = 20
    RETRIEVAL_TOP_K_KEYWORD: int = 20
    RETRIEVAL_RRF_K: int = 60  # standard RRF smoothing constant
    RETRIEVAL_FUSED_TOP_N: int = 15  # candidates passed into the reranker
    RETRIEVAL_FINAL_TOP_N: int = 6  # chunks passed into the context builder

    # --- Context engineering ----------------------------------------------
    CONTEXT_TOKEN_BUDGET: int = 3000
    CONTEXT_MAX_CHUNKS_PER_DOC: int = 3

    # --- Chunking -----------------------------------------------------
    CHUNK_TARGET_TOKENS: int = 300
    CHUNK_OVERLAP_TOKENS: int = 40

    # --- Storage ------------------------------------------------------
    STORAGE_DIR: str = "./storage"

    @property
    def llm_provider_order(self) -> list[str]:
        return [p.strip() for p in self.LLM_PROVIDER_ORDER.split(",") if p.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
