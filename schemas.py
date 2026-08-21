from pydantic import BaseModel, EmailStr, HttpUrl, Field
from typing import List, Optional, Dict, Any


class NewsArticleBase(BaseModel):
    title: str
    description: str
    content: str
    url: HttpUrl
    link: str
    urlToImage: HttpUrl
    publishedAt: str

    class Config:
        from_attributes = True


class NewsArticle(NewsArticleBase):
    id: int

    class Config:
        from_attributes = True


class AddEmailBase(BaseModel):
    email: EmailStr

    class Config:
        from_attributes = True


class AddEmail(AddEmailBase):
    id: int

    class Config:
        from_attributes = True


class ChatQuery(BaseModel):
    message: str
    provider: Optional[str] = None


class CrisisSituationReport(BaseModel):
    urgency: str = Field(default="HIGH", description="Urgency rating: CRITICAL, HIGH, or ELEVATED")
    crisis_type: str = Field(default="Humanitarian Emergency", description="Primary category of the emergency")
    takeaways: List[str] = Field(default_factory=list, description="3-5 executive situational takeaways")
    timeline: List[Dict[str, str]] = Field(default_factory=list, description="Chronological origin milestones (phase & detail)")
    immediate_needs: List[str] = Field(default_factory=list, description="Top 4 urgent humanitarian relief items")
