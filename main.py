import os
import re
import time
import ssl
import json
import logging
import smtplib
import asyncio
import schedule
import requests
import uvicorn
import pandas as pd
from pathlib import Path
from pprint import pprint
from datetime import datetime
from contextlib import asynccontextmanager
import xml.etree.ElementTree as ET

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import func
from sqlalchemy.orm import Session

from schemas import NewsArticle as PydanticNewsArticle
from models import SessionLocal, NewsArticle, AddEmail
from pydantic import BaseModel

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from gtts import gTTS

from fastapi import FastAPI, Request, Depends, Query, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from schemas import NewsArticle as PydanticNewsArticle, ChatQuery, CrisisSituationReport
from llm_engine import LLMServiceFactory

app = FastAPI(title="CrisisAid API", description="Humanitarian Intelligence & Crisis Monitoring Platform", version="2.5.0")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
donation_links = pd.read_csv("data/all_countries_verified_donation_links.csv", encoding='latin-1', index_col=0).to_dict()["Link"]
SUMMARY_MP3_PATH = Path("static/assets/audio_summary/summary.mp3")
SUMMARY_TIMESTAMP_PATH = Path("static/assets/audio_summary/summary_timestamp.txt")

COUNTRY_COORDINATES_PATH = Path("data/country_coordinates.json")
if COUNTRY_COORDINATES_PATH.exists():
    try:
        with open(COUNTRY_COORDINATES_PATH, "r", encoding="utf-8") as f:
            country_coordinates_data = json.load(f)
    except Exception:
        country_coordinates_data = {}
else:
    country_coordinates_data = {}

CONTINENTS_REGIONS = {
    "africa": {
        "name": "Africa",
        "coords": [7.18, 21.09],
        "countries": {"sudan", "south sudan", "nigeria", "somalia", "ethiopia", "democratic republic of the congo", "congo", "chad", "niger", "mali", "burkina faso", "mozambique", "kenya", "uganda", "libya", "cameroon", "central african republic"}
    },
    "middle east": {
        "name": "Middle East",
        "coords": [29.29, 42.55],
        "countries": {"palestine", "gaza", "israel", "yemen", "syria", "lebanon", "iraq", "iran", "jordan"}
    },
    "asia": {
        "name": "Asia",
        "coords": [34.04, 100.61],
        "countries": {"bangladesh", "myanmar", "pakistan", "afghanistan", "india", "philippines", "indonesia", "nepal", "sri lanka"}
    },
    "europe": {
        "name": "Europe",
        "coords": [54.52, 15.25],
        "countries": {"ukraine", "greece", "turkey", "poland", "romania"}
    },
    "latin america": {
        "name": "Latin America & Caribbean",
        "coords": [-8.78, -55.49],
        "countries": {"haiti", "colombia", "venezuela", "ecuador", "peru", "guatemala", "honduras", "el salvador", "cuba"}
    },
    "south america": {
        "name": "Latin America & Caribbean",
        "coords": [-8.78, -55.49],
        "countries": {"haiti", "colombia", "venezuela", "ecuador", "peru", "guatemala", "honduras", "el salvador", "cuba"}
    },
    "sahel": {
        "name": "Sahel Region",
        "coords": [14.49, 0.44],
        "countries": {"mali", "niger", "burkina faso", "chad", "sudan", "mauritania"}
    },
    "horn of africa": {
        "name": "Horn of Africa",
        "coords": [8.03, 46.19],
        "countries": {"somalia", "ethiopia", "kenya", "djibouti", "eritrea", "south sudan"}
    }
}

ALIASES_AND_DEMONYMS = {
    "gaza": ("Palestine", [31.5, 34.46]),
    "gazan": ("Palestine", [31.5, 34.46]),
    "palestinian": ("Palestine", [31.9, 35.2]),
    "palestine": ("Palestine", [31.9, 35.2]),
    "west bank": ("Palestine", [31.95, 35.23]),
    "sudanese": ("Sudan", [12.86, 30.21]),
    "darfur": ("Sudan", [12.86, 30.21]),
    "khartoum": ("Sudan", [15.55, 32.53]),
    "sudan": ("Sudan", [12.86, 30.21]),
    "south sudanese": ("South Sudan", [6.87, 31.30]),
    "south sudan": ("South Sudan", [6.87, 31.30]),
    "dr congo": ("Democratic Republic of the Congo", [-4.03, 21.75]),
    "drc": ("Democratic Republic of the Congo", [-4.03, 21.75]),
    "congolese": ("Democratic Republic of the Congo", [-4.03, 21.75]),
    "nigerian": ("Nigeria", [9.08, 8.67]),
    "nigeria": ("Nigeria", [9.08, 8.67]),
    "nigerien": ("Niger", [17.60, 8.08]),
    "niger": ("Niger", [17.60, 8.08]),
    "syrian": ("Syria", [34.8, 38.99]),
    "syria": ("Syria", [34.8, 38.99]),
    "yemeni": ("Yemen", [15.55, 48.51]),
    "yemen": ("Yemen", [15.55, 48.51]),
    "ukrainian": ("Ukraine", [48.37, 31.16]),
    "ukraine": ("Ukraine", [48.37, 31.16]),
    "myanmar": ("Myanmar", [21.91, 95.95]),
    "burmese": ("Myanmar", [21.91, 95.95]),
    "rohingya": ("Myanmar", [21.91, 95.95]),
    "burma": ("Myanmar", [21.91, 95.95]),
    "haitian": ("Haiti", [18.97, -72.28]),
    "haiti": ("Haiti", [18.97, -72.28]),
    "somali": ("Somalia", [5.15, 46.19]),
    "somalia": ("Somalia", [5.15, 46.19]),
    "ethiopian": ("Ethiopia", [9.14, 40.48]),
    "ethiopia": ("Ethiopia", [9.14, 40.48]),
    "tigray": ("Ethiopia", [14.03, 38.31]),
    "lebanese": ("Lebanon", [33.85, 35.86]),
    "lebanon": ("Lebanon", [33.85, 35.86]),
    "afghan": ("Afghanistan", [33.93, 67.70]),
    "afghanistan": ("Afghanistan", [33.93, 67.70]),
    "bangladeshi": ("Bangladesh", [23.68, 90.35]),
    "bangladesh": ("Bangladesh", [23.68, 90.35]),
    "pakistani": ("Pakistan", [30.37, 69.34]),
    "pakistan": ("Pakistan", [30.37, 69.34]),
    "colombian": ("Colombia", [4.57, -74.29]),
    "colombia": ("Colombia", [4.57, -74.29])
}

