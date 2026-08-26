<p align="center">
    <img width="180" height="180" src="https://github.com/user-attachments/assets/6b06fa9b-f025-4e51-aff3-378157f8b016" alt="CrisisAid Logo"/>
</p>

<h1 align="center">
  <b>CrisisAid</b> — Real-Time Humanitarian Intelligence & Disaster Relief Platform
</h1>

<p align="center">
  <a href="https://fastapi.tiangolo.com/"><img src="https://img.shields.io/badge/FastAPI-0.110+-009688?style=flat&logo=fastapi&logoColor=white" alt="FastAPI"/></a>
  <a href="https://pytorch.org/"><img src="https://img.shields.io/badge/PyTorch-2.0+-EE4C2C?style=flat&logo=pytorch&logoColor=white" alt="PyTorch"/></a>
  <a href="https://huggingface.co/"><img src="https://img.shields.io/badge/HuggingFace-Transformers-FFD21E?style=flat&logo=huggingface&logoColor=black" alt="Hugging Face"/></a>
  <a href="https://www.sqlalchemy.org/"><img src="https://img.shields.io/badge/SQLAlchemy-2.0+-D71F00?style=flat&logo=sqlalchemy&logoColor=white" alt="SQLAlchemy"/></a>
  <a href="https://leafletjs.com/"><img src="https://img.shields.io/badge/Leaflet-1.9.4-199900?style=flat&logo=leaflet&logoColor=white" alt="Leaflet"/></a>
  <a href="https://getbootstrap.com/"><img src="https://img.shields.io/badge/Bootstrap-5.3-7952B3?style=flat&logo=bootstrap&logoColor=white" alt="Bootstrap 5"/></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License"/></a>
</p>

---

## 📌 Overview

**CrisisAid** is an open, full-stack humanitarian intelligence platform engineered to bridge real-time crisis awareness with verified frontline disaster relief. 

The system continuously aggregates multi-source emergency reports (NewsAPI, UN OCHA RSS feeds), normalizes and geolocates crisis entities across 195+ nations, synthesizes in-depth situational assessments using **100% offline local in-memory Large Language Models (LLMs)** and **Retrieval-Augmented Generation (RAG)**, streams conversational intelligence via **Server-Sent Events (SSE)**, maps active emergency corridors with **Leaflet.js**, and directs assistance to accredited relief agencies (MSF, WFP, UNHCR, ICRC) with zero intermediary fees.

---

## 🚀 Key Features

### 🧠 1. Dual-Engine Local AI & RAG Subsystem
* **Deterministic RAG Intelligence (Primary)**: Queries live SQLite records in `<5ms` using NLP entity recognition and keyword scoring to return factual situation briefings, casualty metrics, and verified donation links with zero hallucination.
* **In-Memory Neural Model (`Qwen2.5-0.5B-Instruct` / PyTorch)**: Loaded directly in local RAM for conversational reasoning without external cloud API dependencies.
* **Non-Blocking SSE Streaming**: Generates token chunks via `TextIteratorStreamer` on a background thread while FastAPI asynchronously yields chunks over Server-Sent Events (`/stream_chat/`).
* **Safe Client Markdown Rendering**: Incremental token stream rendered via `marked.js`, preventing incomplete HTML/CSS syntax leaks.

### 🗺️ 2. Geospatial Radar & Aid Corridors
* **Zero-Key Cartography**: Standard OpenStreetMap tiles (`tile.openstreetmap.org`) eliminating rate limits and third-party API key requirements.
* **Dynamic Dark Mode Tile Inversion**: Custom CSS luminance/hue-rotation filters dynamically transform map tiles into high-contrast dark maps without extra server roundtrips.
* **Humanitarian Corridors**: Real-time visual tracking of active, monitored, and restricted aid passage routes (e.g., Port Sudan to Darfur, Rafah Crossing, Polish-Ukrainian Hub).

### 🎙️ 3. Daily Synthesized Crisis Podcast
* **Automated Audio Pipeline**: Synthesizes daily global crisis audio summaries using Google Text-to-Speech (`gTTS`).
* **12-Hour Intelligent Cache**: Automatically pre-generates and caches daily MP3 broadcasts (`summary.mp3`) with disk mtime checks.
* **Client Tempo Selector**: Integrated playback speed controller (`1.15x`, `1.25x`, `1.0x`) using HTML5 media listeners.

