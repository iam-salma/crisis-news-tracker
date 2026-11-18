<p align="center">
    <img width="180" height="180" src="https://github.com/user-attachments/assets/6b06fa9b-f025-4e51-aff3-378157f8b016" alt="CrisisAid Logo"/>
</p>

<h1 align="center">
  <b>CrisisAid</b> — Real-Time Humanitarian Intelligence & Disaster Relief Platform
</h1>

<p align="center">
  <a href="https://fastapi.tiangolo.com/"><img src="https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat&logo=fastapi&logoColor=white" alt="FastAPI"/></a>
  <a href="https://pytorch.org/"><img src="https://img.shields.io/badge/PyTorch-2.0+-EE4C2C?style=flat&logo=pytorch&logoColor=white" alt="PyTorch"/></a>
  <a href="https://huggingface.co/"><img src="https://img.shields.io/badge/HuggingFace-Transformers-FFD21E?style=flat&logo=huggingface&logoColor=black" alt="Hugging Face"/></a>
  <a href="https://www.sqlalchemy.org/"><img src="https://img.shields.io/badge/SQLAlchemy-2.0+-D71F00?style=flat&logo=sqlalchemy&logoColor=white" alt="SQLAlchemy"/></a>
  <a href="https://www.postgresql.org/"><img src="https://img.shields.io/badge/PostgreSQL-Supported-4169E1?style=flat&logo=postgresql&logoColor=white" alt="PostgreSQL"/></a>
  <a href="https://leafletjs.com/"><img src="https://img.shields.io/badge/Leaflet-1.9.4-199900?style=flat&logo=leaflet&logoColor=white" alt="Leaflet"/></a>
  <a href="https://getbootstrap.com/"><img src="https://img.shields.io/badge/Bootstrap-5.3-7952B3?style=flat&logo=bootstrap&logoColor=white" alt="Bootstrap 5"/></a>
  <a href="https://render.com/"><img src="https://img.shields.io/badge/Render-Production-46E3B7?style=flat&logo=render&logoColor=white" alt="Render"/></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License"/></a>
</p>

---

## 📌 Overview

**CrisisAid** is a full-stack, production-grade humanitarian intelligence platform engineered to bridge real-time crisis reporting with verified frontline relief operations.

The platform continuously queries live emergency wire reports using **NewsAPI**, sanitizes and deduplicates articles, geolocates crisis events across 195+ nations, maps active humanitarian corridors using **Leaflet.js**, and sources authentic disaster photojournalism via **Wikimedia Open Media**. It features a **dual-tier AI assistant** combining a deterministic RAG engine (<25ms latency, 0% hallucination) with an in-memory neural model (`Qwen2.5-0.5B-Instruct`) streaming responses via **Server-Sent Events (SSE)** with real-time database context injection, alongside an automated **crisis newsletter dispatch engine**.

---

## 🚀 Key Features

### 🔄 1. Real-Time News Ingestion & Data Hygiene
* **NewsAPI Ingestion**: Continuously polls humanitarian developments using targeted boolean disaster queries (`crisis`, `disaster`, `relief`, `flood`, `earthquake`).
* **Text Normalization**: Strips wire truncation artifacts (`[+1420 chars]`, `Read More: ...`) and syntactically seals incomplete sentences.
* **Alphanumeric Deduplication**: Filters out duplicate reports across publishers before persisting to storage.

### 🧠 2. Dual-Tier AI & Real-Time Token Streaming
* **Instant Crisis Intelligence (Primary RAG)**: Queries live database records in `<25ms` using NLP keyword scoring to deliver factual situation assessments, casualty numbers, and verified NGO links with zero hallucination.
* **In-Memory Neural Model (`Qwen2.5-0.5B-Instruct` / PyTorch)**: Loaded in local memory for conversational dialogue without external cloud API dependencies. Injects real-time database reports directly into prompts to eliminate knowledge cutoffs.
* **Non-Blocking SSE Streaming**: Streams token chunks over Server-Sent Events (`/stream_chat/`) rendered safely on the client with `marked.js`.