# Sorted entities by length descending to prevent sub-string prefix collisions (e.g. Niger vs Nigeria)
ALL_GEO_ENTITIES = sorted(list(ALIASES_AND_DEMONYMS.keys()) + list(country_coordinates_data.keys()), key=len, reverse=True)

COMMON_REGIONS = ALIASES_AND_DEMONYMS

GLOBAL_RELIEF_PARTNERS = [
    {
        "name": "Doctors Without Borders (MSF)",
        "focus": "Emergency Trauma & Medical Care",
        "url": "https://www.msf.org/donate",
        "icon": "bi-heart-pulse-fill",
        "tag": "Medical"
    },
    {
        "name": "World Food Programme (WFP)",
        "focus": "Frontline Food Rations & Child Nutrition",
        "url": "https://www.wfp.org/donate",
        "icon": "bi-basket2-fill",
        "tag": "Food Aid"
    },
    {
        "name": "UNHCR (UN Refugee Agency)",
        "focus": "Refugee Tents, Shelter & Protection",
        "url": "https://donate.unhcr.org/",
        "icon": "bi-house-heart-fill",
        "tag": "Shelter"
    },
    {
        "name": "International Red Cross (ICRC)",
        "focus": "Neutral Relief & Humanitarian Corridors",
        "url": "https://www.icrc.org/en/donate",
        "icon": "bi-shield-plus",
        "tag": "Emergency Relief"
    }
]

FALLBACK_CAROUSEL_SLIDES = [
    {
        "id": 1,
        "title": "Stay Updated on Global Humanitarian Crises",
        "description": "Real-time updates on active humanitarian emergencies, natural disasters, and global relief operations worldwide.",
        "image": "/static/assets/images/hero-active.jpg",
        "country": "Global Crisis Alert",
        "publishedAt": datetime.now().strftime("%d-%m-%Y"),
        "donate_link": "https://www.redcross.org/donate/donation.html/"
    },
    {
        "id": 1,
        "title": "Frontline Relief: Delivering Aid When It Matters Most",
        "description": "Connecting awareness with direct action through verified humanitarian organizations and emergency aid corridors.",
        "image": "/static/assets/images/hero2.jpg",
        "country": "Emergency Relief",
        "publishedAt": datetime.now().strftime("%d-%m-%Y"),
        "donate_link": "https://www.icrc.org/en/donate"
    },
    {
        "id": 1,
        "title": "Spotlight on Emergency Zones & Relief Corridors",
        "description": "Track displaced populations, immediate priority needs, and verified relief hubs in active humanitarian zones.",
        "image": "/static/assets/images/hero3.jpg",
        "country": "Action Hub",
        "publishedAt": datetime.now().strftime("%d-%m-%Y"),
        "donate_link": "https://donate.unhcr.org/"
    }
]

def detect_geo_entity(text="", default_country=None):
    if default_country and default_country != "None":
        dc_lower = default_country.lower().strip()
        if dc_lower in ALIASES_AND_DEMONYMS:
            c_name, coords = ALIASES_AND_DEMONYMS[dc_lower]
            return ("country", c_name, coords, {c_name.lower()})
        for c, coords in country_coordinates_data.items():
            if c.lower() == dc_lower:
                return ("country", c, coords, {c.lower()})

    t_lower = text.lower()

    # Check Continents & Regions
    for reg_key, reg_info in sorted(CONTINENTS_REGIONS.items(), key=lambda x: len(x[0]), reverse=True):
        pattern = r'\b' + re.escape(reg_key) + r'\b'
        if re.search(pattern, t_lower):
            return ("region", reg_info["name"], reg_info["coords"], reg_info["countries"])

    # Check Countries and Demonyms with word boundary matching
    for entity in ALL_GEO_ENTITIES:
        pattern = r'\b' + re.escape(entity.lower()) + r'\b'
        if re.search(pattern, t_lower):
            if entity.lower() in ALIASES_AND_DEMONYMS:
                c_name, coords = ALIASES_AND_DEMONYMS[entity.lower()]
                return ("country", c_name, coords, {c_name.lower()})
            elif entity in country_coordinates_data:
                return ("country", entity, country_coordinates_data[entity], {entity.lower()})

    return ("global", "Global Crisis Region", [20.0, 0.0], set())

def detect_country_coords(text="", default_country=None):
    _, name, coords, _ = detect_geo_entity(text, default_country)
    return (name, coords)


def clean_and_complete_description(title="", description="", country_name=""):
    t_clean = (title or "").rstrip(".").strip()
    d_raw = (description or "").strip()
    
    # Strip trailing links, ads, and truncation markers
    d_clean = re.sub(r'Read More:\s*https?://\S+', '', d_raw, flags=re.IGNORECASE)
    d_clean = re.sub(r'\[\+\d+\s*chars?\]', '', d_clean, flags=re.IGNORECASE)
    d_clean = re.sub(r'<[^>]+>', '', d_clean).strip()
    
    if d_clean:
        if not d_clean.endswith(('.', '!', '?')):
            last_period = max(d_clean.rfind('.'), d_clean.rfind('!'), d_clean.rfind('?'))
            if last_period > 35:
                d_clean = d_clean[:last_period + 1]
            else:
                words = d_clean.split()
                if len(words) > 3:
                    d_clean = " ".join(words[:-1]) + "."
                else:
                    d_clean = d_clean.rstrip(' ,;:-') + "."
    else:
        d_clean = f"Frontline humanitarian teams report ongoing emergency developments across {country_name or 'the affected region'}, requiring coordinated relief operations."

    return d_clean


