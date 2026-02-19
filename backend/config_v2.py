"""
Modern configuration management with proper security and validation
"""

import os
from typing import Optional, List
from pydantic import BaseSettings, validator, Field
from cryptography.fernet import Fernet
import secrets

class Settings(BaseSettings):
    """Production-ready configuration with security best practices"""
    
    # === Application ===
    DEBUG: bool = Field(default=False, env="DEBUG")
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    VERSION: str = "2.0.0"
    
    # === Security - CRITICAL FIXES ===
    SECRET_KEY: str = Field(
        default_factory=lambda: secrets.token_urlsafe(32),
        env="SECRET_KEY"
    )
    JWT_SECRET_KEY: str = Field(
        default_factory=lambda: secrets.token_urlsafe(32),
        env="JWT_SECRET_KEY"
    )
    ENCRYPTION_KEY: Optional[str] = Field(default=None, env="ENCRYPTION_KEY")
    
    @validator("JWT_SECRET_KEY")
    def validate_jwt_secret(cls, v, values):
        """Ensure JWT secret is different from app secret"""
        if v == values.get("SECRET_KEY"):
            raise ValueError("JWT_SECRET_KEY must be different from SECRET_KEY")
        return v
    
    # === Database - MODERN POOLING ===
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    DB_POOL_SIZE: int = Field(default=20, env="DB_POOL_SIZE")
    DB_MAX_OVERFLOW: int = Field(default=30, env="DB_MAX_OVERFLOW")
    DB_POOL_TIMEOUT: int = Field(default=60, env="DB_POOL_TIMEOUT")
    DB_POOL_RECYCLE: int = Field(default=3600, env="DB_POOL_RECYCLE")
    
    # === Performance ===
    MAX_WORKERS: int = Field(default=4, env="MAX_WORKERS")
    CHUNK_SIZE: int = Field(default=10000, env="CHUNK_SIZE")  # Smaller for stability
    BATCH_SIZE: int = Field(default=1000, env="BATCH_SIZE")
    
    # === Monitoring ===
    SENTRY_DSN: Optional[str] = Field(default=None, env="SENTRY_DSN")
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    METRICS_ENABLED: bool = Field(default=True, env="METRICS_ENABLED")
    
    # === External Services ===
    REDIS_URL: Optional[str] = Field(default=None, env="REDIS_URL")
    DEEPSEEK_API_KEY: Optional[str] = Field(default=None, env="DEEPSEEK_API_KEY")
    
    # === Data Processing ===
    MEDICAID_DATASET_PATH: str = Field(default="/data/medicaid_claims.zip", env="MEDICAID_DATASET_PATH")
    SAMPLE_SIZE: Optional[int] = Field(default=None, env="SAMPLE_SIZE")
    
    # === Security Headers ===
    CORS_ORIGINS: List[str] = Field(default=["http://localhost:3000"], env="CORS_ORIGINS")
    RATE_LIMIT_PER_MINUTE: int = Field(default=100, env="RATE_LIMIT_PER_MINUTE")
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Global settings instance
settings = Settings()

# Runtime security validation
def validate_security():
    """Validate critical security settings"""
    issues = []
    
    if len(settings.SECRET_KEY) < 32:
        issues.append("SECRET_KEY too short (min 32 chars)")
    
    if settings.JWT_SECRET_KEY == settings.SECRET_KEY:
        issues.append("JWT_SECRET_KEY must differ from SECRET_KEY")
    
    if settings.ENVIRONMENT == "production" and settings.DEBUG:
        issues.append("DEBUG cannot be true in production")
    
    if issues:
        raise ValueError(f"Security validation failed: {issues}")
    
    return True

# Initialize security validation
validate_security()
