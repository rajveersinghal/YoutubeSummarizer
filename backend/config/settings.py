# config/settings.py - APPLICATION SETTINGS (FIXED)

from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import List, Set, Optional, Any
from pathlib import Path
import os

class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # ============================================================================
    # APPLICATION
    # ============================================================================
    
    APP_NAME: str = "SpectraAI"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = Field(default="development")
    DEBUG: bool = Field(default=True)
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)
    
    # ============================================================================
    # LOGGING
    # ============================================================================
    
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    LOG_FORMAT: str = Field(
        default="detailed",
        description="Log format (simple, detailed)"
    )
    LOG_TO_FILE: bool = Field(
        default=True,
        description="Enable file logging"
    )
    LOG_FILE: str = Field(
        default="spectraai.log",
        description="Log file name"
    )
    
    # ============================================================================
    # CORS
    # ============================================================================
    
    ALLOWED_ORIGINS: str = Field(default="*")
    
    # ============================================================================
    # DATABASE
    # ============================================================================
    
    MONGODB_URI: str = Field(default="mongodb://localhost:27017")
    MONGODB_DB_NAME: str = Field(default="spectraai")
    MONGODB_SERVER_TIMEOUT: int = Field(default=5000)
    MONGODB_CONNECT_TIMEOUT: int = Field(default=10000)
    
    # ============================================================================
    # AUTHENTICATION
    # ============================================================================
    
    CLERK_SECRET_KEY: Optional[str] = Field(default=None)
    CLERK_PUBLISHABLE_KEY: Optional[str] = Field(default=None)
    CLERK_FRONTEND_API: str = "exact-bee-20.clerk.accounts.dev"
    
    ADMIN_USER_IDS: str = Field(
        default="",
        description="Comma-separated list of admin user IDs"
    )
    ADMIN_EMAILS: str = Field(
        default="",
        description="Comma-separated list of admin emails"
    )
    
    # ============================================================================
    # AI MODELS (✅ FIXED)
    # ============================================================================
    
    GEMINI_API_KEY: Optional[str] = Field(default=None)
    # ✅ FIXED: Use gemini-2.5-flash as default
    GEMINI_MODEL: str = Field(default="gemini-2.5-flash")
    GEMINI_TEMPERATURE: float = Field(default=0.7)
    GEMINI_MAX_TOKENS: int = Field(default=2048)
    MAX_CONTEXT_LENGTH: int = Field(default=4096)
    
    # Embeddings
    EMBEDDING_MODEL: str = Field(default="sentence-transformers/all-MiniLM-L6-v2")
    EMBEDDING_DIMENSION: int = Field(default=384)
    
    # Whisper
    WHISPER_MODEL_SIZE: str = Field(default="base")
    WHISPER_DEVICE: str = Field(default="cpu")
    
    # Streaming
    ENABLE_STREAMING: bool = Field(default=True)
    STREAM_CHUNK_SIZE: int = Field(default=20)
    
    # ============================================================================
    # FILE UPLOAD & STORAGE
    # ============================================================================
    
    UPLOAD_MAX_SIZE: int = Field(default=10 * 1024 * 1024)  # 10MB
    VIDEO_MAX_SIZE: int = Field(default=100 * 1024 * 1024)  # 100MB
    ALLOWED_EXTENSIONS: str = Field(default=".pdf,.txt,.docx,.doc,.md")
    ALLOWED_VIDEO_EXTENSIONS: str = Field(default=".mp4,.avi,.mov,.mkv,.webm")
    STORAGE_PATH: str = Field(default="storage")
    
    # ============================================================================
    # DIRECTORIES
    # ============================================================================
    
    BASE_DIR: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[1])
    
    @property
    def DATA_DIR(self) -> Path:
        """Data directory path"""
        return self.BASE_DIR / "data"
    
    @property
    def DOCUMENTS_DIR(self) -> Path:
        """Documents directory path"""
        return self.DATA_DIR / "documents"
    
    @property
    def VIDEOS_DIR(self) -> Path:
        """Videos directory path"""
        return self.DATA_DIR / "videos"
    
    @property
    def AUDIO_DIR(self) -> Path:
        """Audio files directory path"""
        return self.DATA_DIR / "audio"
    
    @property
    def LOGS_DIR(self) -> Path:
        """Logs directory path"""
        return self.BASE_DIR / "logs"
    
    @property
    def STORAGE_DIR(self) -> Path:
        """Storage directory path for uploaded files"""
        return self.BASE_DIR / self.STORAGE_PATH
    
    @property
    def CACHE_DIR(self) -> Path:
        """Cache directory path"""
        return self.BASE_DIR / "cache"
    
    # ============================================================================
    # RATE LIMITING
    # ============================================================================
    
    RATE_LIMIT_ENABLED: bool = Field(default=True)
    RATE_LIMIT_PER_MINUTE: int = Field(default=60)
    RATE_LIMIT_PER_HOUR: int = Field(default=1000)
    
    # ============================================================================
    # PAGINATION
    # ============================================================================
    
    MAX_PAGE_SIZE: int = Field(default=100)
    DEFAULT_PAGE_SIZE: int = Field(default=20)
    
    # ============================================================================
    # AI GENERATION
    # ============================================================================
    
    MAX_AI_CHARS: int = Field(default=2000)
    CHUNK_SIZE: int = Field(default=512)
    CHUNK_OVERLAP: int = Field(default=50)
    
    # ============================================================================
    # USER PREFERENCES DEFAULTS
    # ============================================================================
    
    DEFAULT_THEME: str = Field(default="light")
    DEFAULT_LANGUAGE: str = Field(default="en")
    DEFAULT_NOTIFICATIONS: bool = Field(default=True)
    
    # ============================================================================
    # PYDANTIC CONFIG
    # ============================================================================
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore",
        "arbitrary_types_allowed": True,
    }
    
    # ============================================================================
    # COMPUTED PROPERTIES
    # ============================================================================
    
    @property
    def allowed_origins_list(self) -> List[str]:
        """Get ALLOWED_ORIGINS as a list"""
        if self.ALLOWED_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(',') if origin.strip()]
    
    @property
    def allowed_extensions_set(self) -> Set[str]:
        """Get ALLOWED_EXTENSIONS as a set"""
        extensions = [ext.strip() for ext in self.ALLOWED_EXTENSIONS.split(',') if ext.strip()]
        return set(ext if ext.startswith('.') else f'.{ext}' for ext in extensions)
    
    @property
    def allowed_video_extensions_set(self) -> Set[str]:
        """Get ALLOWED_VIDEO_EXTENSIONS as a set"""
        extensions = [ext.strip() for ext in self.ALLOWED_VIDEO_EXTENSIONS.split(',') if ext.strip()]
        return set(ext if ext.startswith('.') else f'.{ext}' for ext in extensions)
    
    @property
    def admin_user_ids_list(self) -> List[str]:
        """Get ADMIN_USER_IDS as a list"""
        if not self.ADMIN_USER_IDS:
            return []
        return [uid.strip() for uid in self.ADMIN_USER_IDS.split(',') if uid.strip()]
    
    @property
    def admin_emails_list(self) -> List[str]:
        """Get ADMIN_EMAILS as a list"""
        if not self.ADMIN_EMAILS:
            return []
        return [email.strip().lower() for email in self.ADMIN_EMAILS.split(',') if email.strip()]
    
    # ============================================================================
    # VALIDATORS (Pydantic v2)
    # ============================================================================
    
    @field_validator('PORT')
    @classmethod
    def validate_port(cls, v: int) -> int:
        """Validate port number"""
        if not (1 <= v <= 65535):
            raise ValueError("PORT must be between 1 and 65535")
        return v
    
    @field_validator('UPLOAD_MAX_SIZE', 'VIDEO_MAX_SIZE')
    @classmethod
    def validate_upload_size(cls, v: int) -> int:
        """Validate upload size is positive"""
        if v <= 0:
            raise ValueError("Upload size must be positive")
        return v
    
    @field_validator('CHUNK_SIZE')
    @classmethod
    def validate_chunk_size(cls, v: int) -> int:
        """Validate chunk size"""
        if v <= 0:
            raise ValueError("CHUNK_SIZE must be positive")
        return v
    
    @field_validator('CHUNK_OVERLAP')
    @classmethod
    def validate_chunk_overlap(cls, v: int, info) -> int:
        """Validate chunk overlap"""
        if v < 0:
            raise ValueError("CHUNK_OVERLAP must be non-negative")
        chunk_size = info.data.get('CHUNK_SIZE', 512)
        if v >= chunk_size:
            raise ValueError("CHUNK_OVERLAP must be less than CHUNK_SIZE")
        return v
    
    @field_validator('GEMINI_TEMPERATURE')
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        """Validate temperature is in valid range"""
        if not (0.0 <= v <= 2.0):
            raise ValueError("GEMINI_TEMPERATURE must be between 0.0 and 2.0")
        return v
    
    @field_validator('GEMINI_API_KEY')
    @classmethod
    def load_gemini_key_from_env(cls, v: Optional[str]) -> Optional[str]:
        """Load Gemini API key from environment if not set"""
        if v is None or v == "":
            return os.getenv("GEMINI_API_KEY")
        return v
    
    @field_validator('CLERK_SECRET_KEY')
    @classmethod
    def load_clerk_key_from_env(cls, v: Optional[str]) -> Optional[str]:
        """Load Clerk secret key from environment if not set"""
        if v is None or v == "":
            return os.getenv("CLERK_SECRET_KEY")
        return v
    
    @field_validator('CLERK_PUBLISHABLE_KEY')
    @classmethod
    def load_clerk_pub_key_from_env(cls, v: Optional[str]) -> Optional[str]:
        """Load Clerk publishable key from environment if not set"""
        if v is None or v == "":
            return os.getenv("CLERK_PUBLISHABLE_KEY")
        return v
    
    # ============================================================================
    # POST-INIT
    # ============================================================================
    
    def model_post_init(self, __context: Any) -> None:
        """Create necessary directories after initialization"""
        try:
            self.DATA_DIR.mkdir(parents=True, exist_ok=True)
            self.DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
            self.VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
            self.AUDIO_DIR.mkdir(parents=True, exist_ok=True)
            self.LOGS_DIR.mkdir(parents=True, exist_ok=True)
            self.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
            self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"⚠️  Warning: Failed to create directories: {e}")
    
    # ============================================================================
    # VALIDATION METHODS
    # ============================================================================
    
    def validate(self) -> bool:
        """
        Validate critical settings
        
        Returns:
            True if all critical settings are valid, False otherwise
        """
        errors = []
        warnings = []
        
        # Critical checks
        if not self.MONGODB_URI or self.MONGODB_URI == "mongodb://localhost:27017":
            warnings.append("Using default MongoDB URI (localhost)")
        
        if not self.CLERK_SECRET_KEY:
            errors.append("CLERK_SECRET_KEY is required for authentication")
        
        if not self.GEMINI_API_KEY:
            errors.append("GEMINI_API_KEY is required for AI features")
        
        # Optional checks
        if not self.CLERK_PUBLISHABLE_KEY:
            warnings.append("CLERK_PUBLISHABLE_KEY not configured")
        
        if not self.admin_user_ids_list and not self.admin_emails_list:
            warnings.append("No admin users configured")
        
        # Log results
        if errors or warnings:
            try:
                from config.logging_config import logger
                
                for error in errors:
                    logger.error(f"❌ Configuration error: {error}")
                
                for warning in warnings:
                    logger.warning(f"⚠️  Configuration warning: {warning}")
            except ImportError:
                for error in errors:
                    print(f"❌ Configuration error: {error}")
                for warning in warnings:
                    print(f"⚠️  Configuration warning: {warning}")
        
        return len(errors) == 0
    
    def get_info(self) -> dict:
        """
        Get configuration information (safe for logging)
        
        Returns:
            Dictionary with non-sensitive configuration info
        """
        return {
            "app_name": self.APP_NAME,
            "version": self.APP_VERSION,
            "environment": self.ENVIRONMENT,
            "debug": self.DEBUG,
            "host": self.HOST,
            "port": self.PORT,
            "database": self.MONGODB_DB_NAME,
            "ai_model": self.GEMINI_MODEL,
            "ai_temperature": self.GEMINI_TEMPERATURE,
            "ai_max_tokens": self.GEMINI_MAX_TOKENS,
            "embedding_model": self.EMBEDDING_MODEL,
            "whisper_model": self.WHISPER_MODEL_SIZE,
            "rate_limit_enabled": self.RATE_LIMIT_ENABLED,
            "streaming_enabled": self.ENABLE_STREAMING,
            "clerk_configured": bool(self.CLERK_SECRET_KEY),
            "gemini_configured": bool(self.GEMINI_API_KEY),
            "allowed_origins": self.allowed_origins_list,
            "allowed_extensions": list(self.allowed_extensions_set),
            "allowed_video_extensions": list(self.allowed_video_extensions_set),
            "storage_path": str(self.STORAGE_DIR),
            "admin_users_count": len(self.admin_user_ids_list),
            "admin_emails_count": len(self.admin_emails_list),
            "default_theme": self.DEFAULT_THEME,
        }
    
    def is_admin(self, user_id: str = None, email: str = None) -> bool:
        """
        Check if user is admin
        
        Args:
            user_id: User ID to check
            email: Email to check
        
        Returns:
            True if user is admin, False otherwise
        """
        if user_id and user_id in self.admin_user_ids_list:
            return True
        
        if email and email.lower() in self.admin_emails_list:
            return True
        
        return False

# ============================================================================
# GLOBAL SETTINGS INSTANCE
# ============================================================================

settings = Settings()

# ============================================================================
# VALIDATE ON IMPORT
# ============================================================================

if __name__ != "__main__":
    try:
        settings.validate()
    except Exception as e:
        print(f"⚠️  Settings validation warning: {e}")