def analyze_crisis_article(title="", description="", country_name=""):
    text_combined = f"{title} {description}".lower()

    if any(w in text_combined for w in ["war", "strike", "attack", "militia", "clash", "bomb", "missile", "troop", "killing", "atrocit", "hostage", "ceasefire", "military", "combat"]):
        crisis_type = "Armed Conflict & Violence"
        default_urgency = "CRITICAL"
        needs = ["Emergency Trauma Kits", "Safe Passage Corridors", "Emergency Shelter Kits", "Psychosocial Care"]
    elif any(w in text_combined for w in ["flood", "earthquake", "quake", "storm", "hurricane", "typhoon", "cyclone", "wildfire", "tsunami", "drought", "landslide"]):
        crisis_type = "Natural Disaster & Climate Shock"
        default_urgency = "CRITICAL" if any(w in text_combined for w in ["dead", "kill", "mass", "submerged", "casualt"]) else "HIGH"
        needs = ["Clean Drinking Water", "Search & Rescue Units", "Temporary Tarpaulins", "Water Purification Kits"]
    elif any(w in text_combined for w in ["famine", "hunger", "starvat", "food", "malnutrition", "crops"]):
        crisis_type = "Food Insecurity & Famine"
        default_urgency = "CRITICAL"
        needs = ["Therapeutic Food Rations", "Infant Nutrition Packs", "Clean Water Supply", "Agricultural Recovery"]
    elif any(w in text_combined for w in ["refugee", "displace", "flee", "camp", "asylum", "migration", "exodus"]):
        crisis_type = "Displacement & Refugee Emergency"
        default_urgency = "HIGH"
        needs = ["Emergency Tents & Tarpaulins", "Sanitation Facilities", "Family Hygiene Kits", "Child Protection"]
    elif any(w in text_combined for w in ["cholera", "disease", "outbreak", "epidemic", "hospital", "medical", "virus", "health"]):
        crisis_type = "Health & Medical Emergency"
        default_urgency = "HIGH"
        needs = ["Essential Medications", "Mobile Field Clinics", "Vaccines & Cold-Chain", "IV Fluids & Antibiotics"]
    else:
        crisis_type = "Humanitarian Emergency"
        default_urgency = "HIGH"
        needs = ["Emergency Financial Aid", "Essential Relief Kits", "Emergency Medical Attention", "Community Shelter"]

    if any(w in text_combined for w in ["dead", "kill", "massacre", "catastroph", "apocalyptic", "urgent", "imminent", "mass killing"]):
        urgency = "CRITICAL"
    elif any(w in text_combined for w in ["severe", "escalat", "warning", "destruct", "thousands", "critical"]):
        urgency = "HIGH"
    else:
        urgency = default_urgency

    t_clean = title.rstrip(".").strip() if title else "Humanitarian Emergency"
    d_clean = clean_and_complete_description(title=title, description=description, country_name=country_name)
    
    # 1. Full In-Depth Situation Matter (The actual comprehensive text of the article)
    p1 = f"<strong>Field Assessment & Core Situation:</strong> {t_clean}. {d_clean}"
    
    p2 = (
        f"<strong>Humanitarian Impact & Displaced Populations:</strong> Across {country_name or 'the impacted region'}, "
        "civilian populations continue to experience severe strain on basic lifelines and civil infrastructure. "
        "Emergency reports highlight critical shortages of essential medicines, acute trauma supplies, "
        "potable drinking water, and safe shelter facilities for displaced families."
    )
    
    p3 = (
        "<strong>Frontline Logistics & Safe Corridors:</strong> Humanitarian agencies, international relief coordinators, "
        "and local volunteer networks are mobilizing emergency supply convoys and field distribution hubs. "
        "Securing uninterrupted safe-passage corridors remains vital to delivering life-saving assistance "
        "to vulnerable and isolated communities."
    )
    
    p4 = (
        "<strong>Ongoing Monitoring & Priority Action:</strong> Emergency coordinators are maintaining continuous field assessments "
        "to track resource allocations, health risks, and logistics bottlenecks. "
        "Direct contributions to accredited humanitarian funds are essential to sustaining continuous food, medical, and shelter pipelines."
    )
    
    full_report = [p1, p2, p3, p4]

    takeaways = [
        f"<strong>Core Situation:</strong> {t_clean}.",
        f"<strong>On-the-Ground Impact:</strong> {d_clean}",
        f"<strong>Priority Needs:</strong> Immediate dispatch of {', '.join(needs[:2]).lower()} to front-line relief distribution centers.",
        "<strong>Humanitarian Response:</strong> Relief coordinators are mobilizing emergency supply lines and establishing safe corridors."
    ]

    timeline = [
        {
            "phase": "Background & Catalyst",
            "detail": f"Underlying regional vulnerabilities and acute escalations have intensified humanitarian pressures across {country_name or 'the impacted region'}."
        },
        {
            "phase": "Active Situation",
            "detail": f"{t_clean}. Essential infrastructure and community lifelines have sustained serious disruption."
        },
        {
            "phase": "Response & Corridors",
            "detail": "Emergency response agencies, international relief partners, and local volunteer networks are coordinating frontline relief."
        }
    ]

    return {
        "crisis_type": crisis_type,
        "urgency": urgency,
        "immediate_needs": needs,
        "cleaned_description": d_clean,
        "full_report": full_report,
        "takeaways": takeaways,
        "timeline": timeline
    }

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def fetch_news_from_api(country=None):
    if not os.environ.get("NEWS_API_KEY") or not os.environ.get("NEWS_API_URL"):
        return []
    params = {
        "apiKey": os.environ["NEWS_API_KEY"],
        "q": f"({country} AND (humanitarian+crisis -political+crisis -financial+crisis -president -movie -twitter))"
            if country else "humanitarian+crisis -political+crisis -financial+crisis -human+rights -president -movie -TV -twitter",
        "searchln": "title,description,content",
        "excludeDomains": "lifesciencesworld.com,psychologytoday.com,smallwarsjournal.com,leicarumors.com,"
                        "abcnews.go.com,sf.funcheap.com,fark.com,nypost.com,archdaily.com,vulture.com,designboom.com,gizmodo.com",
        "language": "en",
    }
    try:
        response = requests.get(os.environ["NEWS_API_URL"], params=params, timeout=8)
        response.raise_for_status()
        articles = response.json().get("articles", [])
        articles_with_images = [article for article in articles if article.get("urlToImage")]
        sorted_articles = sorted(
            articles_with_images,
            key=lambda article: datetime.fromisoformat(article["publishedAt"].replace("Z", "+00:00")),
            reverse=True
        )
        return sorted_articles
    except Exception as e:
        print(f"NewsAPI query notice: {e}")
        return []

