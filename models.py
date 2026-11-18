from sqlalchemy import Column, Integer, String
from core.database import Base, engine, SessionLocal


class NewsArticle(Base):
    __tablename__ = "news_posts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String)
    content = Column(String)
    url = Column(String)
    link = Column(String)
    urlToImage = Column(String)
    publishedAt = Column(String)


class AddEmail(Base):
    __tablename__ = "user_emails"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True)


__all__ = ["Base", "NewsArticle", "AddEmail", "engine", "SessionLocal"]
