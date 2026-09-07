import requests
from typing import Optional
from core.config import settings
from core.logging_config import logger

_MEDIA_CACHE: dict = {}


DISASTER_KEYWORDS = [
    'disaster', 'flood', 'relief', 'earthquake', 'cyclone', 'crisis',
    'landslide', 'drought', 'storm', 'emergency', 'tsunami', 'conflict',
    'rescue', 'humanitarian', 'famine', 'wildfire', 'war'
]

PERSON_OR_UNWANTED_TITLES = [
    'actor', 'actress', 'film', 'cinema', 'politician', 'singer',
    'cricket', 'player', 'model', 'minister', 'demographics', 'flag of',
    'coat of arms', 'economy of', 'politics of', 'music', 'album', 'biography', 'song'
]

UNWANTED_KEYWORDS = [
    'flag', 'coat_of_arms', 'seal', 'emblem', 'icon', 'pyramid',
    'locator', 'map', 'diagram', 'chart', 'symbol', '.svg', 'insignia',
    'portrait', 'headshot'
]


def fetch_wiki_media_image(query: str) -> Optional[str]:
    """
    Queries Wikimedia & Wikipedia Open Media for high-resolution crisis photography.
    Strictly filters for disaster/humanitarian events and filters out actors/celebrities/maps/flags.
    """
    q_clean = query.strip()
    if not q_clean:
        return None

    cache_key = q_clean.lower()
    if cache_key in _MEDIA_CACHE:
        return _MEDIA_CACHE[cache_key]

    c_lower = q_clean.lower()
    c_root = c_lower[:-1] if len(c_lower) > 5 and c_lower.endswith('n') else c_lower

    headers = {'User-Agent': 'CrisisAid-Intelligence/2.5 (contact@crisisaid.org)'}
    search_queries = [
        f"{q_clean} disaster relief",
        f"Floods in {q_clean}",
        f"{q_clean} humanitarian crisis",
        f"Natural disasters in {q_clean}",
        f"{q_clean} crisis disaster",
        q_clean
    ]

    # Pass 1: Strict match - article title must relate to the country AND a disaster event
    for sq in search_queries:
        try:
            params = {
                'action': 'query',
                'generator': 'search',
                'gsrsearch': sq,
                'gsrlimit': 8,
                'prop': 'pageimages',
                'piprop': 'thumbnail',
                'pithumbsize': 1200,
                'format': 'json'
            }
            resp = requests.get('https://en.wikipedia.org/w/api.php', params=params, headers=headers, timeout=3.5)
            if resp.ok:
                pages = resp.json().get('query', {}).get('pages', {})
                sorted_pages = sorted(pages.values(), key=lambda p: p.get('index', 99))
                for page in sorted_pages:
                    thumb = page.get('thumbnail', {}).get('source')
                    title = page.get('title', '')
                    title_l = title.lower()
                    if thumb:
                        thumb_l = thumb.lower()
                        if any(ext in thumb_l for ext in ['.jpg', '.jpeg', '.webp']):
                            if any(u in thumb_l for u in UNWANTED_KEYWORDS):
                                continue
                            if any(u in title_l for u in PERSON_OR_UNWANTED_TITLES):
                                continue
                            has_country = (c_lower in title_l) or (c_root in title_l)
                            has_disaster = any(k in title_l for k in DISASTER_KEYWORDS)
                            if has_country and has_disaster:
                                logger.info('[Media Search] Found high-res disaster photo for %s via "%s": %s', query, title, thumb)
                                _MEDIA_CACHE[cache_key] = thumb
                                return thumb
        except Exception as e:
            logger.debug('[Media Search] Pass 1 error on "%s": %s', sq, e)
            continue

    # Pass 2: Relaxed disaster photo match (valid disaster page without strict country in title)
    for sq in search_queries:
        try:
            params = {
                'action': 'query',
                'generator': 'search',
                'gsrsearch': sq,
                'gsrlimit': 6,
                'prop': 'pageimages',
                'piprop': 'thumbnail',
                'pithumbsize': 1200,
                'format': 'json'
            }
            resp = requests.get('https://en.wikipedia.org/w/api.php', params=params, headers=headers, timeout=3.5)
            if resp.ok:
                pages = resp.json().get('query', {}).get('pages', {})
                sorted_pages = sorted(pages.values(), key=lambda p: p.get('index', 99))
                for page in sorted_pages:
                    thumb = page.get('thumbnail', {}).get('source')
                    title = page.get('title', '')
                    title_l = title.lower()
                    if thumb:
                        thumb_l = thumb.lower()
                        if any(ext in thumb_l for ext in ['.jpg', '.jpeg', '.webp']):
                            if any(u in thumb_l for u in UNWANTED_KEYWORDS):
                                continue
                            if any(u in title_l for u in PERSON_OR_UNWANTED_TITLES):
                                continue
                            if any(k in title_l for k in DISASTER_KEYWORDS):
                                logger.info('[Media Search] Found contextual disaster photo for %s via "%s": %s', query, title, thumb)
                                _MEDIA_CACHE[cache_key] = thumb
                                return thumb
        except Exception as e:
            logger.debug('[Media Search] Pass 2 error on "%s": %s', sq, e)
            continue

    return None


def fetch_custom_search_image(query: str) -> Optional[str]:
    """
    Main image search engine for crisis intelligence hero sections.
    1. Primary: Queries Wikimedia & Wikipedia Open Media (reliable, keyless, high-res crisis journalism).
    2. Fallback: Google Programmable Custom Search JSON API (if configured and permitted).
    """
    # 1. Primary: Open Media Crisis Photography
    media_img = fetch_wiki_media_image(query)
    if media_img:
        return media_img

    # 2. Secondary fallback: Google Custom Search API
    key = settings.CUSTOM_SEARCH_API_KEY.strip('"\'') if settings.CUSTOM_SEARCH_API_KEY else ''
    cx = settings.SEARCH_ENGINE_ID.strip('"\'') if settings.SEARCH_ENGINE_ID else ''
    url = settings.CUSTOM_SEARCH_URL or 'https://www.googleapis.com/customsearch/v1'

    if not key or not cx:
        return None

    try:
        params = {
            'key': key,
            'cx': cx,
            'q': f'{query} crisis disaster relief',
            'searchType': 'image',
            'num': 1,
            'safe': 'active',
            'imgSize': 'large'
        }
        resp = requests.get(url, params=params, timeout=4)
        if resp.ok:
            data = resp.json()
            items = data.get('items', [])
            if items and 'link' in items[0]:
                img_url = items[0]['link']
                if img_url.startswith('http'):
                    logger.info('[Custom Search API] Successfully fetched image for %s: %s', query, img_url)
                    return img_url
        else:
            logger.warning('[Custom Search API] Response %s: %s', resp.status_code, resp.text[:200])
    except Exception as e:
        logger.error('[Custom Search API] Request failed: %s', e)

    return None