def fetch_un_humanitarian_rss():
    headers = {"User-Agent": "Mozilla/5.0 CrisisAid/2.0"}
    un_urls = [
        "https://news.un.org/feed/subscribe/en/news/topic/humanitarian-aid/feed/rss.xml",
        "https://news.un.org/feed/subscribe/en/news/topic/peace-and-security/feed/rss.xml"
    ]
    articles = []
    seen_titles = set()
    for u in un_urls:
        try:
            resp = requests.get(u, headers=headers, timeout=6)
            if resp.ok:
                root = ET.fromstring(resp.content)
                for item in root.findall("./channel/item"):
                    t = item.find("title").text if item.find("title") is not None else ""
                    norm_t = re.sub(r"[^a-zA-Z0-9]", "", t.lower())
                    if not t or norm_t in seen_titles:
                        continue
                    seen_titles.add(norm_t)
                    desc_el = item.find("description")
                    raw_desc = desc_el.text if desc_el is not None else ""
                    clean_desc = re.sub(r"<[^>]+>", "", raw_desc).strip()
                    link = item.find("link").text if item.find("link") is not None else ""
                    enclosure = item.find("enclosure")
                    img_url = enclosure.get("url") if enclosure is not None else ""

                    pub_date_str = item.find("pubDate").text if item.find("pubDate") is not None else ""
                    try:
                        dt = datetime.strptime(pub_date_str[:25], "%a, %d %b %Y %H:%M:%S")
                        formatted_date = dt.strftime("%d-%m-%Y")
                    except Exception:
                        formatted_date = datetime.now().strftime("%d-%m-%Y")

                    articles.append({
                        "title": t,
                        "description": clean_desc[:280],
                        "url": link,
                        "urlToImage": img_url or "/static/assets/images/hero-active.jpg",
                        "publishedAt": formatted_date,
                        "source": "UN OCHA / UN News"
                    })
        except Exception as e:
            print(f"UN Humanitarian feed notice: {e}")
    return articles

def fetch_multi_source_news(country=None):
    all_articles = []
    seen_titles = set()

    # 1. Fetch from NewsAPI
    try:
        api_articles = fetch_news_from_api(country)
        for a in api_articles:
            t = a.get("title", "")
            norm_t = re.sub(r"[^a-zA-Z0-9]", "", t.lower())
            if norm_t and norm_t not in seen_titles:
                seen_titles.add(norm_t)
                all_articles.append(a)
    except Exception as e:
        print(f"NewsAPI fetch notice: {e}")

    # 2. Supplement with UN Humanitarian RSS feeds
    try:
        un_articles = fetch_un_humanitarian_rss()
        for a in un_articles:
            if country:
                c_lower = country.lower()
                if c_lower not in a["title"].lower() and c_lower not in a["description"].lower():
                    continue
            t = a.get("title", "")
            norm_t = re.sub(r"[^a-zA-Z0-9]", "", t.lower())
            if norm_t and norm_t not in seen_titles:
                seen_titles.add(norm_t)
                all_articles.append(a)
    except Exception as e:
        print(f"UN RSS supplement notice: {e}")

    return all_articles


async def insert_news_in_db(country=None):
    articles = fetch_multi_source_news(country)
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
            
            pub_val = str(article.get("publishedAt") or "")
            if len(pub_val) == 10 and pub_val[2] == "-" and pub_val[5] == "-":
                formatted_pub = pub_val
            else:
                try:
                    dt = datetime.fromisoformat(pub_val.replace("Z", "+00:00").replace("T", " "))
                    formatted_pub = dt.strftime("%d-%m-%Y")
                except Exception:
                    formatted_pub = datetime.now().strftime("%d-%m-%Y")

            db_article = NewsArticle(
                title=article.get("title"),
                description=article.get("description"),
                content="",
                url=article.get("url"),
                link="",
                urlToImage=article.get("urlToImage"),
                publishedAt=formatted_pub
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


def clean_summary_text(text):
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)  # remove bold
    text = re.sub(r"\*(.*?)\*", r"\1", text)      # remove italic
    text = re.sub(r"^\s*[\*\-•]\s*", '', text, flags=re.MULTILINE)  # remove bullets
    text = re.sub(r"^\s*#+\s*", '', text, flags=re.MULTILINE) # remove hashes
    text = text.strip()
    return text


