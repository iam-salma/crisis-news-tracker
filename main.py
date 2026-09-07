import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from core.config import settings
from core.database import Base, engine
from core.logging_config import logger
from routers import pages_router, api_router
from services.news_service import insert_news_in_db

# Create SQLite tables on module import if not present
Base.metadata.create_all(bind=engine)
templates = Jinja2Templates(directory=str(settings.TEMPLATES_DIR))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Modern ASGI Lifespan Context Manager.
    Handles startup database validation and graceful shutdown.
    """
    logger.info("Initializing %s v%s...", settings.PROJECT_NAME, settings.PROJECT_VERSION)
    settings.INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Startup ETL check (run in background)
    asyncio.create_task(insert_news_in_db())
    
    yield
    
    logger.info("Shutting down %s gracefully.", settings.PROJECT_NAME)


# FastAPI Application Instance
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.PROJECT_VERSION,
    lifespan=lifespan
)

# 1. Performance Middleware: GZip Compression (> 500 bytes)
app.add_middleware(GZipMiddleware, minimum_size=500)

# 2. Security Middleware: Cross-Origin Resource Sharing (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. HTTP Security Headers Middleware (OWASP Defense)
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    return response

# Mount Static Assets
app.mount("/static", StaticFiles(directory=str(settings.STATIC_DIR)), name="static")

# Mount Application Routers
app.include_router(pages_router)
app.include_router(api_router)


# Global Exception Handlers
@app.exception_handler(404)
async def custom_404_handler(request: Request, exc: HTTPException):
    """Clean custom 404 response handler."""
    if request.url.path.startswith(("/generate", "/stream_chat", "/get_crisis_countries")):
        return JSONResponse(status_code=404, content={"error": "Resource not found"})
    return templates.TemplateResponse(
        "search.html",
        {"request": request, "all_articles": [], "country": "Page Not Found"},
        status_code=404
    )


@app.exception_handler(500)
async def custom_500_handler(request: Request, exc: Exception):
    """Global unhandled exception handler."""
    logger.error("Unhandled Exception on %s: %s", request.url.path, exc)
    if request.url.path.startswith(("/generate", "/stream_chat", "/get_crisis_countries")):
        return JSONResponse(status_code=500, content={"error": "Internal Server Error"})
    return HTMLResponse(
        content="<h2 style='font-family:sans-serif; text-align:center; margin-top:20vh;'>An unexpected server error occurred. Please refresh or return to <a href='/'>Home</a>.</h2>",
        status_code=500
    )


if __name__ == "__main__":
    import os
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
