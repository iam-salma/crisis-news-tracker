import re
import random
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from core.config import settings
from core.database import SessionLocal
from core.logging_config import logger
from models import NewsArticle

# High-Resolution Contextual Crisis Photography for Telemetry Alerts
CRISIS_TELEMETRY_PHOTOS = {
    "earthquake": [
        "https://images.unsplash.com/photo-1588880331179-bc9b93a8cb5e?w=900&auto=format&fit=crop&q=75",
        "https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?w=900&auto=format&fit=crop&q=75"
    ],
    "cyclone": [
        "https://images.unsplash.com/photo-1527482797697-8795b05a13fe?w=900&auto=format&fit=crop&q=75",
        "https://images.unsplash.com/photo-1509114397022-ed747cca3f65?w=900&auto=format&fit=crop&q=75"
    ],
    "flood": [
        "https://images.unsplash.com/photo-1547683905-f686c993aae5?w=900&auto=format&fit=crop&q=75",
        "https://images.unsplash.com/photo-1517486808906-6ca8b3f04846?w=900&auto=format&fit=crop&q=75"
    ],
    "fire": [
        "https://images.unsplash.com/photo-1602980085566-4c6575724c4c?w=900&auto=format&fit=crop&q=75"
    ],
    "conflict": [
        "https://images.unsplash.com/photo-1579208575657-c595a05383b7?w=900&auto=format&fit=crop&q=75",
        "https://images.unsplash.com/photo-1488521787991-ed7bbaae773c?w=900&auto=format&fit=crop&q=75"
    ],
    "general": [
        "/static/assets/images/hero-active.jpg",
        "/static/assets/images/hero1.jpg",
        "/static/assets/images/hero2.jpg",
        "/static/assets/images/hero3.jpg"
    ]
}


def get_contextual_photo(text: str) -> str:
    """Assigns high-resolution contextual photo URL based on crisis keywords."""
    text_l = (text or "").lower()
    if any(w in text_l for w in ["earthquake", "quake", "seismic", "tremor"]):
        return random.choice(CRISIS_TELEMETRY_PHOTOS["earthquake"])
    elif any(w in text_l for w in ["cyclone", "hurricane", "typhoon", "storm", "tropical"]):
        return random.choice(CRISIS_TELEMETRY_PHOTOS["cyclone"])
    elif any(w in text_l for w in ["flood", "submerged", "rainfall", "inundation"]):
        return random.choice(CRISIS_TELEMETRY_PHOTOS["flood"])
    elif any(w in text_l for w in ["fire", "wildfire", "forest"]):
        return random.choice(CRISIS_TELEMETRY_PHOTOS["fire"])
    elif any(w in text_l for w in ["war", "strike", "attack", "refugee", "displaced", "clash", "bomb"]):
        return random.choice(CRISIS_TELEMETRY_PHOTOS["conflict"])
    return random.choice(CRISIS_TELEMETRY_PHOTOS["general"])


