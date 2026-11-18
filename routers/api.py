import re
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List

from fastapi import APIRouter, Depends, Request, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse, RedirectResponse
from sqlalchemy.orm import Session

from core.config import settings
from core.database import get_db
from core.logging_config import logger
from models import NewsArticle, AddEmail
from schemas import ChatQuery
from llm_engine import LLMServiceFactory
from services.geo_service import detect_geo_entity, CONTINENTS_REGIONS
from services.relief_service import donation_links, HUMANITARIAN_CORRIDORS
from services.analysis_service import analyze_crisis_article
from services.chat_service import generate_ai_chat_response, get_rag_context_for_query
from services.email_service import (
    send_welcome_newsletter_email,
    send_contact_email,
    broadcast_crisis_newsletter
)

router = APIRouter(tags=["API"])


@router.post("/generate/", summary="REST AI Chat Intelligence")
async def generate_chat(data: ChatQuery, db: Session = Depends(get_db)):
    """Non-streaming AI chat query execution with live RAG retrieval & LLM fallback."""
    user_message = data.message.strip()
    if not user_message:
        return {"response": "Please type a message so I can assist you.", "provider": "CrisisAid Local Engine"}

    selected_provider = data.provider or "local_rule"

    if selected_provider == "local_hf":
        try:
            rag_context = get_rag_context_for_query(user_message, db)
            system_prompt = (
                f"You are CrisisAid AI, an expert real-time humanitarian intelligence system. "
                f"Current system date is {datetime.now().strftime('%d %B %Y')}. "
                f"Use the following real-time crisis intelligence reports from our live database to answer the user accurately. "
                f"Focus on current frontline developments, casualties, civilian displacement, and relief efforts. "
                f"Do NOT say your knowledge cuts off in 2023 because you are provided with live real-time reports below.\n\n"
                f"--- LIVE HUMANITARIAN DATABASE REPORTS ---\n{rag_context}\n--- END REPORTS ---"
            )
            bot_reply, provider_name = await LLMServiceFactory.generate_with_fallback(
                prompt=user_message,
                system_prompt=system_prompt,
                preferred="local_hf"
            )
            return {"response": bot_reply, "provider": provider_name}
        except Exception as e:
            logger.warning("Local HF Provider invocation fallback notice: %s", e)

    # Deterministic RAG intelligence default
    reply = generate_ai_chat_response(user_message, db)
    return {"response": reply, "provider": "Deterministic Humanitarian RAG Engine"}