async def generate_content(title="", description=""):
    # Run in-memory local LLM (Qwen2.5) for text synthesis
    prompt = (
        f"Write a detailed, factual and structured humanitarian report based on this development:\n"
        f"Title: {title}\nDescription: {description}\n"
        "Provide 3-5 structured bullet points detailing context, civilian impact, and relief operations."
    )
    system_prompt = "You are CrisisAid AI, an expert humanitarian crisis analyst."
    
    try:
        report_text, provider = await LLMServiceFactory.generate_with_fallback(prompt, system_prompt)
        if report_text and len(report_text) > 30:
            return clean_summary_text(report_text)
    except Exception as e:
        print(f"[Local LLM] Report generation fallback notice: {e}")

    # Deterministic fallback structured report
    t = title.rstrip(".").strip() if title else "Humanitarian Crisis Development"
    d = description.strip() if description else "Emergency response teams are monitoring relief efforts on the ground."
    points = [
        f"<strong>Key Development:</strong> {t}.",
        f"<strong>Situational Overview:</strong> {d}",
        "<strong>Humanitarian Impact:</strong> Impacted populations face urgent shortages of critical supplies, food, and clean water.",
        "<strong>Relief & Response:</strong> International aid organizations and local emergency response teams are coordinating relief corridors and emergency assistance.",
        "<strong>Ongoing Monitoring:</strong> Aid coordinators continue to assess immediate needs to ensure support reaches affected communities."
    ]
    return "\n".join(points)


async def get_donation_link(news="", country=None):
    # Step 1: Check if country is explicitly passed and exists in verified donation_links
    if country and country != "None" and country in donation_links:
        return donation_links[country]

    # Step 2: Check if any country in donation_links is mentioned in news text
    if news:
        news_lower = news.lower()
        for c_name, c_link in donation_links.items():
            if len(c_name) > 3 and c_name.lower() in news_lower:
                return c_link

    # Default verified global humanitarian relief fund
    return "https://www.redcross.org/donate/donation.html/"


def generate_audio_summary(articles=None, filename="static/assets/audio_summary/summary.mp3"):
    Path(filename).parent.mkdir(parents=True, exist_ok=True)
    summary_text = None

    if articles and len(articles) > 0:
        lines = ["Here is today's humanitarian crisis audio briefing."]
        for art in articles[:4]:
            title = getattr(art, "title", "") or ""
            title = title.rstrip(".").strip()
            if title:
                lines.append(f"In top developments: {title}.")
        lines.append("Stay informed and consider supporting verified relief efforts.")
        summary_text = " ".join(lines)
    else:
        summary_text = "Welcome to Crisis Aid. Stay informed on global humanitarian updates and support emergency relief worldwide."

    summary_text = clean_summary_text(summary_text)

    # Generate MP3 using Google Text-to-Speech
    tts = gTTS(text=summary_text, lang='en')
    tts.save(filename)
    return summary_text
    tts.save(filename)
    return summary_text


def get_hero_image(country, articles=None):
    if os.environ.get("SEARCH_ENGINE_ID") and os.environ.get("CUSTOM_SEARCH_API_KEY") and os.environ.get("CUSTOM_SEARCH_URL"):
        try:
            params = {
                "q": f"humanitarian+crisis+in+{country}",
                "cx": os.environ["SEARCH_ENGINE_ID"],
                "key": os.environ["CUSTOM_SEARCH_API_KEY"],
                "searchType": "image",
                "num": 1
            }
            response = requests.get(os.environ["CUSTOM_SEARCH_URL"], params=params, timeout=6)
            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                if items and "link" in items[0]:
                    return items[0]["link"]
        except Exception as e:
            print(f"Error fetching image for {country}: {e}")

    # Fallback 1: Use the image from the first matching article
    if articles:
        for art in articles:
            img = getattr(art, "urlToImage", None) or (art.get("urlToImage") if isinstance(art, dict) else None)
            if img:
                return img

    # Fallback 2: Local default hero image
    return "/static/assets/images/hero1.jpg"


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


def is_audio_fresh():
    if not SUMMARY_MP3_PATH.exists() or not SUMMARY_TIMESTAMP_PATH.exists():
        return False

    try:
        with open(SUMMARY_TIMESTAMP_PATH, "r") as f:
            last_generated_date = f.read().strip()
        today = datetime.now().strftime("%Y-%m-%d")
        return last_generated_date == today
    except Exception:
        return False


def mark_audio_updated():
    SUMMARY_TIMESTAMP_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SUMMARY_TIMESTAMP_PATH, "w") as f:
        f.write(datetime.now().strftime("%Y-%m-%d"))
    print("audio updated.")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db)):
    await insert_news_in_db()
    articles = db.query(NewsArticle).limit(30).all()
    py_articles = [PydanticNewsArticle.model_validate(article) for article in articles]
    
    # Extract dynamic breaking news slides for the carousel
    carousel_slides = []
    for a in articles:
        if a.urlToImage and a.urlToImage.startswith("http"):
            c_name, _ = detect_country_coords(f"{a.title} {a.description or ''}")
            carousel_slides.append({
                "id": a.id,
                "title": a.title,
                "description": a.description or "",
                "image": a.urlToImage,
                "country": c_name,
                "publishedAt": a.publishedAt,
                "donate_link": donation_links.get(c_name, a.link if (a.link and a.link.startswith("http")) else "https://www.redcross.org/donate/donation.html/")
            })
        if len(carousel_slides) >= 3:
            break

    # Fallback to curated slides if fewer than 2 valid slides found
    if len(carousel_slides) < 2:
        carousel_slides = FALLBACK_CAROUSEL_SLIDES

    voice_ready = False
    try:
        if not is_audio_fresh():
            await asyncio.to_thread(generate_audio_summary, articles)
            mark_audio_updated()
        else:
            print("Using cached summary.mp3")
        voice_ready = SUMMARY_MP3_PATH.exists()
    except Exception as e:
        print("Voice generation failed:", e)
        # Fall back to existing cached summary if available
        voice_ready = SUMMARY_MP3_PATH.exists()

    audio_version = int(SUMMARY_MP3_PATH.stat().st_mtime) if SUMMARY_MP3_PATH.exists() else int(time.time())

    return templates.TemplateResponse("index.html", {
        "request": request,
        "all_articles": py_articles,
        "carousel_slides": carousel_slides,
        "year": datetime.now().strftime("%Y"),
        "voice_ready": voice_ready,
        "audio_version": audio_version
    })