def fetch_news_from_api(country: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetches real-time humanitarian news from NewsAPI."""
    if not settings.NEWS_API_KEY or not settings.NEWS_API_URL:
        return []

    params = {
        "apiKey": settings.NEWS_API_KEY,
        "q": f"({country} AND (humanitarian+crisis -political+crisis -financial+crisis -president -movie -twitter))"
            if country else "humanitarian+crisis -political+crisis -financial+crisis -human+rights -president -movie -TV -twitter",
        "searchln": "title,description,content",
        "excludeDomains": "lifesciencesworld.com,psychologytoday.com,smallwarsjournal.com,leicarumors.com,"
                        "abcnews.go.com,sf.funcheap.com,fark.com,nypost.com,archdaily.com,vulture.com,designboom.com,gizmodo.com",
        "language": "en",
    }
    try:
        response = requests.get(settings.NEWS_API_URL, params=params, timeout=8)
        response.raise_for_status()
        articles = response.json().get("articles", [])
        articles_with_images = [a for a in articles if a.get("urlToImage")]
        sorted_articles = sorted(
            articles_with_images,
            key=lambda a: datetime.fromisoformat(a["publishedAt"].replace("Z", "+00:00")),
            reverse=True
        )
        return sorted_articles
    except Exception as e:
        logger.warning("NewsAPI query notice: %s", e)
        return []


def fetch_gdacs_alerts() -> List[Dict[str, Any]]:
    """Fetches Primary Disaster Telemetry from GDACS (Global Disaster Alert & Coordination System)."""
    headers = {"User-Agent": "Mozilla/5.0 CrisisAid/2.5"}
    url = "https://www.gdacs.org/xml/rss.xml"
    articles = []
    try:
        resp = requests.get(url, headers=headers, timeout=6)
        if resp.ok:
            root = ET.fromstring(resp.content)
            for item in root.findall("./channel/item")[:12]:
                t = item.find("title").text if item.find("title") is not None else ""
                if not t:
                    continue
                desc_el = item.find("description")
                raw_desc = desc_el.text if desc_el is not None else ""
                clean_desc = re.sub(r"<[^>]+>", "", raw_desc).strip()
                link = item.find("link").text if item.find("link") is not None else "https://www.gdacs.org"
                photo = get_contextual_photo(f"{t} {clean_desc}")

                articles.append({
                    "title": t,
                    "description": clean_desc[:300] if clean_desc else "Active disaster telemetry report from GDACS.",
                    "url": link,
                    "urlToImage": photo,
                    "publishedAt": datetime.now().strftime("%d-%m-%Y"),
                    "source": "GDACS Disaster Telemetry"
                })
    except Exception as e:
        logger.warning("GDACS feed ingestion notice: %s", e)
    return articles


def fetch_usgs_earthquakes() -> List[Dict[str, Any]]:
    """Fetches Primary Seismic Telemetry from USGS Significant Earthquake GeoJSON API."""
    url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_month.geojson"
    articles = []
    try:
        resp = requests.get(url, timeout=6)
        if resp.ok:
            data = resp.json()
            for feat in data.get("features", [])[:8]:
                props = feat.get("properties", {})
                title = props.get("title", "")
                url_link = props.get("url", "https://earthquake.usgs.gov")
                mag = props.get("mag", "")
                place = props.get("place", "")
                photo = get_contextual_photo("earthquake seismic")

                articles.append({
                    "title": f"Magnitude {mag} Earthquake Alert: {place}",
                    "description": f"Significant seismic event detected at {place}. Continuous monitoring through USGS Seismology.",
                    "url": url_link,
                    "urlToImage": photo,
                    "publishedAt": datetime.now().strftime("%d-%m-%Y"),
                    "source": "USGS Seismic Network"
                })
    except Exception as e:
        logger.warning("USGS Earthquake feed notice: %s", e)
    return articles


def fetch_un_humanitarian_rss() -> List[Dict[str, Any]]:
    """Fetches verified emergency reports from UN OCHA & UN News RSS feeds."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) CrisisAid/2.5"}
    un_urls = [
        "https://news.un.org/feed/subscribe/en/news/topic/humanitarian-aid/feed/rss.xml",
        "https://news.un.org/feed/subscribe/en/news/topic/peace-and-security/feed/rss.xml"
    ]
    articles = []
    seen_titles = set()

    for url in un_urls:
        try:
            resp = requests.get(url, headers=headers, timeout=6)
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
                    if not img_url:
                        img_url = get_contextual_photo(f"{t} {clean_desc}")

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
                        "urlToImage": img_url,
                        "publishedAt": formatted_date,
                        "source": "UN OCHA / UN News"
                    })
        except Exception as e:
            logger.warning("UN Humanitarian feed notice for %s: %s", url, e)

    return articles


