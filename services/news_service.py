import re
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from core.config import settings
from core.database import SessionLocal
from core.logging_config import logger
from models import NewsArticle


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
            for item in root.findall("./channel/item")[:15]:
                t = item.find("title").text if item.find("title") is not None else ""
                if not t:
                    continue
                desc_el = item.find("description")
                raw_desc = desc_el.text if desc_el is not None else ""
                clean_desc = re.sub(r"<[^>]+>", "", raw_desc).strip()
                link = item.find("link").text if item.find("link") is not None else "https://www.gdacs.org"

                articles.append({
                    "title": t,
                    "description": clean_desc[:300] if clean_desc else "Active disaster telemetry report from GDACS.",
                    "url": link,
                    "urlToImage": "/static/assets/images/hero-active.jpg",
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
            for feat in data.get("features", [])[:10]:
                props = feat.get("properties", {})
                title = props.get("title", "")
                url_link = props.get("url", "https://earthquake.usgs.gov")
                mag = props.get("mag", "")
                place = props.get("place", "")

                articles.append({
                    "title": f"Magnitude {mag} Earthquake Alert: {place}",
                    "description": f"Seismic alert recorded at {place}. Primary seismic sensor monitoring active through USGS.",
                    "url": url_link,
                    "urlToImage": "/static/assets/images/hero-active.jpg",
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
            logger.warning("UN Humanitarian feed notice for %s: %s", url, e)

    return articles


def fetch_multi_source_news(country: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Multi-Tier Aggregator: Ingests Primary Disaster Telemetry (GDACS, USGS)
    alongside UN OCHA RSS feeds and NewsAPI with cross-source deduplication.
    """
    all_articles = []
    seen_titles = set()

    # 1. Primary Disaster Telemetry (GDACS)
    try:
        gdacs_events = fetch_gdacs_alerts()
        for a in gdacs_events:
            if country and country.lower() not in a["title"].lower():
                continue
            t = a.get("title", "")
            norm_t = re.sub(r"[^a-zA-Z0-9]", "", t.lower())
            if norm_t and norm_t not in seen_titles:
                seen_titles.add(norm_t)
                all_articles.append(a)
    except Exception as e:
        logger.warning("GDACS aggregator notice: %s", e)

    # 2. Primary Seismic Telemetry (USGS)
    try:
        usgs_events = fetch_usgs_earthquakes()
        for a in usgs_events:
            if country and country.lower() not in a["title"].lower():
                continue
            t = a.get("title", "")
            norm_t = re.sub(r"[^a-zA-Z0-9]", "", t.lower())
            if norm_t and norm_t not in seen_titles:
                seen_titles.add(norm_t)
                all_articles.append(a)
    except Exception as e:
        logger.warning("USGS aggregator notice: %s", e)

    # 3. UN OCHA / UN News RSS feeds
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
        logger.warning("UN RSS supplement error: %s", e)

    # 4. NewsAPI Coverage
    try:
        api_articles = fetch_news_from_api(country)
        for a in api_articles:
            t = a.get("title", "")
            norm_t = re.sub(r"[^a-zA-Z0-9]", "", t.lower())
            if norm_t and norm_t not in seen_titles:
                seen_titles.add(norm_t)
                all_articles.append(a)
    except Exception as e:
        logger.warning("NewsAPI fetch error: %s", e)

    return all_articles


async def insert_news_in_db(country: Optional[str] = None) -> None:
    """ETL Pipeline: Fetches, normalizes, and upserts fresh articles into SQLite."""
    articles = fetch_multi_source_news(country)
    try:
        with SessionLocal() as db:
            rows_deleted = db.query(NewsArticle).delete()
            db.commit()
            logger.info("Cleared %d existing records from NewsArticle.", rows_deleted)

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
                    urlToImage=article.get("urlToImage"),
                    publishedAt=formatted_pub
                )
                db.add(db_article)
                db_articles.append(db_article)

            db.commit()
            logger.info("Successfully persisted %d multi-source articles into database.", len(db_articles))
    except Exception as e:
        logger.error("Error updating database in insert_news_in_db: %s", e)
