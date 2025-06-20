from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./instance/news.db"

Base = declarative_base()


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


engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# create tables
Base.metadata.create_all(bind=engine)
