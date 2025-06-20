import os
import re
import time
import ssl
import logging
import smtplib
import schedule
import requests
import uvicorn
from pprint import pprint
from datetime import datetime
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import func
from sqlalchemy.orm import Session

from schemas import NewsArticle as PydanticNewsArticle
from models import SessionLocal, NewsArticle, AddEmail
from pydantic import BaseModel

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from fastapi import FastAPI, Request, Depends, Query, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def fetch_news_from_api(country=None):
    params = {
        "apiKey": os.environ["NEWS_API_KEY"],
        "q": f"({country} AND (humanitarian+crisis -political+crisis -financial+crisis -president -movie -twitter))"
            if country else
                "humanitarian+crisis -political+crisis -financial+crisis -human+rights -president -movie -TV -twitter",
        "searchln": "title,description,content",
        "excludeDomains": "lifesciencesworld.com,psychologytoday.com,smallwarsjournal.com,leicarumors.com,"
                        "abcnews.go.com,sf.funcheap.com,fark.com",
        "language": "en",
    }
    response = requests.get(os.environ["NEWS_API_URL"], params=params)
    response.raise_for_status()
    articles = response.json().get("articles", [])
    articles_with_images = [article for article in articles if article.get("urlToImage")]
    # sorting articles to get latest news on top
    sorted_articles = sorted(
        articles_with_images,
        key=lambda article: datetime.fromisoformat(article["publishedAt"].replace("Z", "+00:00")),
        reverse=True
    )
    return sorted_articles


async def insert_news_in_db(country=None):
    articles = fetch_news_from_api(country)
    try:
        # lets link with SQLite database first
        # db = next(get_db())
        with SessionLocal() as db:
            # delete all old rows to add latest news rows
            rows_deleted = db.query(NewsArticle).delete()
            db.commit()
            print(f"Deleted {rows_deleted} rows from NewsArticle.")
        
        db_articles = []
        for article in articles:
            # check if the articles fetched are already in the database
            existing_article = db.query(NewsArticle).filter_by(title=article.get("title")).first()
            if existing_article:
                print("skipped duplicate article...")
                continue
            
            # let's create 1 row to insert in our NewsArticle database
            db_article = NewsArticle(
                title=article.get("title"),
                description=article.get("description"),
                content="",  # using gemini api to generate content else use newsapi content=(article.get("content")).replace("<ul><li>", "").split('[')[0],
                url=article.get("url"),
                link="",   # using gemini api to generate link
                urlToImage=article.get("urlToImage"),
                publishedAt=datetime.fromisoformat(article.get("publishedAt").rstrip("Z")).strftime('%d-%m-%Y')
            )
            try:
                db.add(db_article) # add the created row to the database
                db.commit()        # save the changes made
                db.refresh(db_article)
                # print(f"{db_article.title} added...")
            except Exception as e:
                db.rollback()      # undo changes
                print(f"Error: {e}")

            # db.add(db_article)
            db_articles.append(db_article)

        db.commit()
        print(f"Inserted {len(db_articles)} articles into the database.")
    except Exception as e:
        print(f"Error filling database with news: {e}")


async def generate_content(content):
    payload = {
        "contents": [{
            "parts": [{"text": f"Write a detailed, factual and structured news report based on the following summary: "
                            f"{content} in bullet points. Use specific details and avoid placeholders."}]
        }],
        "generationConfig": {
            "maxOutputTokens": 500
        }
    }
    params = {"key": os.environ["GEMINI_API_KEY"]}
    headers = {"Content-Type": "application/json"}
    response = requests.post(os.environ["GEMINI_API_URL"], json=payload, params=params, headers=headers)
    response.raise_for_status()
    data = response.json()
    return data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "No content generated.")


async def get_donation_link(news):
    payload = {
        "contents": [{
            "parts": [{"text": f"Give me one direct donation link for the following news: {news}."
                            " If no specific link is found, provide a trusted global humanitarian donation link"
                            " for the country mentioned in the news. Only return the URL without any extra text."}]
        }]
    }
    headers = {"Content-Type": "application/json"}
    params = {"key": os.environ["GEMINI_API_KEY"]}
    response = requests.post(os.environ["GEMINI_API_URL"], json=payload, params=params, headers=headers)
    response.raise_for_status()
    data = response.json()
    text_response = (data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0]
                    .get("text", "No donation link found"))

    # Extract URL using regex
    url_match = re.search(r"https?://\S+", text_response)
    return url_match.group(0) if url_match else "No valid donation link found"


def get_hero_image(country):
    params = {
        "q": f"humanitarian+crisis+in+{country}",
        "cx": os.environ["SEARCH_ENGINE_ID"],
        "key": os.environ["CUSTOM_SEARCH_API_KEY"],
        "searchType": "image",
        "num": 1
    }
    response = requests.get(os.environ["CUSTOM_SEARCH_URL"], params=params)
    response.raise_for_status()
    data = response.json()
    hero_image_url = data["items"][0]["link"]

    return hero_image_url