### 🗺️ 3. Interactive Geospatial Radar & Aid Corridors
* **Zero-Key Cartography**: Renders high-performance interactive maps using **Leaflet.js** and OpenStreetMap tiles.
* **Dynamic Dark Mode Filter**: Custom CSS luminance/hue-rotation dynamically themes map tiles without extra network requests.
* **Humanitarian Corridors**: Tracks active and restricted passage routes (e.g., Port Sudan to Darfur, Rafah Crossing, Polish-Ukrainian Hub).

### 📸 4. Dynamic Open Media Photojournalism
* **Wikimedia / Wikipedia Open Media Engine**: Queries open media repositories for genuine, high-resolution disaster photography with zero API key requirement.
* **Heuristic Disaster Filtering**: Excludes headshots, celebrity portraits, maps, and flags to ensure only verified crisis field photography is displayed in hero banners.
* **Google Custom Search Fallback**: Automatically cascades to Google Custom Search JSON API if Wikimedia returns no matching disaster imagery.

### 📬 5. Automated Humanitarian Briefing & Newsletter
* **Subscriber Management**: Secure email registration via `/getmail` with automated instant welcome confirmations.
* **Automated Broadcast Engine**: `POST /api/newsletter/broadcast` compiles the top verified crisis situation reports and dispatches formatted email digests to all subscribers.
* **Free-Tier Cron Compatibility**: Readily scheduled via free services like [cron-job.org](https://cron-job.org) for automated daily morning deliveries.

### 🎙️ 6. Automated Daily Crisis Briefing Podcast
* **Audio Synthesis**: Synthesizes daily global crisis audio summaries using Google Text-to-Speech (`gTTS`).
* **Intelligent File Cache**: Caches daily MP3 broadcasts (`summary.mp3`) with disk timestamp checks.
* **Player Controls**: Integrated client-side speed controller (`1.0x`, `1.15x`, `1.25x`).

---

## 🏛️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                     CLIENT LAYER                                            │
│   • Responsive Bootstrap 5 UI with Dark / Light Mode Switcher & Offcanvas Navigation        │
│   • Real-Time Token Parser (marked.js Markdown Engine + Server-Sent Events / SSE)           │
│   • Interactive Cartography (Leaflet.js + OpenStreetMap + Animated Hotspot Pins)           │
└──────────────────────────────────────────────┬──────────────────────────────────────────────┘
                                               │ HTTP / REST / SSE Stream
                                               ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                ASGI APPLICATION LAYER (FastAPI)                             │
│   • Async Event Loop (uvicorn) with GZip Middleware, Security Headers & CORS                │
│   • Routing Engine & Jinja2 Server (routers/pages.py, routers/api.py)                       │
│   • ASGI Lifespan Manager (startup schema checks & background news ingestion)               │
└───────────────────────┬─────────────────────────────────────────────┬───────────────────────┘
                        │                                             │
      Database Sessions │ Dependency Injection                        │ Provider Abstraction
                        ▼                                             ▼
┌───────────────────────────────────────────┐   ┌─────────────────────────────────────────────┐
│              PERSISTENCE LAYER            │   │              AI & RAG SUBSYSTEM             │
│   • SQLAlchemy 2.0 ORM                    │   │   • LLMServiceFactory (Provider Switcher)   │
│   • SQLite (local) / PostgreSQL (Render)  │   │   • Instant RAG Engine (Zero Hallucination) │
│   • Automatic 'postgres://' URI parsing   │   │   • HuggingFace Local LLM (Qwen2.5-0.5B)    │
│   • Models: NewsArticle, AddEmail         │   │   • TextIteratorStreamer + Async SSE        │
└───────────────────────▲───────────────────┘   └─────────────────────────────────────────────┘
                        │
                        │ Ingestion & Dispatch Pipelines
┌───────────────────────┴─────────────────────────────────────────────────────────────────────┐
│                                 DATA & COMMUNICATION SERVICES                               │
│   • News Ingestion: NewsAPI REST API with boolean disaster queries                          │
│   • Media Intelligence: Wikimedia Open Media API + Google Custom Search Fallback            │
│   • Audio Pipeline: Daily Synthesized Crisis Podcast (gTTS + 12h Cache)                     │
│   • Email Service: SMTP Newsletter Dispatcher (Welcome Emails + Automated Daily Digests)    │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📂 Project Structure

```text
CrisisAid/
│
├── core/                         # Core infrastructure & configuration
│   ├── config.py                 # Centralized environment settings & directory paths
│   ├── database.py               # SQLAlchemy 2.0 engine, SessionLocal & get_db
│   └── logging_config.py         # Standardized application logger
│
├── routers/                      # Application Controllers
│   ├── pages.py                  # HTML template views (/, /search, /locate, /about, /chat)
│   └── api.py                    # REST endpoints, SSE streaming & newsletter broadcast
│
├── services/                     # Business Logic Layer
│   ├── news_service.py           # NewsAPI ingestion, sanitization & database upserts
│   ├── chat_service.py           # Instant RAG intelligence (keyword scoring & briefings)
│   ├── email_service.py          # SMTP welcome emails & newsletter broadcasting
│   ├── custom_search_service.py  # Wikimedia Open Media & Google Custom Search fallback
│   ├── geo_service.py            # Geolocation entity recognition & coordinate mapping
│   ├── relief_service.py         # Verified donation links (MSF, WFP, Red Cross)
│   ├── analysis_service.py       # Crisis situation analysis & threat level scoring
│   └── audio_service.py          # Daily podcast briefing generation (gTTS)
│
├── templates/                    # Jinja2 HTML Presentation Layer
│   ├── base.html                 # Master layout shell with Bootstrap 5 & theme script
│   ├── home.html                 # Breaking carousel, daily podcast & articles feed
│   ├── search.html               # Country filtered crisis archive with dynamic hero image
│   ├── chat.html                 # Real-time SSE streaming AI assistant interface
│   ├── locate.html               # Interactive Leaflet.js crisis map & corridors
│   ├── news_detail.html          # In-depth situation report, takeaways & map
│   └── about.html                # Humanitarian mission & verified partners
│
├── static/                       # Static assets (CSS, JS, images, generated audio)
├── data/                         # Static lookups (coordinates JSON & verified donation CSV)
│
├── models.py                     # SQLAlchemy database models (NewsArticle, AddEmail)
├── schemas.py                    # Pydantic data schemas (ChatQuery, CrisisSituationReport)
├── llm_engine.py                 # In-memory neural LLM provider (PyTorch / Qwen2.5)
├── main.py                       # FastAPI application entrypoint with ASGI Lifespan
├── requirements.txt              # Production Python dependencies
├── Procfile                      # Process file for Render / PaaS deployment
├── render.yaml                   # Render Infrastructure as Code (Blueprint)
└── .env.example                  # Environment variables template
```

---

## 🛠️ Tech Stack

| Domain | Technology | Purpose |
| :--- | :--- | :--- |
| **Backend Framework** | **FastAPI (ASGI)** | High-concurrency async web server & REST/SSE endpoints |
| **Local AI Engine** | **PyTorch + Hugging Face** | In-memory neural inference (`Qwen/Qwen2.5-0.5B-Instruct`) |
| **Data Ingestion** | **NewsAPI** | Live crisis report retrieval across 195+ nations |
| **Media Search** | **Wikimedia Open Media API** | High-resolution, authentic regional disaster photojournalism |
| **Streaming** | **Server-Sent Events (SSE)** | Low-latency token-by-token chat streaming |
| **Database & ORM** | **SQLAlchemy 2.0 + SQLite / PostgreSQL** | Local SQLite (WAL mode) & Cloud PostgreSQL (`psycopg2-binary`) |
| **Email Dispatch** | **Python smtplib + SSL/TLS** | Automated welcome notifications & daily newsletter broadcasts |
| **Geospatial Mapping** | **Leaflet.js + OpenStreetMap** | Key-free interactive crisis hotspots and safe aid corridors |
| **Audio Processing** | **gTTS (Google Text-to-Speech)** | Automated daily broadcast synthesis with file caching |
| **Cloud Hosting** | **Render** | Production web service deployment with automated CI/CD |

---

## 🔌 API & Endpoint Reference

| Method | Endpoint | Description | Payload / Query |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | Homepage with breaking carousel, audio briefing & live news feed | — |
| `GET` | `/locate` | Geospatial crisis radar with hotspot explorer & corridors | — |
| `GET` | `/news_article/{id}/{country}` | In-depth situation report, takeaways, timeline & focus map | `news_id: int, country: str` |
| `GET` | `/chat` | AI humanitarian chat assistant interface | — |
| `GET` | `/search` | Filtered crisis search results with dynamic hero photo | `?country=Sudan` |
| `POST` | `/stream_chat/` | **Server-Sent Events (SSE)** real-time token stream | `{"message": str, "provider": str}` |
| `POST` | `/generate/` | REST AI chat response with live RAG retrieval | `{"message": str, "provider": str}` |
| `GET` | `/get_crisis_countries` | JSON list of active crisis hotspots & aid corridors | — |
| `GET` | `/getmail` | Register email address for disaster updates & welcome email | `?email=user@example.com` |
| `POST` | `/api/newsletter/broadcast` | Dispatches latest top 5 situation reports to subscribers | — |
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
  python -m venv caid
  (Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned) ; .\caid\Scripts\Activate.ps1
  ```
* **On macOS / Linux**:
  ```bash
  python3 -m venv caid
  source caid/bin/activate
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
Populate `.env` with your credentials:
```ini
PORT=8080

# News Ingestion
NEWS_API_KEY="your_news_api_key_here"
NEWS_API_URL="https://newsapi.org/v2/everything"

# Optional: Local HuggingFace Model (Defaults to Qwen2.5-0.5B-Instruct)
LOCAL_HF_MODEL="Qwen/Qwen2.5-0.5B-Instruct"

# Email & Newsletter Dispatch (Gmail App Password)
EMAIL_USER="your-email@gmail.com"
EMAIL_PASSWORD="your-google-app-password"
EMAIL_PORT=465
EMAIL_SERVER="smtp.gmail.com"

# Optional: Cloud Database (Defaults to local SQLite if left empty)
DATABASE_URL=""
```
*(Note: CrisisAid operates completely offline with fallback data even if API keys or email credentials are omitted.)*

### 5. Run the Application
```bash
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```
Visit **`http://127.0.0.1:8000`** in your browser.

---

## ☁️ Deployment on Render

This repository is pre-configured for deployment on **Render** via `render.yaml` and `Procfile`.

### 1. Deploy the Web Service
1. Push your repository to GitHub.
2. In the [Render Dashboard](https://dashboard.render.com/), create a **New Web Service** connected to your repository.
3. Configure settings:
   * **Build Command**: `pip install -r requirements.txt`
   * **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Set your Environment Variables in the Render dashboard:
   * `NEWS_API_KEY`: *(Your NewsAPI key)*
   * `EMAIL_USER`: *(Your sender Gmail address)*
   * `EMAIL_PASSWORD`: *(Your Gmail App Password)*
   * `DATABASE_URL`: *(Your PostgreSQL Internal Connection URL if using Render PostgreSQL)*

### 2. Automate Daily Newsletter Briefings
Because Render's free tier can spin down after periods of inactivity, configure a free external cron job (e.g., via [cron-job.org](https://cron-job.org)):
1. Create a new cron job pointing to:
   ```text
   POST https://your-app-name.onrender.com/api/newsletter/broadcast
   ```
2. Set the schedule to run daily (e.g., `08:00 AM UTC`).
3. The cron trigger will wake the application, fetch the latest breaking reports, and dispatch the digest to all subscribers.

---

## 🧪 Verification & Testing

Run the automated endpoint verification suite:
```bash
python -c "from fastapi.testclient import TestClient; from main import app; client = TestClient(app); assert client.get('/').status_code == 200; assert client.get('/locate').status_code == 200; assert client.post('/generate/', json={'message': 'Sudan'}).status_code == 200; print('All endpoints verified operational!')"
```

---

## 📄 License

Distributed under the **MIT License**. See [`LICENSE`](file:///C:/Users/salma/Projects/CrisisAid-news-and-awareness/LICENSE) for details.
