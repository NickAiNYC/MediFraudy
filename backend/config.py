"""Configuration management using environment variables with validation."""

import os
from typing import Optional
from dotenv import load_dotenv

# Load .env file if present
load_dotenv()


class Settings:
    """Application settings loaded from environment variables with validation."""

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://analyst:change_this_in_production@postgres:5432/medicaid_db",
    )
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "50"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "20"))
    DB_POOL_TIMEOUT: int = int(os.getenv("DB_POOL_TIMEOUT", "60"))

    # Application
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes", "t")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "development_secret_key")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")  # development, staging, production
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # Dataset
    MEDICAID_DATASET_URL: Optional[str] = os.getenv("MEDICAID_DATASET_URL")
    MEDICAID_DATASET_PATH: Optional[str] = os.getenv("MEDICAID_DATASET_PATH", "/data/medicaid_claims.zip")
    MEDICAID_DATASET_CHECKSUM: Optional[str] = os.getenv("MEDICAID_DATASET_CHECKSUM")  # SHA-256
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "50000"))
    
    # Processing
    MAX_WORKERS: int = int(os.getenv("MAX_WORKERS", "4"))  # For parallel processing
    SAMPLE_SIZE: Optional[int] = os.getenv("SAMPLE_SIZE")  # For dev: load only N rows
    if SAMPLE_SIZE:
        SAMPLE_SIZE = int(SAMPLE_SIZE)
    
    # CORS
    CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
    
    # Feature flags
    ENABLE_POL_CACHE: bool = os.getenv("ENABLE_POL_CACHE", "True").lower() in ("true", "1", "yes", "t")
    POL_CACHE_DAYS: int = int(os.getenv("POL_CACHE_DAYS", "7"))
    
    # External services (optional)
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    CLAUDE_API_KEY: Optional[str] = os.getenv("CLAUDE_API_KEY")
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "local")  # local, openai, claude
    
    # Export
    EXPORT_DIR: str = os.getenv("EXPORT_DIR", "/app/exports")
    
    def __init__(self):
        """Validate critical settings in production."""
        if self.ENVIRONMENT == "production":
            self._validate_production()
    
    def _validate_production(self):
        """Ensure required settings are set in production."""
        if self.DATABASE_URL == "postgresql://analyst:changeme_in_production@postgres:5432/medicaid_db":
            raise ValueError("DATABASE_URL must be changed in production")
        
        if self.SECRET_KEY == "development_secret_key":
            raise ValueError("SECRET_KEY must be changed in production")
        
        if not self.MEDICAID_DATASET_URL and not self.MEDICAID_DATASET_PATH:
            raise ValueError("Either MEDICAID_DATASET_URL or MEDICAID_DATASET_PATH must be set")
    
    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"
    
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"
    
    @property
    def database_dsn(self) -> str:
        """Return database URL with SSL enforcement in production."""
        base_url = self.DATABASE_URL
        
        # If running in docker internal network, force disable SSL
        if "@postgres" in base_url:
            # Strip any existing query params to avoid duplicates
            if "?" in base_url:
                base_url = base_url.split("?")[0]
            return base_url + "?sslmode=disable"
            
        if self.is_production:
            if "sslmode=" not in base_url:
                return base_url + ("&" if "?" in base_url else "?") + "sslmode=require"
            
        return base_url
    
    def dict(self) -> dict:
        """Return settings as dictionary (excluding secrets)."""
        return {
            "environment": self.ENVIRONMENT,
            "debug": self.DEBUG,
            "host": self.HOST,
            "port": self.PORT,
            "database": self.DATABASE_URL.split("@")[-1] if "@" in self.DATABASE_URL else "set",
            "chunk_size": self.CHUNK_SIZE,
            "cors_origins": self.CORS_ORIGINS,
            "log_level": self.LOG_LEVEL,
            "pol_cache_days": self.POL_CACHE_DAYS,
            "llm_provider": self.LLM_PROVIDER,
        }


# Create global settings instance
settings = Settings()
