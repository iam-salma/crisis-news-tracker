from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from core.config import settings

# Create database engine
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

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
