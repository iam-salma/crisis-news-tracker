"""
Crisis News Scraper — replaces NewsAPI with direct web scraping.

Strategy:
  1. RSS/Atom feeds (ReliefWeb, Al Jazeera, BBC) — clean, structured, respectful.
  2. HTML scraping fallback (Reuters) — when feeds aren't available.
  3. Caching layer — avoid hammering sources.
  4. NewsAPI fallback — when all scrapers fail, fall through to the API.

Output format matches NewsAPI's article schema so main.py needs zero structural changes.
"""

import re
import time
import json
import hashlib
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ── Cache ─────────────────────────────────────────────────────────────────
CACHE_DIR = Path("data/cache")
CACHE_TTL_SECONDS = 900  # 15 minutes


def _cache_key(*sources: str) -> str:
    raw = ":".join(sources)
    return hashlib.md5(raw.encode()).hexdigest()


def _cache_read(key: str) -> Optional[list[dict]]:
    path = CACHE_DIR / f"{key}.json"
    if not path.exists():
        return None
    age = time.time() - path.stat().st_mtime
    if age > CACHE_TTL_SECONDS:
        path.unlink(missing_ok=True)
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _cache_write(key: str, articles: list[dict]) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"{key}.json"
    path.write_text(json.dumps(articles, ensure_ascii=False, default=str), encoding="utf-8")


# ── Helpers ───────────────────────────────────────────────────────────────

def _normalise_article(
    raw: dict,
    source_name: str,
) -> Optional[dict]:
    """Normalise a scraper-raw dict into NewsAPI-shaped article."""
    title = (raw.get("title") or "").strip()
    if not title:
        return None
    
    # Parse publishedAt into ISO 8601
    pub = raw.get("publishedAt") or raw.get("published")
    if isinstance(pub, str):
        pub = pub.strip()
    elif hasattr(pub, "isoformat"):
        pub = pub.isoformat()
    if not pub:
        pub = datetime.now(timezone.utc).isoformat()

    # Image
    img = raw.get("urlToImage") or raw.get("media_content") or ""
    if isinstance(img, list) and img:
        img = img[0].get("href") or img[0].get("url", "")
    if isinstance(img, dict):
        img = img.get("href") or img.get("url", "")
    img = str(img) if img else ""

    desc = (raw.get("description") or raw.get("summary") or "").strip()
    link = (raw.get("link") or raw.get("url") or "").strip()

    return {
        "title": title,
        "description": desc[:500],
        "content": desc,
        "url": link,
        "urlToImage": img,
        "publishedAt": pub,
        "source": {"name": source_name},
    }


# ── Source scrapers ───────────────────────────────────────────────────────