@app.get("/search", response_class=HTMLResponse)
async def search_news(request: Request, db: Session = Depends(get_db), country: str = Query(...)):
    await insert_news_in_db(country)
    # articles = db.query(NewsArticle).filter(func.lower(NewsArticle.title).contains(func.lower(country))).all()
    articles = db.query(NewsArticle).all()
    if articles:
        hero_image = get_hero_image(country, articles)
        donation_link_hero = await get_donation_link(f"news related to {country}", country=country)
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

    # Detect country name & coordinates for interactive mini-map
    detected_country, coords = detect_country_coords(f"{article.title} {article.description or ''}", country)

    # Rich crisis intelligence analysis
    analysis = analyze_crisis_article(title=article.title, description=article.description, country_name=detected_country)

    # Verified donation link
    if not article.link or not article.link.startswith("http"):
        article.link = await get_donation_link(news=article.title, country=detected_country)

    # Store formatted takeaways in article.content if not already populated
    if not article.content or len(article.content.strip()) < 10:
        article.content = "\n".join(analysis["takeaways"])

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error updating article in db: {e}")

    # Specific country verified donation link (if in CSV), otherwise general
    country_relief_link = donation_links.get(detected_country, article.link or "https://www.redcross.org/donate/donation.html/")

    return templates.TemplateResponse("news_article.html", {
        "request": request,
        "article": article,
        "country": country if country != "None" else detected_country,
        "detected_country": detected_country,
        "coords": coords,
        "analysis": analysis,
        "country_relief_link": country_relief_link,
        "relief_partners": GLOBAL_RELIEF_PARTNERS
    })


@app.get("/chat", response_class=HTMLResponse)
async def chat(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})

class ChatRequest(BaseModel):
    message: str

CHAT_STOP_WORDS = {
    'what', 'when', 'where', 'which', 'who', 'whom', 'this', 'that', 'these', 'those',
    'am', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
    'do', 'does', 'did', 'doing', 'a', 'an', 'the', 'and', 'but', 'if', 'or', 'because',
    'as', 'until', 'while', 'of', 'at', 'by', 'for', 'with', 'about', 'against', 'between',
    'into', 'through', 'during', 'before', 'after', 'above', 'below', 'to', 'from',
    'up', 'down', 'in', 'out', 'on', 'off', 'over', 'under', 'again', 'further', 'then',
    'once', 'here', 'there', 'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other',
    'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very',
    'can', 'will', 'just', 'should', 'now', 'news', 'update', 'updates', 'latest', 'today',
    'tell', 'give', 'show', 'happening', 'going', 'please', 'crisis', 'crises'
}

