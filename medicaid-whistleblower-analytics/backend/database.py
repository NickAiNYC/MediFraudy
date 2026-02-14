"""Database connection setup using SQLAlchemy with connection pooling and retry logic."""

import logging
from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy.exc import OperationalError, TimeoutError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import settings

logger = logging.getLogger(__name__)


# Configure SQLite for development (optional)
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable foreign keys and better concurrency for SQLite."""
    if settings.DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()


# Create engine with connection pooling
engine = create_engine(
    settings.database_dsn,  # Use the property from config
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_pre_ping=True,  # Verify connections before using
    pool_recycle=3600,   # Recycle connections every hour
    echo=settings.DEBUG,  # Log SQL in debug mode
    echo_pool=settings.DEBUG,  # Log connection pool in debug mode
    connect_args={
        "connect_timeout": 10,  # Connection timeout in seconds
        "keepalives_idle": 30,   # Keep connection alive
        "keepalives_interval": 10,
        "keepalives_count": 5,
    } if "postgresql" in settings.DATABASE_URL else {}
)


# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,  # Don't expire objects after commit
)


# Base class for models
Base = declarative_base()


# Retry decorator for database operations
retry_db = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(OperationalError),
    before_sleep=lambda retry_state: logger.warning(
        f"Database operation failed, retrying... ({retry_state.attempt_number}/3)"
    ),
)


@retry_db
def get_db() -> Generator[Session, None, None]:
    """
    Yield a database session with automatic retry on connection failure.
    Ensures session is properly closed after use.
    """
    db = SessionLocal()
    try:
        logger.debug("Database session opened")
        yield db
    except OperationalError as e:
        logger.error(f"Database operational error: {e}")
        db.rollback()
        raise
    finally:
        logger.debug("Database session closed")
        db.close()


def get_db_direct() -> Session:
    """Get a database session directly (for scripts, not FastAPI endpoints)."""
    return SessionLocal()


def init_db() -> None:
    """Create database tables if they don't exist."""
    logger.info("Creating database tables if they don't exist...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified")


def check_db_connection() -> bool:
    """Verify database connectivity."""
    try:
        with SessionLocal() as db:
            db.execute("SELECT 1")
            logger.info("Database connection successful")
            return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False


def dispose_engine() -> None:
    """Dispose of the connection pool (for shutdown)."""
    engine.dispose()
    logger.info("Database engine disposed")


# Context manager for scripts
class db_session:
    """Context manager for database sessions in scripts."""
    
    def __enter__(self):
        self.db = SessionLocal()
        return self.db
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.db.rollback()
        self.db.close()


# Health check function
def get_db_stats() -> dict:
    """Get database connection pool statistics."""
    pool = engine.pool
    return {
        "size": pool.size(),
        "checked_in_connections": pool.checkedin(),
        "overflow": pool.overflow(),
        "total": pool.total(),
    }