def send_newsletter():
    db = next(get_db())  # let's connect with the SQLite database
    article = db.query(NewsArticle).first()  # fetch the latest news article for emailing it
    emails = db.query(AddEmail.email).all()  # get all emails from the AddEmail database
    email_list = [email[0] for email in emails] # convert into a list
    for recipient_email in email_list:
        msg = MIMEMultipart()
        msg['From'] = os.environ["EMAIL"]
        msg['To'] = recipient_email
        msg['Subject'] = f"CrisisAid: Latest News: {article.title}"
        body = f"""<html>
                    <body>
                        <h5><b>{article.title}</b></h5>
                        <img src="{article.urlToImage}" alt="Crisis Image" style="width: 25%; object-fit: cover;"/>
                        <p>{article.description}</p>
                        <p><strong>Published on:</strong> {article.publishedAt}</p>
                    </body>
                </html>"""

        msg.attach(MIMEText(body, 'html'))  # used to convert html body to normal text
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", port=465, context=ssl.create_default_context()) as server:
                server.login(os.environ["EMAIL"], os.environ["PASSWORD"]) # logging in to your email account
                server.sendmail(os.environ["EMAIL"], recipient_email, msg.as_string()) # sending the mail
            print(f"Email sent to {recipient_email}")
        except Exception as e:
            print(f"Error sending email to {recipient_email}: {e}")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db)):
    await insert_news_in_db()
    articles = db.query(NewsArticle).limit(30).all()
    py_articles = [PydanticNewsArticle.model_validate(article) for article in articles]
    current_yr = datetime.now().strftime("%Y")  # for displaying copyright
    return templates.TemplateResponse("index.html", {
        "request": request,
        "all_articles": py_articles,
        "year": current_yr
    })


@app.get("/search", response_class=HTMLResponse)
async def search_news(request: Request, db: Session = Depends(get_db), country: str = Query(...)):
    await insert_news_in_db(country)
    # articles = db.query(NewsArticle).filter(func.lower(NewsArticle.title).contains(func.lower(country))).all()
    articles = db.query(NewsArticle).all()
    if articles:
        hero_image = get_hero_image(country)
        donation_link_hero = await get_donation_link(f"news related to {country}")
        py_articles = [PydanticNewsArticle.model_validate(article) for article in articles]
        return templates.TemplateResponse("search.html", {
            "request": request,
            "country": country,
            "hero_image": hero_image,
            "donation_link_hero": donation_link_hero,
            "all_articles": py_articles
        })
    else:
        return RedirectResponse(url=f"/?country_error=true", status_code=303)


@app.get("/news_article/{news_id}/{country}", response_class=HTMLResponse)
async def news_detail(request: Request, news_id: int, country: str, db: Session = Depends(get_db)):

    article = db.query(NewsArticle).filter(NewsArticle.id == news_id).first()

    if article is None:
        raise HTTPException(status_code=404, detail="Article not found")

    article.content = await generate_content(article.title+": "+article.description)
    article.link = await get_donation_link(article.title)
    db.commit()

    return templates.TemplateResponse("news_article.html", {"request": request, "article": article, "country": country})


@app.get("/chat", response_class=HTMLResponse)
async def chat(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})

class ChatRequest(BaseModel):
    message: str
    
@app.post("/generate/")
async def generate_chat(data: ChatRequest):
    user_message = data.message
    response = "hello! the chat feature is yet to be released!"
    return {"response": response}


@app.get("/locate", response_class=HTMLResponse)
async def locate(request: Request):
    return templates.TemplateResponse("locate.html", {"request": request})


@app.get("/get_crisis_countries")
async def get_crisis_countries():
    articles = fetch_news_from_api()
    countries = requests.get(os.environ["REST_COUNTRIES_API_URL"]).json()
    country_data = {country["name"]["common"]: country.get("latlng", [None, None]) for country in countries}

    crisis_countries = []
    for article in articles:
        if "aid" not in article["title"] and "for" not in article["title"] and "to" not in article["title"]:
            for country in list(country_data.keys()):
                if country.lower() in article["title"].lower() or country.lower() in article["description"].lower():
                    lat, lng = country_data[country]
                    img = article["urlToImage"]
                    crisis_countries.append(
                        {"name": country, "news": article["title"], "img": img, "lat": lat, "lng": lng})
                    country_data.pop(country)

    # pprint(crisis_countries)
    return {"crisis_countries": crisis_countries}


@app.get("/about", response_class=HTMLResponse)
async def about(request: Request):
    return templates.TemplateResponse("about.html", {"request": request})


@app.get("/getmail", response_class=HTMLResponse)
async def get_mail(email: str = Query(...), db: Session = Depends(get_db)):
    try:
        is_existing_email = db.query(AddEmail).filter(AddEmail.email == email).first()
        if is_existing_email:
            return RedirectResponse(url="/?error=true", status_code=303)

        # Insert the new email into the database
        db_article = AddEmail(email=email)
        db.add(db_article)
        db.commit()
        db.refresh(db_article)

        print(f"Inserted {email} into the database.")
        return RedirectResponse(url="/?email_success=true", status_code=303)

    except Exception as e:
        print(f"Error inserting email: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@asynccontextmanager
async def startup_event():
    await get_crisis_countries()
    schedule.every().day.at("08:00").do(send_newsletter)
    # while True:
    #     schedule.run_pending()
    #     time.sleep(60)


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