async def generate_ai_chat_response(user_message: str, db: Session = None):
    msg_lower = user_message.lower().strip()
    geo_type, geo_name, geo_coords, geo_target_countries = detect_geo_entity(user_message)
    verified_donation_url = donation_links.get(geo_name) if geo_type == "country" else None

    # Step 1: Ranked search in database
    matched_articles = []
    all_db_articles = []
    if db:
        try:
            all_db_articles = db.query(NewsArticle).all()
            words = [re.sub(r'[^a-z0-9]', '', w) for w in msg_lower.split()]
            keywords = [w for w in words if len(w) >= 3 and w not in CHAT_STOP_WORDS]

            scored = []
            for art in all_db_articles:
                title_l = (art.title or "").lower()
                desc_l = (art.description or "").lower()
                art_text = f"{title_l} {desc_l}"
                art_geo_type, art_c_name, _, _ = detect_geo_entity(art_text)
                score = 0

                # Match by region / continent
                if geo_type == "region":
                    if art_c_name.lower() in geo_target_countries:
                        score += 20
                    elif any(c in art_text for c in geo_target_countries):
                        score += 12

                # Match by specific country
                elif geo_type == "country":
                    if art_c_name.lower() == geo_name.lower():
                        score += 25
                    elif geo_name.lower() in title_l:
                        score += 15
                    elif geo_name.lower() in desc_l:
                        score += 8

                # Match by remaining keywords
                for kw in keywords:
                    if kw in title_l:
                        score += 4
                    elif kw in desc_l:
                        score += 2

                if score > 0:
                    scored.append((score, art))

            scored.sort(key=lambda x: x[0], reverse=True)
            matched_articles = [art for score, art in scored]
        except Exception as e:
            print(f"Chat DB ranking notice: {e}")

    # Context for LLM
    context_articles = matched_articles[:5] if matched_articles else all_db_articles[:5]
    context_snippets = []
    for a in context_articles:
        context_snippets.append(f"• Title: {a.title}\n  Summary: {a.description or ''}\n  Date: {a.publishedAt}")
    live_news_context = "\n\n".join(context_snippets)

    # Step 2: Try Gemini LLM
    if os.environ.get("GEMINI_API_KEY") and os.environ.get("GEMINI_API_URL"):
        try:
            system_prompt = (
                "You are CrisisAid AI, an authoritative, empathetic, and factual humanitarian crisis assistant.\n"
                "Your objective is to provide accurate, real-time crisis intelligence, emergency relief guidance, verified donation information, and disaster safety advice.\n"
                "Ground your answers in the following live crisis news reports currently in the CrisisAid database:\n\n"
                f"--- LIVE CRISIS DATA ---\n{live_news_context}\n-----------------------\n\n"
                f"User Question: {user_message}\n\n"
                "Instructions:\n"
                "- If the user asks about a specific country or continent/region, focus directly on that area and the matching news reports.\n"
                "- Highlight critical facts, affected populations, and active emergency zones.\n"
                "- Mention verified relief organizations (MSF, WFP, Red Cross/ICRC, UNHCR) where appropriate.\n"
                "- Use bolding for key terms and bullet points for lists.\n"
                "- Keep responses structured, concise, and informative."
            )

            payload = {
                "contents": [{
                    "parts": [{"text": system_prompt}]
                }]
            }
            params = {"key": os.environ["GEMINI_API_KEY"]}
            headers = {"Content-Type": "application/json"}
            response = requests.post(os.environ["GEMINI_API_URL"], json=payload, params=params, headers=headers, timeout=12)
            if response.status_code == 200:
                data = response.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts and "text" in parts[0]:
                        raw_text = parts[0]["text"]
                        raw_text = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", raw_text)
                        raw_text = re.sub(r"^\*\s+", "• ", raw_text, flags=re.MULTILINE)
                        return raw_text.strip()
        except Exception as e:
            print(f"Gemini chat generation notice: {e}. Falling back to local intelligence engine.")

    # Step 3: Local Rule-Based Humanitarian Intelligence Engine Fallback

    # Greetings
    if any(msg_lower.startswith(g) for g in ["hi", "hello", "hey", "greetings", "howdy", "good morning", "good evening"]):
        return (
            "### 👋 Hello! I am CrisisAid AI.\n\n"
            "I provide real-time situational intelligence on active humanitarian crises, disaster response, and verified relief channels.\n\n"
            "**What you can ask me:**\n"
            "* **Countries & Regions:** e.g., *'Situation in Sudan'*, *'Africa crisis updates'*, or *'Middle East briefing'*\n"
            "* **Verified Aid Funds:** e.g., *'How can I donate to emergency relief?'*\n"
            "* **Disaster Preparedness:** e.g., *'Earthquake safety tips'*"
        )

    # Donation query
    if any(w in msg_lower for w in ["donate", "donation", "give", "contribute", "help", "fund", "charity"]):
        if verified_donation_url and geo_type == "country":
            return (
                f"### 💸 Verified Frontline Relief for {geo_name}\n\n"
                f"You can support verified frontline relief operations in **{geo_name}** directly:\n\n"
                f"👉 **[Official {geo_name} Verified Relief Fund ↗]({verified_donation_url})**\n\n"
                f"**Leading International Partners in {geo_name}:**\n"
                "* **Doctors Without Borders (MSF):** [Medical & Trauma Relief ↗](https://www.msf.org/donate)\n"
                "* **UN World Food Programme (WFP):** [Emergency Food Assistance ↗](https://www.wfp.org/donate)\n"
                "* **International Red Cross (ICRC):** [Neutral Humanitarian Corridors ↗](https://www.icrc.org/en/donate)"
            )
        return (
            "### 💸 Verified Humanitarian Relief Channels\n\n"
            "To ensure your donation reaches verified frontline responders on the ground, support accredited international partners:\n\n"
            "* **Medical & Trauma Care:** [Doctors Without Borders (MSF) ↗](https://www.msf.org/donate)\n"
            "* **Emergency Food & Nutrition:** [UN World Food Programme (WFP) ↗](https://www.wfp.org/donate)\n"
            "* **Refugee Shelter & Legal Protection:** [UNHCR ↗](https://donate.unhcr.org/)\n"
            "* **Neutral Rapid Corridors:** [International Red Cross (ICRC) ↗](https://www.icrc.org/en/donate)\n\n"
            "*You can also search for a specific country in the search bar to find localized relief funds.*"
        )

    # Disaster preparedness & safety query
    if any(w in msg_lower for w in ["safety", "prepare", "tips", "survival", "first aid", "kit", "preparedness"]):
        return (
            "### 🛡️ Emergency Disaster Preparedness Guidelines\n\n"
            "* **72-Hour Emergency Go-Bag:** Pack 1 gallon of water per person per day, non-perishable food, high-lumen flashlights, portable battery radio, and a trauma first-aid kit.\n"
            "* **Water Purification:** Boil water vigorously for at least 1 full minute or use chlorine water purification tablets before consumption during flood and earthquake emergencies.\n"
            "* **Family Communication Plan:** Establish an out-of-area emergency contact and designate two safe evacuation meeting points.\n"
            "* **Official Broadcasts:** Monitor local civil defense emergency frequencies and official Red Cross/Crescent alerts."
        )

    # Continent / Region query
    if geo_type == "region":
        if matched_articles:
            reports = []
            for art in matched_articles[:4]:
                t = art.title.rstrip(".")
                d = art.description or "Active humanitarian monitoring."
                _, c_name, _, _ = detect_geo_entity(f"{art.title} {art.description or ''}")
                reports.append(
                    f"* **{t}** `({c_name})`\n"
                    f"  {d} [Read Briefing ↗](/news_article/{art.id}/{c_name})"
                )
            return (
                f"### 🌍 Regional Humanitarian Intelligence: {geo_name}\n\n"
                f"Current crisis monitoring across **{geo_name}** identifies active emergency responses in affected zones:\n\n"
                + "\n\n".join(reports)
                + "\n\n👉 **Frontline Relief:** Support emergency relief through [International Red Cross Corridors ↗](https://www.icrc.org/en/donate)"
            )

    # Specific country query
    if geo_type == "country" and geo_name != "Global Crisis Region":
        if matched_articles:
            reports = []
            for art in matched_articles[:3]:
                t = art.title.rstrip(".")
                d = art.description or "Ongoing frontline monitoring."
                reports.append(
                    f"* **{t}**\n"
                    f"  {d} [Read Briefing ↗](/news_article/{art.id}/{geo_name})"
                )
            donate_btn = ""
            if verified_donation_url:
                donate_btn = f"\n\n👉 **Verified Action:** [Donate to {geo_name} Emergency Relief ↗]({verified_donation_url})"
            return f"### 🚨 Crisis Overview & Latest Reports for {geo_name}\n\n" + "\n\n".join(reports) + donate_btn
        else:
            relief_url = donation_links.get(geo_name, "https://www.redcross.org/donate/donation.html/")
            return (
                f"### 🚨 Humanitarian Situation in {geo_name}\n\n"
                f"Frontline monitoring indicates active humanitarian distress in **{geo_name}**. Aid agencies are coordinating emergency supplies and medical relief.\n\n"
                f"👉 **Verified Relief Action:** [Donate to {geo_name} Relief ↗]({relief_url})"
            )

    # General crisis updates query (or fallback for broad search)
    is_general_update = any(w in msg_lower for w in ["latest", "update", "updates", "overview", "breaking", "current", "news", "summary", "today", "global"])
    if is_general_update or not matched_articles:
        source_articles = all_db_articles[:4] if all_db_articles else []
        if source_articles:
            reports = []
            for art in source_articles:
                t = art.title.rstrip(".")
                d = art.description or "Active humanitarian monitoring."
                c_name, _ = detect_country_coords(f"{art.title} {art.description or ''}")
                reports.append(
                    f"* **{t}** `({c_name})`\n"
                    f"  {d} [Read Briefing ↗](/news_article/{art.id}/{c_name})"
                )
            return "### 🚨 Global Humanitarian Crisis Briefing (Latest Updates)\n\n" + "\n\n".join(reports)

    return (
        "### 🤖 CrisisAid Humanitarian Assistant\n\n"
        "I am actively tracking global emergencies, natural disasters, and frontline relief corridors.\n\n"
        "Try asking me about a specific country (e.g. *'Sudan'*, *'Gaza'*, *'Ukraine'*), "
        "a continent (e.g. *'Africa'*, *'Middle East'*, *'Asia'*), "
        "or ask how you can donate to verified relief efforts."
    )

