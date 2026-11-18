import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings:
    PROJECT_NAME: str = "CrisisAid API"
    PROJECT_DESCRIPTION: str = "Real-Time Humanitarian Intelligence & Crisis Monitoring Platform"
    PROJECT_VERSION: str = "2.5.0"
    
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    STATIC_DIR: Path = BASE_DIR / "static"
    TEMPLATES_DIR: Path = BASE_DIR / "templates"
    INSTANCE_DIR: Path = BASE_DIR / "instance"
    
    _raw_db_url: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'instance'}/news.db")
    # Render PostgreSQL URLs start with postgres://, SQLAlchemy 2.0 requires postgresql://
    if _raw_db_url.startswith("postgres://"):
        _raw_db_url = _raw_db_url.replace("postgres://", "postgresql://", 1)
    DATABASE_URL: str = _raw_db_url
    
    NEWS_API_KEY: str = os.getenv("NEWS_API_KEY", "")
    NEWS_API_URL: str = os.getenv("NEWS_API_URL", "https://newsapi.org/v2/everything")
    
    LOCAL_HF_MODEL: str = os.getenv("LOCAL_HF_MODEL", "Qwen/Qwen2.5-0.5B-Instruct")
    
    DONATION_LINKS_PATH: Path = DATA_DIR / "all_countries_verified_donation_links.csv"
    COUNTRY_COORDINATES_PATH: Path = DATA_DIR / "country_coordinates.json"
    
    SUMMARY_MP3_PATH: Path = STATIC_DIR / "assets" / "audio_summary" / "summary.mp3"
    SUMMARY_TIMESTAMP_PATH: Path = STATIC_DIR / "assets" / "audio_summary" / "summary_timestamp.txt"
    
    CUSTOM_SEARCH_API_KEY: str = os.getenv("CUSTOM_SEARCH_API_KEY", "")
    SEARCH_ENGINE_ID: str = os.getenv("SEARCH_ENGINE_ID", "")
    CUSTOM_SEARCH_URL: str = os.getenv("CUSTOM_SEARCH_URL", "https://www.googleapis.com/customsearch/v1")

    EMAIL_USER: str = os.getenv("EMAIL_USER", "")
    EMAIL_PASSWORD: str = os.getenv("EMAIL_PASSWORD", "")
    EMAIL_SERVER: str = os.getenv("EMAIL_SERVER", "smtp.gmail.com")
    EMAIL_PORT: int = int(os.getenv("EMAIL_PORT", "465"))

settings = Settings()

# Ensure local directories exist upon settings initialization
settings.INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
