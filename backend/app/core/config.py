from pathlib import Path
from typing import Literal, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Enterprise Document Intelligence RAG System"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    
    # Storage Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    DOCUMENTS_DIR: Path = DATA_DIR / "documents"
    CHROMA_PERSIST_DIR: Path = DATA_DIR / "chroma"
    SQLITE_DB_PATH: Path = DATA_DIR / "rag_metadata.db"
    
    # LLM Settings
    LLM_PROVIDER: Literal["gemini", "openai", "ollama", "mock"] = "mock"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-flash"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"
    LLM_TEMPERATURE: float = 0.0
    LLM_MAX_TOKENS: int = 1024
    
    # Embedding Settings
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
    EMBEDDING_DEVICE: str = "cpu"
    
    # Default Chunking Settings
    DEFAULT_CHUNK_SIZE: int = 600
    DEFAULT_CHUNK_OVERLAP: int = 100
    
    # Default Retrieval Settings
    DEFAULT_TOP_K: int = 4
    ENABLE_RERANKING: bool = True
    RERANKER_TOP_N: int = 3
    SIMILARITY_THRESHOLD: float = 0.25  # Chunks with cosine distance above this (or score below) are flagged
    
    # Hallucination Protection
    STRICT_GROUNDING: bool = True
    NO_ANSWER_FALLBACK: str = (
        "I could not find sufficient information in the uploaded documents to answer your question."
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()

# Ensure required storage directories exist
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
settings.CHROMA_PERSIST_DIR.mkdir(parents=True, exist_ok=True)