def _fetch_reliefweb(country: Optional[str] = None) -> list[dict]:
    """
    ReliefWeb (UN OCHA) — humanitarian crises, excellent structured RSS.
    https://reliefweb.int/updates?search=crisis
    """
    raw_articles = []
    base = "https://reliefweb.int/updates/rss.xml"
    params = {"search": country or "humanitarian+crisis"}
    try:
        resp = requests.get(base, params=params, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml-xml")
        for item in soup.select("item"):
            ns = {
                "media": "http://search.yahoo.com/mrss/",
                "dc": "http://purl.org/dc/elements/1.1/",
            }
            raw_articles.append({
                "title": item.find("title").text if item.find("title") else "",
                "link": item.find("link").text if item.find("link") else "",
                "description": item.find("description").text if item.find("description") else "",
                "publishedAt": item.find("dc:date").text if item.find("dc:date") else "",
                "urlToImage": item.find("media:content")["url"] if item.find("media:content") else "",
            })
    except requests.RequestException as e:
        logger.warning("ReliefWeb scrape failed: %s", e)
    return raw_articles


def _fetch_aljazeera(country: Optional[str] = None) -> list[dict]:
    """Al Jazeera — RSS feed."""
    raw_articles = []
    feed_url = "https://www.aljazeera.com/xml/rss/all.xml"
    try:
        resp = requests.get(feed_url, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml-xml")
        for item in soup.select("item"):
            title = item.find("title").text if item.find("title") else ""
            if country and country.lower() not in title.lower():
                continue
            
            img = ""
            media_ns = item.find("media:content")
            if media_ns:
                img = media_ns.get("url", "")
            if not img:
                media_ns = item.find("media:thumbnail")
                if media_ns:
                    img = media_ns.get("url", "")

            raw_articles.append({
                "title": title,
                "link": item.find("link").text if item.find("link") else "",
                "description": item.find("description").text if item.find("description") else "",
                "publishedAt": item.find("pubDate").text if item.find("pubDate") else "",
                "urlToImage": img,
            })
    except requests.RequestException as e:
        logger.warning("Al Jazeera scrape failed: %s", e)
    return raw_articles


def _fetch_bbc(country: Optional[str] = None) -> list[dict]:
    """BBC News — RSS feed."""
    raw_articles = []
    feed_url = "https://feeds.bbci.co.uk/news/world/rss.xml"
    try:
        resp = requests.get(feed_url, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml-xml")
        for item in soup.select("item"):
            title = item.find("title").text if item.find("title") else ""
            if country and country.lower() not in title.lower():
                continue
            
            img = ""
            media_ns = item.find("media:thumbnail")
            if media_ns:
                img = media_ns.get("url", "")
            if not img:
                media_group = item.find("media:group")
                if media_group:
                    thumb = media_group.find("media:thumbnail")
                    if thumb:
                        img = thumb.get("url", "")

            raw_articles.append({
                "title": title,
                "link": item.find("link").text if item.find("link") else "",
                "description": item.find("description").text if item.find("description") else "",
                "publishedAt": item.find("pubDate").text if item.find("pubDate") else "",
                "urlToImage": img,
            })
    except requests.RequestException as e:
        logger.warning("BBC scrape failed: %s", e)
    return raw_articles


def _fetch_reuters(country: Optional[str] = None) -> list[dict]:
    """Reuters — HTML scraping of the world news page (no public RSS)."""
    raw_articles = []
    url = "https://www.reuters.com/world/"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
    }
    try:
        resp = requests.get(url, headers=headers, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        for article_tag in soup.select('[data-testid="MediaPromo"]'):
            title_el = article_tag.select_one("a")
            img_el = article_tag.select_one("img")
            title = title_el.get_text(strip=True) if title_el else ""
            link = title_el.get("href", "") if title_el else ""
            if link and not link.startswith("http"):
                link = "https://www.reuters.com" + link
            img = img_el.get("src", "") if img_el else ""

            if country and country.lower() not in title.lower():
                continue

            desc = ""
            desc_el = article_tag.select_one('[data-testid="Paragraph"]')
            if desc_el:
                desc = desc_el.get_text(strip=True)

            raw_articles.append({
                "title": title,
                "link": link,
                "description": desc,
                "publishedAt": datetime.now(timezone.utc).isoformat(),
                "urlToImage": img,
            })
    except requests.RequestException as e:
        logger.warning("Reuters scrape failed: %s", e)
    return raw_articles


# ── Public API (drop-in replacement for fetch_news_from_api) ───────────────

SOURCES = [
    ("ReliefWeb", _fetch_reliefweb),
    ("BBC News", _fetch_bbc),
    ("Reuters", _fetch_reuters),
    ("Al Jazeera", _fetch_aljazeera),
]


def fetch_news(country: Optional[str] = None) -> list[dict]:
    """
    Fetch crisis news via web scraping across multiple sources.
    Returns deduplicated, sorted articles matching NewsAPI schema.

    This is the direct replacement for fetch_news_from_api() in main.py.
    """
    cache_key = _cache_key("scraper", country or "__all__")
    cached = _cache_read(cache_key)
    if cached is not None:
        logger.info("Serving %d articles from cache", len(cached))
        return cached

    seen_titles: set[str] = set()
    all_articles: list[dict] = []

    for source_name, fetcher in SOURCES:
        try:
            raw_items = fetcher(country)
        except Exception as e:
            logger.error("Scraper %s raised: %s", source_name, e)
            continue

        for raw in raw_items:
            article = _normalise_article(raw, source_name)
            if article is None:
                continue
            title_hash = hashlib.md5(article["title"].encode()).hexdigest()
            if title_hash in seen_titles:
                continue
            seen_titles.add(title_hash)
            all_articles.append(article)

    # Sort by publishedAt descending (newest first)
    all_articles.sort(key=lambda a: a.get("publishedAt") or "", reverse=True)

    _cache_write(cache_key, all_articles)
    logger.info("Scraped %d unique articles from %d sources", len(all_articles), len(SOURCES))
    return all_articles


def fetch_news_with_api_fallback(
    api_fetcher,
    country: Optional[str] = None,
) -> list[dict]:
    """
    Try scraper first; if it returns fewer than 3 articles, fall through to
    the News API.  This gives you resilience without sacrificing autonomy.
    """
    articles = fetch_news(country)
    if len(articles) >= 3:
        return articles
    logger.info("Scraper returned only %d articles; falling back to API", len(articles))
    return api_fetcher(country)
