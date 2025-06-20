from pydantic import BaseModel, EmailStr, HttpUrl


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
