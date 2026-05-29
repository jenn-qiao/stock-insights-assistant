# Stock Insights Assistant

Ask natural language questions about US stocks and ETFs — and get AI-powered, data-backed summaries in plain English.

Built with FastAPI, Streamlit, Finnhub, and OpenAI.

---

## Features

- Real-time quotes — US stocks, ETFs, and indices
- Historical trend analysis — week, month, year
- P/E ratio and company profile data
- Multi-stock comparisons
- Typo tolerance and fuzzy company name matching
- "Did you mean...?" suggestions for ambiguous tickers
- Sidebar with randomised example questions

---

## Example Queries

| Query | What it does |
|---|---|
| "How is Apple doing today?" | Real-time quote + company profile |
| "Compare Tesla and Ford" | Side-by-side stats |
| "How has NVDA performed this year?" | Historical price data |
| "What is Amazon's P/E ratio?" | Fundamental metrics |
| "appple stock" | Typo-corrected to AAPL |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python 3.11) |
| Frontend | Streamlit |
| AI | OpenAI API (gpt-4o-mini) |
| Market Data | Finnhub API |
| HTTP Client | httpx (async) |
| Validation | Pydantic v2 |
| Containerisation | Docker + Docker Compose |

---

## Project Structure

```text
backend/
├── app/
│   ├── api/           # Route handlers (HTTP transport only)
│   ├── services/
│   │   ├── finnhub.py   # Finnhub API client
│   │   ├── openai.py    # Ticker extraction + summary generation
│   │   └── insight.py   # Orchestration layer
│   ├── models/        # Pydantic schemas
│   ├── utils/         # Custom exceptions
│   ├── config.py      # Environment variable loading
│   └── main.py        # FastAPI entry point
├── tests/
├── Dockerfile
└── requirements.txt

frontend/
├── app.py             # Streamlit chat UI
├── Dockerfile
└── requirements.txt
```

---

## Setup

### Prerequisites

- Docker + Docker Compose
- Finnhub API key — [finnhub.io](https://finnhub.io)
- OpenAI API key — [platform.openai.com](https://platform.openai.com)

### Environment variables

```bash
cp .env.example .env
# Fill in FINNHUB_API_KEY and OPENAI_API_KEY
```

---

## Running the App

```bash
# First run or after code changes
docker compose up --build

# Subsequent runs
docker compose up

# Rebuild backend only
docker compose up --build backend
```

| Service | URL |
|---|---|
| Streamlit UI | http://localhost:8501 |
| Backend API | http://localhost:8000 |
| Swagger docs | http://localhost:8000/docs |

### Without Docker

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt

# Terminal 1
cd backend && uvicorn app.main:app --reload

# Terminal 2
cd frontend && streamlit run app.py
```

---

## Tests

```bash
docker compose run --rm backend pytest

# Verbose
docker compose run --rm backend pytest -v
```

Tests use mocked API clients — no real API keys required.

---

## Linting

```bash
# Check
docker compose run --rm backend ruff check app/

# Auto-fix
docker compose run --rm backend ruff check app/ --fix
```

---

## Architecture

The backend uses a layered architecture — each layer has one responsibility and is independently testable.

```
User question
     │
     ▼
 FastAPI Route              ← HTTP transport only
     │
     ▼
 StockInsightService        ← Orchestrates all steps
     ├── OpenAIService.extract_tickers()      ← question → ticker list
     ├── FinnhubService.get_quote()           ← real-time price
     ├── FinnhubService.get_company_profile() ← company metadata
     ├── FinnhubService.get_metrics()         ← P/E ratio
     ├── FinnhubService.get_candles()         ← historical data (if period detected)
     └── OpenAIService.generate_summary()     ← LLM summary from structured data
```

---

## Trade-offs & Decisions

**Two-call OpenAI approach** — Ticker extraction and summary generation are separate calls. Each prompt stays focused and the extraction step is independently testable.

**Candle failures are silent** — Historical candle errors are skipped gracefully so a data failure never blocks a user query.

**US stocks only** — The app focuses on US-listed stocks and ETFs. This keeps the codebase simple — tickers are passed directly to Finnhub without any exchange-prefix routing.

**Streamlit frontend** — Chosen for speed of development. The trade-off is limited UI control (e.g. sidebar buttons require `st.rerun()` to avoid duplicate messages) vs a React frontend.

---

## What I'd Improve With More Time

- **Charts** — render a price chart from the candle data already being fetched
- **Streaming** — stream the OpenAI summary token-by-token for snappier UX
- **Caching** — cache quotes for 15–30s to avoid duplicate Finnhub calls
- **Portfolio mode** — let users save and track a watchlist across sessions

---

## AI Tools Used

Claude was used throughout to scaffold boilerplate, iterate on OpenAI prompts, debug Docker and Finnhub edge cases, and suggest architectural patterns like the two-call approach. All output was reviewed, tested, and adapted to fit the project.