@router.post("/stream_chat/", summary="Streaming SSE AI Chat")
async def stream_chat(data: ChatQuery, db: Session = Depends(get_db)):
    """Server-Sent Events (SSE) token streamer for real-time AI conversation with RAG context."""
    user_message = data.message.strip()
    if not user_message:
        async def empty_stream():
            yield "data: Please type a message so I can assist you.\n\n"
        return StreamingResponse(empty_stream(), media_type="text/event-stream")

    selected_provider = data.provider or "local_rule"

    if selected_provider == "local_hf":
        try:
            rag_context = get_rag_context_for_query(user_message, db)
            system_prompt = (
                f"You are CrisisAid AI, an expert real-time humanitarian intelligence system. "
                f"Current system date is {datetime.now().strftime('%d %B %Y')}. "
                f"Use the following real-time crisis intelligence reports from our live database to answer the user accurately. "
                f"Focus on current frontline developments, casualties, civilian displacement, and relief efforts. "
                f"Do NOT say your knowledge cuts off in 2023 because you are provided with live real-time reports below.\n\n"
                f"--- LIVE HUMANITARIAN DATABASE REPORTS ---\n{rag_context}\n--- END REPORTS ---"
            )
            hf_provider = LLMServiceFactory.get_provider("local_hf")

            async def event_generator():
                async for token in hf_provider.stream_response(user_message, system_prompt):
                    yield f"data: {token}\n\n"

            return StreamingResponse(
                event_generator(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"
                }
            )
        except Exception as e:
            logger.warning("Streaming fallback to deterministic RAG: %s", e)

    # Deterministic token chunk streamer
    async def simulated_stream():
        full_reply = generate_ai_chat_response(user_message, db)
        words = full_reply.split(" ")
        for i, word in enumerate(words):
            chunk = word + (" " if i < len(words) - 1 else "")
            yield f"data: {chunk}\n\n"
            await asyncio.sleep(0.02)

    return StreamingResponse(
        simulated_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/get_crisis_countries", summary="Active Telemetry & Geospatial Hotspots")
async def get_crisis_countries(db: Session = Depends(get_db)):
    """Returns detected crisis geographic hotspots with direct donation links."""
    try:
        articles = db.query(NewsArticle).all()
        crisis_countries = []
        unique_countries = set()

        for article in articles:
            combined_text = f"{article.title} {article.description}"
            detected_country = detect_geo_entity(combined_text)

            if detected_country and detected_country not in unique_countries:
                unique_countries.add(detected_country)
                d_link = donation_links.get(detected_country.lower(), "https://www.icrc.org/en/donate")
                crisis_countries.append({
                    "country": detected_country,
                    "title": article.title,
                    "donation_link": d_link,
                    "source": getattr(article, "url", "#")
                })

        return {
            "total_hotspots": len(crisis_countries),
            "total_countries": len(unique_countries),
            "crisis_countries": crisis_countries,
            "corridors": HUMANITARIAN_CORRIDORS
        }
    except Exception as e:
        logger.error("Error retrieving crisis countries: %s", e)
        return {"total_hotspots": 0, "total_countries": 0, "crisis_countries": [], "corridors": HUMANITARIAN_CORRIDORS}


EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


@router.get("/getmail", summary="Newsletter Subscription")
async def get_mail(request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Registers user email for crisis briefings and dispatches welcome confirmation."""
    email = request.query_params.get("email", "").strip()
    if not email or not EMAIL_REGEX.match(email) or len(email) > 120:
        return RedirectResponse(url="/?invalid_email=true#target-section", status_code=303)

    try:
        existing = db.query(AddEmail).filter_by(email=email).first()
        if not existing:
            new_sub = AddEmail(email=email)
            db.add(new_sub)
            db.commit()
            # Send welcome confirmation in the background if SMTP credentials are configured
            background_tasks.add_task(send_welcome_newsletter_email, email)
            logger.info("New newsletter subscriber registered: %s", email)
    except Exception as e:
        db.rollback()
        logger.warning("Newsletter registration notice: %s", e)

    return RedirectResponse(url="/?subscribed=true#target-section", status_code=303)


@router.post("/api/newsletter/broadcast", summary="Dispatch Newsletter Broadcast")
async def dispatch_newsletter(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Admin endpoint to dispatch latest situation report digest to all subscribers."""
    try:
        subs = [row.email for row in db.query(AddEmail).all()]
        if not subs:
            return JSONResponse(status_code=200, content={"message": "No subscribers registered yet."})

        articles = [
            {"title": a.title, "description": a.description, "url": a.url}
            for a in db.query(NewsArticle).order_by(NewsArticle.id.desc()).limit(5).all()
        ]

        background_tasks.add_task(broadcast_crisis_newsletter, subs, articles)
        return {"status": "queued", "subscribers_count": len(subs), "articles_count": len(articles)}
    except Exception as e:
        logger.error("Newsletter broadcast dispatch error: %s", e)
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/contact", summary="Submit Contact Form")
async def contact_form(request: Request, background_tasks: BackgroundTasks):
    """Processes contact inquiries asynchronously."""
    try:
        form_data = await request.form()
        name = form_data.get("name", "").strip()
        email = form_data.get("email", "").strip()
        message = form_data.get("message", "").strip()

        if name and email and message:
            background_tasks.add_task(send_contact_email, name, email, message)

        return RedirectResponse(url="/about?sent=true", status_code=303)
    except Exception as e:
        logger.error("Contact form processing error: %s", e)
        return RedirectResponse(url="/about?error=true", status_code=303)
