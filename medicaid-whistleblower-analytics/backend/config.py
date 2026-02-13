"""Configuration management using environment variables."""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://analyst:change_this_in_production@localhost:5432/medicaid_db",
    )
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "development_secret_key")
    MEDICAID_DATASET_URL: str = os.getenv(
        "MEDICAID_DATASET_URL", "https://data.medicaid.gov/path/to/dataset"
    )
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "50000"))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))


settings = Settings()
