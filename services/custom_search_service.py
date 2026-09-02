import requests
from typing import Optional
from core.config import settings
from core.logging_config import logger


def fetch_custom_search_image(query: str) -> Optional[str]:
    """
    Queries Google Programmable Custom Search JSON API for the top image.
    Uses CUSTOM_SEARCH_API_KEY, SEARCH_ENGINE_ID, and CUSTOM_SEARCH_URL from .env.
    """
    key = settings.CUSTOM_SEARCH_API_KEY.strip('"\'') if settings.CUSTOM_SEARCH_API_KEY else ''
    cx = settings.SEARCH_ENGINE_ID.strip('"\'') if settings.SEARCH_ENGINE_ID else ''
    url = settings.CUSTOM_SEARCH_URL or 'https://www.googleapis.com/customsearch/v1'

    if not key or not cx:
        logger.info('[Custom Search API] Skipping: CUSTOM_SEARCH_API_KEY or SEARCH_ENGINE_ID not set in .env')
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
