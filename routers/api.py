import re
import json
import asyncio
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
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
from services.chat_service import generate_ai_chat_response

router = APIRouter(tags=["API"])


@router.post("/generate/", summary="REST AI Chat Intelligence")
async def generate_chat(data: ChatQuery, db: Session = Depends(get_db)):
    """Non-streaming AI chat query execution with local heuristic & LLM fallback."""
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
            logger.warning("[Local HF] REST error: %s. Using RAG Engine.", e)

    bot_reply = await generate_ai_chat_response(user_message, db=db)
    return {"response": bot_reply, "provider": "CrisisAid Local Intelligence Engine"}


@router.post("/stream_chat/", summary="Server-Sent Events (SSE) AI Chat Streaming")
async def stream_chat(data: ChatQuery, db: Session = Depends(get_db)):
    """Streams real-time token chunks over Server-Sent Events (SSE)."""
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
                logger.warning("[Local HF Stream] notice: %s. Cascading to RAG Engine.", e)

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


@router.get("/get_crisis_countries", summary="Active Crisis Geo Hotspots")
async def get_crisis_countries(db: Session = Depends(get_db)):
    """Retrieves all active crisis hotspots with geolocation and urgency metadata."""
    try:
        articles = db.query(NewsArticle).all()
        crisis_countries = []
        unique_countries = set()

        for art in articles:
            geo_type, geo_name, coords, _ = detect_geo_entity(f"{art.title} {art.description or ''}")
            analysis = analyze_crisis_article(title=art.title, description=art.description, country_name=geo_name)

            continent = "Global"
            for reg_key, reg_info in CONTINENTS_REGIONS.items():
                if geo_name.lower() in reg_info["countries"] or geo_name.lower() == reg_key:
                    continent = reg_info["name"]
                    break

            donate_url = donation_links.get(geo_name, art.link or "https://www.redcross.org/donate/donation.html/")
            unique_countries.add(geo_name)

            crisis_countries.append({
                "id": art.id,
                "country": geo_name,
                "continent": continent,
                "title": art.title,
                "description": art.description or "Active humanitarian response underway.",
                "image": art.urlToImage or "/static/assets/images/hero-active.jpg",
                "publishedAt": art.publishedAt,
                "lat": coords[0],
                "lng": coords[1],
                "urgency": analysis["urgency"],
                "crisis_type": analysis["crisis_type"],
                "immediate_needs": analysis["immediate_needs"],
                "donate_url": donate_url,
                "briefing_url": f"/news_article/{art.id}/{geo_name}"
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


@router.get("/getmail", summary="Newsletter Subscription")
async def get_mail(request: Request, db: Session = Depends(get_db)):
    """Registers user email for crisis briefings."""
    email = request.query_params.get("email", "").strip()
    if not email:
        return RedirectResponse(url="/", status_code=303)

    try:
        existing = db.query(AddEmail).filter_by(email=email).first()
        if not existing:
            new_sub = AddEmail(email=email)
            db.add(new_sub)
            db.commit()
    except Exception as e:
        db.rollback()
        logger.warning("Newsletter registration notice: %s", e)

    return RedirectResponse(url="/?subscribed=true", status_code=303)


def send_contact_email(name: str, email: str, message: str) -> None:
    """Dispatches contact form submission via SMTP."""
    if not settings.EMAIL_USER or not settings.EMAIL_PASSWORD:
        return

    try:
        msg = MIMEMultipart()
        msg['From'] = settings.EMAIL_USER
        msg['To'] = settings.EMAIL_USER
        msg['Subject'] = f"CrisisAid Contact Form Submission from {name}"
        body = f"Sender Name: {name}\nSender Email: {email}\n\nMessage:\n{message}"
        msg.attach(MIMEText(body, 'plain'))

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(settings.EMAIL_SERVER, settings.EMAIL_PORT, context=context) as server:
            server.login(settings.EMAIL_USER, settings.EMAIL_PASSWORD)
            server.sendmail(settings.EMAIL_USER, settings.EMAIL_USER, msg.as_string())
        logger.info("Successfully sent contact email from %s", email)
    except Exception as e:
        logger.error("Failed to send contact email: %s", e)


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
