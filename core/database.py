from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from core.config import settings
from core.logging_config import logger

is_sqlite = "sqlite" in settings.DATABASE_URL

# Create database engine with connection pooling and timeouts
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 15} if is_sqlite else {},
    pool_pre_ping=True
)

# Enable SQLite WAL (Write-Ahead Logging) mode for non-blocking concurrent reads & writes
if is_sqlite:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        try:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA synchronous=NORMAL;")
            cursor.execute("PRAGMA busy_timeout=5000;")
            cursor.execute("PRAGMA cache_size=-64000;")  # 64MB memory cache
            cursor.close()
        except Exception as e:
            logger.warning("Failed to enable SQLite WAL pragmas: %s", e)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative base
Base = declarative_base()

def get_db():
    """FastAPI Dependency Injection for SQLAlchemy database sessions."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
