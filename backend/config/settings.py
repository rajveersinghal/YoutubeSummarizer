# backend/config/settings.py
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Settings:
    """Application Settings"""
    
    # Base Directory
    BASE_DIR = Path(__file__).resolve().parents[2]
    
    # Application
    APP_NAME = "Spectra-AI"
    APP_VERSION = "2.0.0"
    DEBUG = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1", "yes")
    PORT = int(os.getenv("PORT", 5000))
    HOST = os.getenv("HOST", "0.0.0.0")
    
    # Security
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
    
    # MongoDB Configuration
    MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
    MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "spectra_ai")
    MONGODB_CONNECT_TIMEOUT = int(os.getenv("MONGODB_CONNECT_TIMEOUT", "5000"))
    MONGODB_SERVER_TIMEOUT = int(os.getenv("MONGODB_SERVER_TIMEOUT", "5000"))
    
    # Clerk Authentication
    CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY")
    CLERK_PUBLISHABLE_KEY = os.getenv("CLERK_PUBLISHABLE_KEY")
    
    # AI Model Configuration - ✅ WORKING MODELS
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    GEMINI_MODEL = "gemini-flash-latest"  # ✅ Auto-updates to latest
    MODEL_NAME = "gemini-flash-latest"  # ✅ For backward compatibility
    GEMINI_TEMPERATURE = 0.7
    GEMINI_MAX_OUTPUT_TOKENS = 1024
    MAX_AI_CHARS = int(os.getenv("MAX_AI_CHARS", "5000"))
    
    # Whisper Configuration
    WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "small")
    
    # Embedding Configuration
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "800"))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
    
    # Vector Store Configuration
    VECTOR_STORE_TYPE = os.getenv("VECTOR_STORE_TYPE", "faiss")
    FAISS_INDEX_PATH = BASE_DIR / "data" / "faiss_indexes"
    
    # RAG Configuration
    TOP_K_CHUNKS = int(os.getenv("TOP_K_CHUNKS", "5"))
    
    # File Storage
    AUDIO_DIR = BASE_DIR / "data" / "audio"
    LOGS_DIR = BASE_DIR / "data" / "logs"
    UPLOAD_MAX_SIZE = int(os.getenv("UPLOAD_MAX_SIZE", "10485760"))
    ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE = LOGS_DIR / "spectra_ai.log"
    
    # Rate Limiting
    RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "True").lower() in ("true", "1")
    RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    
    # Pagination
    DEFAULT_PAGE_SIZE = int(os.getenv("DEFAULT_PAGE_SIZE", "20"))
    MAX_PAGE_SIZE = int(os.getenv("MAX_PAGE_SIZE", "100"))
    
    @classmethod
    def create_directories(cls):
        """Create necessary directories if they don't exist"""
        cls.AUDIO_DIR.mkdir(parents=True, exist_ok=True)
        cls.LOGS_DIR.mkdir(parents=True, exist_ok=True)
        cls.FAISS_INDEX_PATH.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def validate(cls):
        """Validate critical settings"""
        errors = []
        
        if not cls.GEMINI_API_KEY:
            errors.append("GEMINI_API_KEY is not set")
        
        if not cls.MONGODB_URI:
            errors.append("MONGODB_URI is not set")
        
        if not cls.CLERK_SECRET_KEY:
            errors.append("CLERK_SECRET_KEY is not set")
        
        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")
        
        return True

settings = Settings()
settings.create_directories()