@app.post("/generate/")
async def generate_chat(data: ChatQuery, db: Session = Depends(get_db)):
    user_message = data.message.strip()
    if not user_message:
        return {"response": "Please type a message so I can assist you.", "provider": "CrisisAid Local Engine"}

    selected_provider = data.provider or "local_rule"
    
    if selected_provider == "local_hf":
        try:
            bot_reply, provider_name = await LLMServiceFactory.generate_with_fallback(
                prompt=user_message,
                system_prompt="You are CrisisAid AI, a helpful humanitarian crisis assistant. Keep answers concise and direct.",
                preferred="local_hf"
            )
            return {"response": bot_reply, "provider": provider_name}
        except Exception as e:
            print(f"[Local HF] Notice: {e}. Using RAG Engine...")

    bot_reply = await generate_ai_chat_response(user_message, db=db)
    return {"response": bot_reply, "provider": "CrisisAid Local Intelligence Engine"}


@app.post("/stream_chat/")
async def stream_chat(data: ChatQuery, db: Session = Depends(get_db)):
    user_message = data.message.strip()
    if not user_message:
        async def empty_stream():
            yield f"data: {json.dumps({'type': 'token', 'chunk': 'Please type a question so I can assist you.'})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        return StreamingResponse(empty_stream(), media_type="text/event-stream")

    selected_provider = data.provider or "local_rule"

    async def sse_event_generator():
        if selected_provider == "local_hf":
            try:
                yield f"data: {json.dumps({'type': 'meta', 'provider': 'Local In-Memory LLM (Qwen2.5)'})}\n\n"
                async for item in LLMServiceFactory.stream_with_fallback(
                    prompt=user_message,
                    system_prompt="You are CrisisAid AI, a helpful humanitarian crisis assistant.",
                    preferred="local_hf"
                ):
                    if item.get("type") == "token":
                        yield f"data: {json.dumps(item)}\n\n"
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                return
            except Exception as e:
                print(f"[Local HF Stream] Notice: {e}. Cascading to RAG Engine...")

        # Primary Instant RAG Intelligence Engine
        bot_reply = await generate_ai_chat_response(user_message, db=db)
        yield f"data: {json.dumps({'type': 'meta', 'provider': 'CrisisAid Local Intelligence Engine'})}\n\n"
        
        words = re.split(r'(\s+)', bot_reply)
        for w in words:
            if w:
                yield f"data: {json.dumps({'type': 'token', 'chunk': w})}\n\n"
                await asyncio.sleep(0.012)
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(sse_event_generator(), media_type="text/event-stream")


@app.get("/locate", response_class=HTMLResponse)
async def locate(request: Request):
    return templates.TemplateResponse("locate.html", {"request": request})


@app.get("/get_crisis_countries")
async def get_crisis_countries(db: Session = Depends(get_db)):
    articles = db.query(NewsArticle).all()
    crisis_hotspots = []
    seen_articles = set()

    for art in articles:
        if art.id in seen_articles:
            continue
        desc = art.description or ""
        text = f"{art.title} {desc}"
        geo_type, geo_name, coords, _ = detect_geo_entity(text)

        if geo_type == "country" and geo_name != "Global Crisis Region" and coords and len(coords) == 2:
            continent = "Other"
            for reg_k, reg_v in CONTINENTS_REGIONS.items():
                if geo_name.lower() in reg_v["countries"]:
                    continent = reg_v["name"]
                    break

            analysis = analyze_crisis_article(art.title, desc, geo_name)
            donate_url = donation_links.get(geo_name, art.link if (art.link and art.link.startswith("http")) else "https://www.redcross.org/donate/donation.html/")
            d_snippet = desc[:130] + ("..." if len(desc) > 130 else "")

            image_url = art.urlToImage if (art.urlToImage and art.urlToImage.startswith("http")) else "/static/assets/images/hero-active.jpg"
            crisis_hotspots.append({
                "id": art.id,
                "country": geo_name,
                "name": geo_name,
                "continent": continent,
                "title": art.title,
                "news": art.title,
                "description": d_snippet,
                "image": image_url,
                "img": image_url,
                "lat": coords[0],
                "lng": coords[1],
                "urgency": analysis.get("urgency", "HIGH"),
                "crisis_type": analysis.get("crisis_type", "Humanitarian Emergency"),
                "donate_url": donate_url,
                "briefing_url": f"/news_article/{art.id}/{geo_name}"
            })
            seen_articles.add(art.id)

    return {
        "crisis_countries": crisis_hotspots,
        "total_hotspots": len(crisis_hotspots),
        "total_countries": len(set(h["country"] for h in crisis_hotspots))
    }


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
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))


# Uncomment the lines below to run the app with hot reloading
# if __name__ == "__main__":
#     uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), reload=True)

# or write "uvicorn main:app --reload" in terminal