def fetch_multi_source_news(country: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Multi-Tier Aggregator: Ingests Primary Disaster Telemetry (GDACS, USGS)
    alongside UN OCHA RSS feeds and NewsAPI with cross-source deduplication and dynamic shuffling.
    """
    newsapi_articles = []
    un_articles = []
    telemetry_articles = []
    seen_titles = set()

    # 1. NewsAPI Coverage (Rich Photography)
    try:
        raw_api = fetch_news_from_api(country)
        for a in raw_api:
            t = a.get("title", "")
            norm_t = re.sub(r"[^a-zA-Z0-9]", "", t.lower())
            if norm_t and norm_t not in seen_titles:
                seen_titles.add(norm_t)
                newsapi_articles.append(a)
    except Exception as e:
        logger.warning("NewsAPI fetch error: %s", e)

    # 2. UN OCHA / UN News RSS feeds
    try:
        raw_un = fetch_un_humanitarian_rss()
        for a in raw_un:
            if country:
                c_lower = country.lower()
                if c_lower not in a["title"].lower() and c_lower not in a["description"].lower():
                    continue
            t = a.get("title", "")
            norm_t = re.sub(r"[^a-zA-Z0-9]", "", t.lower())
            if norm_t and norm_t not in seen_titles:
                seen_titles.add(norm_t)
                un_articles.append(a)
    except Exception as e:
        logger.warning("UN RSS supplement error: %s", e)

    # 3. Primary Disaster Telemetry (GDACS + USGS)
    try:
        raw_gdacs = fetch_gdacs_alerts()
        for a in raw_gdacs:
            if country and country.lower() not in a["title"].lower():
                continue
            t = a.get("title", "")
            norm_t = re.sub(r"[^a-zA-Z0-9]", "", t.lower())
            if norm_t and norm_t not in seen_titles:
                seen_titles.add(norm_t)
                telemetry_articles.append(a)

        raw_usgs = fetch_usgs_earthquakes()
        for a in raw_usgs:
            if country and country.lower() not in a["title"].lower():
                continue
            t = a.get("title", "")
            norm_t = re.sub(r"[^a-zA-Z0-9]", "", t.lower())
            if norm_t and norm_t not in seen_titles:
                seen_titles.add(norm_t)
                telemetry_articles.append(a)
    except Exception as e:
        logger.warning("Telemetry aggregator notice: %s", e)

    # Shuffle each list to vary coverage
    random.shuffle(newsapi_articles)
    random.shuffle(un_articles)
    random.shuffle(telemetry_articles)

    # Interleave multi-source articles: NewsAPI (rich photo), UN OCHA, Telemetry
    interleaved = []
    max_len = max(len(newsapi_articles), len(un_articles), len(telemetry_articles), 1)
    for i in range(max_len):
        if i < len(newsapi_articles):
            interleaved.append(newsapi_articles[i])
        if i < len(un_articles):
            interleaved.append(un_articles[i])
        if i < len(telemetry_articles):
            interleaved.append(telemetry_articles[i])

    return interleaved


async def insert_news_in_db(country: Optional[str] = None) -> None:
    """ETL Pipeline: Fetches, normalizes, and upserts fresh articles into SQLite."""
    articles = fetch_multi_source_news(country)
    try:
        with SessionLocal() as db:
            # Only perform a full table clear during global periodic refresh (country is None)
            if not country:
                rows_deleted = db.query(NewsArticle).delete()
                db.commit()
                logger.info("Cleared %d existing records for global refresh.", rows_deleted)

            db_articles = []
            for article in articles:
                existing_article = db.query(NewsArticle).filter_by(title=article.get("title")).first()
                if existing_article:
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
                    urlToImage=article.get("urlToImage") or "/static/assets/images/hero-active.jpg",
                    publishedAt=formatted_pub
                )
                db.add(db_article)
                db_articles.append(db_article)

            db.commit()
            logger.info("Successfully persisted %d articles into database (filter=%s).", len(db_articles), country or "global")
    except Exception as e:
        logger.error("Error updating database in insert_news_in_db: %s", e)
