import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings

# Absolute path to the backend directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    # Application Info
    APP_NAME: str = "Literature Intelligence Platform"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "127.0.0.1"

    # Ollama Service Configurations
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_LLM_MODEL: str = "qwen3:1.7b"
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text"
    
    # Model Hyperparameters (Optimized for 8 GB RAM)
    LLM_TEMPERATURE: float = 0.1
    LLM_CONTEXT_LENGTH: int = 4096
    LLM_MAX_OUTPUT_TOKENS: int = 512
    OLLAMA_TIMEOUT_SECONDS: float = 90.0
    OLLAMA_KEEP_ALIVE: str = "5m"  # Unload from RAM when idle

    # Storage Paths
    SQLITE_DB_PATH: str = str(BASE_DIR / "data" / "literature.db")
    CHROMA_PERSIST_DIR: str = str(BASE_DIR / "data" / "chroma")
    UPLOAD_DIR: str = str(BASE_DIR / "data" / "PDFs")
    PDF_STORAGE_DIR: str = str(BASE_DIR / "data" / "PDFs")
    EXTRACTED_STORAGE_DIR: str = str(BASE_DIR / "data" / "extracted")

    # Document Ingestion Settings
    MAX_UPLOAD_SIZE_MB: int = 50
    MAX_CHUNK_TOKENS: int = 600
    CHUNK_OVERLAP_TOKENS: int = 100
    TOP_K_RETRIEVAL: int = 4

    # Academic Discovery Agent Settings
    ACADEMIC_SEARCH_TIMEOUT_SECONDS: float = 12.0
    SEMANTIC_SCHOLAR_API_KEY: str = ""
    OPENALEX_EMAIL: str = "literature-platform@local.ai"

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000"
    ]

    class Config:
        env_file = str(BASE_DIR / ".env")
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()

# Ensure runtime directories exist on startup
os.makedirs(Path(settings.SQLITE_DB_PATH).parent, exist_ok=True)
os.makedirs(Path(settings.CHROMA_PERSIST_DIR), exist_ok=True)
os.makedirs(Path(settings.UPLOAD_DIR), exist_ok=True)
os.makedirs(Path(settings.PDF_STORAGE_DIR), exist_ok=True)
os.makedirs(Path(settings.EXTRACTED_STORAGE_DIR), exist_ok=True)
