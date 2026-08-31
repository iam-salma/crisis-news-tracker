import requests
from typing import Optional, List, Any, Dict
from core.config import settings
from core.logging_config import logger
from services.news_service import get_contextual_photo

# In-memory image cache to avoid duplicate network latency
IMAGE_CACHE: Dict[str, str] = {}


def fetch_google_search_image(query: str) -> Optional[str]:
    """
    Searches Google Custom Search JSON API for high-resolution photography of a country, city, or region.
    Requires GOOGLE_API_KEY and GOOGLE_CSE_ID in environment / .env.
    """
    if not settings.GOOGLE_API_KEY or not settings.GOOGLE_CSE_ID:
        return None
    try:
        url = "https://customsearch.googleapis.com/customsearch/v1"
        params = {
            "key": settings.GOOGLE_API_KEY,
            "cx": settings.GOOGLE_CSE_ID,
            "q": f"{query} landscape scenery photography",
            "searchType": "image",
            "num": 1,
            "safe": "active",
            "imgSize": "large",
            "imgType": "photo"
        }
        resp = requests.get(url, params=params, timeout=3)
        if resp.ok:
            data = resp.json()
            items = data.get("items", [])
            if items and "link" in items[0]:
                img_url = items[0]["link"]
                if img_url.startswith("http") and not img_url.endswith(".svg"):
                    logger.info("Google Search API image retrieved for %s", query)
                    return img_url
    except Exception as e:
        logger.warning("Google Search API image fetch notice: %s", e)
    return None


def fetch_wikimedia_image(query: str) -> Optional[str]:
    """
    Retrieves authentic landmark or landscape photography from Wikipedia / Wikimedia REST API.
    Zero-configuration, instant, and supports any global country, city, or territory.
    """
    if not query:
        return None
    headers = {"User-Agent": "CrisisAid/2.5 (contact@crisisaid.org)"}
    variations = [query, f"{query} City", f"{query} Strip", f"{query} Province", f"{query} State"]
    for q in variations:
        try:
            url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(q)}"
            resp = requests.get(url, headers=headers, timeout=2.5)
            if resp.ok:
                data = resp.json()
                img_info = data.get("originalimage") or data.get("thumbnail")
                if img_info and "source" in img_info:
                    src = img_info["source"]
                    if src.startswith("http") and not src.endswith(".svg"):
                        return src
        except Exception:
            continue
    return None


def get_hero_image_for_query(query: str, articles: Optional[List[Any]] = None) -> str:
    """
    Multi-tier prioritized image resolver for country/city/region search:
    1. Check Memory Cache
    2. Google Custom Search JSON API (if configured)
    3. First verified article photograph
    4. Wikimedia / Wikipedia Landmark Photography
    5. Contextual High-Resolution Unsplash Photography
    """
    q_key = query.lower().strip()
    if q_key in IMAGE_CACHE:
        return IMAGE_CACHE[q_key]

    # 1. Google Search API
    google_img = fetch_google_search_image(query)
    if google_img:
        IMAGE_CACHE[q_key] = google_img
        return google_img

    # 2. Verified article image
    if articles:
        for a in articles:
            umg = getattr(a, "urlToImage", None) or (a.get("urlToImage") if isinstance(a, dict) else None)
            if umg and umg.startswith("http") and not umg.endswith("hero-active.jpg") and len(umg) > 15:
                IMAGE_CACHE[q_key] = umg
                return umg

    # 3. Wikimedia real-world photo
    wiki_img = fetch_wikimedia_image(query)
    if wiki_img:
        IMAGE_CACHE[q_key] = wiki_img
        return wiki_img

    # 4. Contextual Unsplash photo
    fallback_img = get_contextual_photo(f"{query} crisis disaster relief")
    IMAGE_CACHE[q_key] = fallback_img
    return fallback_img


