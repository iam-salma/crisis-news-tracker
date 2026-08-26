import time
import asyncio
from pathlib import Path
from typing import List, Any
from gtts import gTTS
from core.config import settings
from core.logging_config import logger
from services.analysis_service import clean_summary_text


def get_audio_cache_version() -> str:
    """Returns audio cache version timestamp string."""
    if settings.SUMMARY_TIMESTAMP_PATH.exists():
        try:
            return settings.SUMMARY_TIMESTAMP_PATH.read_text().strip()
        except Exception:
            return str(int(time.time()))
    return str(int(time.time()))


async def generate_audio_summary(articles: List[Any]) -> None:
    """
    Synthesizes daily global humanitarian audio broadcast.
    Uses cached MP3 if updated within the last 12 hours.
    """
    settings.SUMMARY_MP3_PATH.parent.mkdir(parents=True, exist_ok=True)

    # 12-Hour Cache Check
    if settings.SUMMARY_MP3_PATH.exists() and settings.SUMMARY_MP3_PATH.stat().st_size > 5000:
        try:
            mtime = settings.SUMMARY_MP3_PATH.stat().st_mtime
            if time.time() - mtime < 43200:
                logger.info("Using cached daily audio summary.")
                return
        except Exception as e:
            logger.warning("Audio summary cache check notice: %s", e)

    if not articles:
        return

    top_articles = articles[:4]
    broadcast_items = []
    for idx, a in enumerate(top_articles, 1):
        t = getattr(a, 'title', '') or ''
        d = getattr(a, 'description', '') or ''
        clean_t = t.rstrip('.').strip()
        clean_d = d.strip()
        broadcast_items.append(f"Report {idx}: {clean_t}. {clean_d}")

    summary_text = (
        "Global Humanitarian Crisis Intelligence Broadcast. "
        "Here are today's critical emergency developments from frontline monitors: "
        + " ".join(broadcast_items)
        + " Stay informed. Support verified frontline aid corridors at Crisis Aid."
    )

    clean_text = clean_summary_text(summary_text)

    def _synthesize():
        try:
            tts = gTTS(text=clean_text, lang="en")
            tts.save(str(settings.SUMMARY_MP3_PATH))
            settings.SUMMARY_TIMESTAMP_PATH.write_text(str(time.time()))
            logger.info("Successfully synthesized daily audio summary broadcast.")
        except Exception as e:
            logger.error("Error generating daily audio summary: %s", e)

    await asyncio.to_thread(_synthesize)
