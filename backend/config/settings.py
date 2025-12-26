# backend/config/settings.py - COMPLETE CONFIGURATION

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

class Settings:
    # ============================================================================
    # APPLICATION
    # ============================================================================
    APP_NAME: str = os.getenv("APP_NAME", "SpectraAI")
    APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # ============================================================================
    # CORS
    # ============================================================================
    ALLOWED_ORIGINS: list = os.getenv(
        "ALLOWED_ORIGINS", 
        "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    
    # ============================================================================
    # MONGODB
    # ============================================================================
    MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    MONGODB_DB_NAME: str = os.getenv("MONGODB_DB_NAME", "spectraai")
    MONGODB_SERVER_TIMEOUT: int = int(os.getenv("MONGODB_SERVER_TIMEOUT", "5000"))
    MONGODB_CONNECT_TIMEOUT: int = int(os.getenv("MONGODB_CONNECT_TIMEOUT", "10000"))
    
    # ============================================================================
    # CLERK AUTHENTICATION
    # ============================================================================
    CLERK_SECRET_KEY: str = os.getenv("CLERK_SECRET_KEY", "")
    CLERK_PUBLISHABLE_KEY: str = os.getenv("CLERK_PUBLISHABLE_KEY", "")
    CLERK_FRONTEND_API: str = os.getenv("CLERK_FRONTEND_API", "")
    
    # ============================================================================
    # AI CONFIGURATION
    # ============================================================================
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    GEMINI_TEMPERATURE: float = float(os.getenv("GEMINI_TEMPERATURE", "0.7"))
    GEMINI_MAX_TOKENS: int = int(os.getenv("GEMINI_MAX_TOKENS", "2048"))
    MAX_CONTEXT_LENGTH: int = int(os.getenv("MAX_CONTEXT_LENGTH", "4096"))
    
    # Embedding
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    EMBEDDING_DIMENSION: int = int(os.getenv("EMBEDDING_DIMENSION", "384"))
    
    # Whisper
    WHISPER_MODEL_SIZE: str = os.getenv("WHISPER_MODEL_SIZE", "base")
    WHISPER_DEVICE: str = os.getenv("WHISPER_DEVICE", "cpu")
    
    # Streaming
    ENABLE_STREAMING: bool = os.getenv("ENABLE_STREAMING", "true").lower() == "true"
    STREAM_CHUNK_SIZE: int = int(os.getenv("STREAM_CHUNK_SIZE", "20"))
    
    # ============================================================================
    # FILE STORAGE
    # ============================================================================
    UPLOAD_MAX_SIZE: int = int(os.getenv("UPLOAD_MAX_SIZE", "10485760"))
    VIDEO_MAX_SIZE: int = int(os.getenv("VIDEO_MAX_SIZE", "104857600"))
    ALLOWED_EXTENSIONS: list = os.getenv("ALLOWED_EXTENSIONS", ".pdf,.txt,.docx,.doc,.md").split(",")
    ALLOWED_VIDEO_EXTENSIONS: list = os.getenv("ALLOWED_VIDEO_EXTENSIONS", ".mp4,.avi,.mov,.mkv,.webm").split(",")
    STORAGE_PATH: str = os.getenv("STORAGE_PATH", "storage")
    
    # ============================================================================
    # RATE LIMITING
    # ============================================================================
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    RATE_LIMIT_PER_HOUR: int = int(os.getenv("RATE_LIMIT_PER_HOUR", "1000"))
    
    # ============================================================================
    # PAGINATION
    # ============================================================================
    MAX_PAGE_SIZE: int = int(os.getenv("MAX_PAGE_SIZE", "100"))
    DEFAULT_PAGE_SIZE: int = int(os.getenv("DEFAULT_PAGE_SIZE", "20"))
    
    # ============================================================================
    # AI GENERATION & RAG
    # ============================================================================
    MAX_AI_CHARS: int = int(os.getenv("MAX_AI_CHARS", "2000"))
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "512"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "50"))
    
    # ============================================================================
    # USER PREFERENCES
    # ============================================================================
    DEFAULT_THEME: str = os.getenv("DEFAULT_THEME", "light")
    DEFAULT_LANGUAGE: str = os.getenv("DEFAULT_LANGUAGE", "en")
    DEFAULT_NOTIFICATIONS: bool = os.getenv("DEFAULT_NOTIFICATIONS", "true").lower() == "true"
    
    # ============================================================================
    # LOGGING
    # ============================================================================
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "detailed")
    LOG_TO_FILE: bool = os.getenv("LOG_TO_FILE", "true").lower() == "true"
    LOG_FILE: str = os.getenv("LOG_FILE", "spectraai.log")
    SHOW_ERROR_DETAILS: bool = os.getenv("SHOW_ERROR_DETAILS", "true").lower() == "true"

settings = Settings()

# Print loaded settings (for debugging)
if settings.DEBUG:
    print("✅ Settings loaded:")
    print(f"   - Groq API Key: {'✅ SET' if settings.GROQ_API_KEY else '❌ NOT SET'}")
    print(f"   - Gemini API Key: {'✅ SET' if settings.GEMINI_API_KEY else '❌ NOT SET'}")
    print(f"   - MongoDB: {settings.MONGODB_URI}")
    print(f"   - Environment: {settings.ENVIRONMENT}")