### 🔄 4. Multi-Source ETL Ingestion & Data Hygiene
* **Wire Feed Ingestion**: Ingests JSON from NewsAPI and parses XML RSS feeds from UN OCHA / UN News.
* **Deduplication Engine**: Alphanumeric hashing prevents duplicate wire reports across providers.
* **Incomplete Sentence Repair**: Strips trailing truncation artifacts (`[+1420 chars]`, `Read More: ...`) and syntactically seals incomplete sentences.

### 📱 5. Fluid Responsive UI & Theme Engine
* Fully responsive across mobile, tablet, and widescreen monitors with offcanvas navigation.
* Native system-aware light/dark theme toggle with persistent `localStorage` preference.

---

## 🏛️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                     CLIENT LAYER                                            │
│   • Responsive Bootstrap 5 UI (CSS Variables, Theme Switcher, CSS Tile Inversion)           │
│   • Real-Time Token Parser (marked.js Markdown Engine + EventSource / Fetch API)            │
│   • Interactive Cartography (Leaflet.js + OpenStreetMap + Custom Pulsing Pins)             │
└──────────────────────────────────────────────┬──────────────────────────────────────────────┘
                                               │ HTTP / REST / SSE Stream
                                               ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                ASGI APPLICATION LAYER (FastAPI)                             │
│   • Async Event Loop (uvicorn) with GZip Middleware & CORS                                  │
│   • Routing Engine & Jinja2 Template Server (routers/pages.py, routers/api.py)              │
│   • Lifespan Context Manager (Startup ETL & graceful resource disposal)                    │
└───────────────────────┬─────────────────────────────────────────────┬───────────────────────┘
                        │                                             │
      Database Sessions │ Dependency Injection                        │ Provider Abstraction
                        ▼                                             ▼
┌───────────────────────────────────────────┐   ┌─────────────────────────────────────────────┐
│              PERSISTENCE LAYER            │   │            LOCAL AI & RAG SUBSYSTEM         │
│   • SQLAlchemy 2.0 ORM                    │   │   • LLMServiceFactory (Factory Pattern)     │
│   • SQLite Database (instance/news.db)    │   │   • HuggingFaceLocalLLMProvider (Qwen2.5)   │
│   • Models: NewsArticle, AddEmail         │   │   • TextIteratorStreamer + Background Thread│
│   • Geo Coordinate Registry (JSON)        │   │   • Deterministic Humanitarian RAG Engine   │
└───────────────────────▲───────────────────┘   └─────────────────────────────────────────────┘
                        │
                        │ Ingestion Pipeline (ETL)
┌───────────────────────┴─────────────────────────────────────────────────────────────────────┐
│                                  DATA INGESTION & PIPELINES                                 │
│   • Multi-Source Aggregator (NewsAPI REST API + UN OCHA XML RSS Feeds)                      │
│   • Text Normalization, Deduplication & Incomplete Sentence Cleaning Regex                 │
│   • Audio Pipeline: Daily Synthesized Crisis Podcast (gTTS + 12h Cache)                     │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📂 Project Structure

```
CrisisAid/
├── core/
│   ├── config.py             # Centralized settings, environment variables & paths
│   ├── database.py           # Engine, SessionLocal & get_db Dependency Injection
│   └── logging_config.py     # Production structured logging formatter
├── models/
│   ├── __init__.py           # SQLAlchemy ORM models (NewsArticle, AddEmail)
│   └── ...
├── schemas/
│   ├── __init__.py           # Pydantic schemas (ChatQuery, CrisisSituationReport)
│   └── ...
├── services/
│   ├── news_service.py       # Multi-source ETL (NewsAPI + UN RSS) & deduplication
│   ├── geo_service.py        # NLP entity extraction, coordinate resolution & regions
│   ├── relief_service.py     # Verified donation link registry & accredited NGO corridors
│   ├── analysis_service.py   # Domain-specific crisis reports, takeaways & text cleaners
│   ├── audio_service.py      # Synthesized daily crisis broadcast (gTTS) & file caching
│   └── chat_service.py       # Deterministic RAG intelligence & query ranking engine
├── routers/
│   ├── pages.py              # HTML Views (/, /locate, /about, /chat, /search, /news_article/...)
│   └── api.py                # REST Endpoints & SSE Streaming (/generate/, /stream_chat/, ...)
├── data/
│   ├── all_countries_verified_donation_links.csv
│   └── country_coordinates.json
├── static/
│   ├── css/styles.css        # Responsive styling & CSS dark-mode tile filter
│   ├── js/script.js          # Audio controller & client utilities
│   └── assets/               # Audio summaries, icons & images
├── templates/
│   ├── base.html             # Base shell with marked.js, Bootstrap & theme setup
│   ├── index.html            # Breaking carousel, daily podcast & articles feed
│   ├── locate.html           # Interactive Leaflet crisis map & aid corridors
│   ├── chat.html             # SSE AI chat streaming interface with suggestion tags
│   ├── news_article.html     # Unified briefing: situation report, takeaways, timeline
│   ├── search.html           # Country filtered crisis archive
│   └── about.html            # Humanitarian mission & accredited partners
├── llm_engine.py             # Hugging Face Qwen2.5 / PyTorch in-memory provider
├── main.py                   # Clean application entrypoint (<90 lines) with Lifespan
├── requirements.txt          # Python dependencies
└── .env.example              # Environment variables template
```

---

## 🛠️ Tech Stack

| Domain | Technology | Purpose |
| :--- | :--- | :--- |
| **Framework** | **FastAPI (ASGI)** | High-concurrency async web server & REST/SSE endpoints |
| **Local AI Engine** | **Hugging Face `transformers` + PyTorch** | 100% offline in-memory inference (`Qwen/Qwen2.5-0.5B-Instruct`) |
| **Streaming** | **Server-Sent Events (SSE)** | Low-latency unidirectional token streaming |
| **Database & ORM** | **SQLite 3 + SQLAlchemy 2.0** | Relational storage with dependency injection |
| **ETL & Feed Ingestion** | **NewsAPI + UN OCHA XML RSS** | Multi-source humanitarian crisis report aggregation |
| **Geospatial Mapping** | **Leaflet.js + OpenStreetMap** | Key-free interactive crisis hotspots and safe aid corridors |
| **Audio Processing** | **gTTS (Google Text-to-Speech)** | Automated daily broadcast synthesis with 12-hour file caching |
| **Frontend & UX** | **Bootstrap 5.3 + marked.js** | Mobile-first responsive interface with live markdown parser |

---

## 🔌 API Reference

| Method | Endpoint | Description | Payload / Query |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | Homepage with breaking carousel, audio briefing & live news feed | — |
| `GET` | `/locate` | Geospatial crisis radar with hotspot explorer & corridors | — |
| `GET` | `/news_article/{id}/{country}` | In-depth situation report, takeaways, timeline & focus map | `news_id: int, country: str` |
| `GET` | `/chat` | AI humanitarian chat assistant interface | — |
| `GET` | `/search` | Filtered crisis search results by country | `?country=Sudan` |
| `POST` | `/stream_chat/` | **Server-Sent Events (SSE)** real-time token stream | `{"message": str, "provider": str}` |
| `POST` | `/generate/` | REST AI chat response | `{"message": str, "provider": str}` |
| `GET` | `/get_crisis_countries` | JSON list of active crisis hotspots & aid corridors | — |
| `GET` | `/getmail` | Register email address for disaster updates | `?email=user@example.com` |
| `POST` | `/contact` | Asynchronously submit inquiries via background email task | Form data (`name, email, message`) |

---

## ⚙️ Installation & Local Setup

### 1. Clone the Repository
```bash
git clone https://github.com/iam-salma/crisis-news-tracker.git
cd crisis-news-tracker
```

### 2. Create and Activate Virtual Environment
* **On Windows (PowerShell)**:
  ```powershell
  python -m venv venv
  .\venv\Scripts\Activate.ps1
  ```
* **On macOS / Linux**:
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

### 3. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Populate `.env` with your configuration:
```ini
NEWS_API_KEY="your_news_api_key_here"
NEWS_API_URL="https://newsapi.org/v2/everything"
LOCAL_HF_MODEL="Qwen/Qwen2.5-0.5B-Instruct"
EMAIL_USER=""
EMAIL_PASSWORD=""
```
*(Note: CrisisAid functions completely offline with fallback data even if API keys are omitted.)*

### 5. Run the Application
```bash
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Visit **`http://127.0.0.1:8000`** in your browser.

---

## 🧪 Verification & Testing

Run the automated endpoint verification suite:
```bash
python -c "from fastapi.testclient import TestClient; from main import app; client = TestClient(app); assert client.get('/').status_code == 200; assert client.get('/locate').status_code == 200; assert client.post('/generate/', json={'message': 'Sudan'}).status_code == 200; print('All endpoints verified operational!')"
```

## 📄 License

Distributed under the **MIT License**. See [`LICENSE`](file:///C:/Users/salma/Projects/CrisisAid-news-and-awareness/LICENSE) for details.
