# Stock Insights Assistant

AI-powered stock analysis application built with FastAPI, Finnhub, and OpenAI.

Ask natural language questions about stocks, ETFs, crypto, forex, and international markets — and get intelligent, data-backed summaries powered by real-time financial data and GPT-4o-mini.

---

## Features

- Natural language stock queries with typo tolerance and fuzzy matching
- Real-time quotes via Finnhub (US stocks, ETFs, indices, crypto, forex, international)
- Historical price data and trend analysis (week, month, 3M, 6M, YTD, YoY, 52-week)
- Multi-stock comparison support
- "Did you mean...?" suggestions for ambiguous or misspelled tickers
- Sidebar with randomised example questions
- FastAPI backend with modular, layered architecture
- Streamlit chat-style frontend
- Async HTTP with `httpx`, structured schemas with Pydantic
- Graceful error handling throughout

---

## Example Queries

| Query | What it does |
|---|---|
| "How is Apple doing today?" | Real-time quote + company profile |
| "Compare Tesla and Ford" | Side-by-side stats |
| "How has NVDA performed this year?" | 365-day historical candles |
| "What's EUR/USD at?" | Forex via OANDA feed |
| "How is Bitcoin doing?" | Crypto via Binance feed |
| "How is Vodafone performing?" | UK stock via LSE feed |
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
│   ├── api/           # Route handlers (thin — HTTP transport only)
│   ├── services/      # Business logic + external API clients
│   │   ├── finnhub.py   # Finnhub client + symbol normaliser
│   │   ├── openai.py    # Ticker extraction + summary generation
│   │   └── insight.py   # Orchestration layer
│   ├── models/        # Pydantic schemas
│   ├── utils/         # Custom exceptions
│   ├── config.py      # Environment variable loading
│   └── main.py        # FastAPI entry point
├── tests/             # Unit tests (mocked API clients)
├── Dockerfile
└── requirements.txt

frontend/
├── app.py             # Streamlit chat UI with sidebar
├── Dockerfile
└── requirements.txt

docker-compose.yml
.env.example
```

---

## Prerequisites

- Python 3.11+
- Docker + Docker Compose (recommended)
- Finnhub API key — [finnhub.io](https://finnhub.io)
- OpenAI API key — [platform.openai.com](https://platform.openai.com)

---

## Environment Variables

```bash
cp .env.example .env
```

```env
FINNHUB_API_KEY=your_finnhub_key
OPENAI_API_KEY=your_openai_key
```

---

## Running the App

### With Docker (recommended)

```bash
# First time or after any code changes
docker compose up --build

# Subsequent runs
docker compose up
```

| Service | URL |
|---|---|
| Streamlit UI | http://localhost:8501 |
| Backend API | http://localhost:8000 |
| Swagger docs | http://localhost:8000/docs |

> **Tip:** To rebuild only the backend: `docker compose up --build backend`

### Without Docker

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt

# Terminal 1 — backend
cd backend && uvicorn app.main:app --reload

# Terminal 2 — frontend
cd frontend && streamlit run app.py
```

---

## Running Tests

```bash
# Locally
cd backend && pytest

# In Docker
docker compose run --rm backend pytest
```

Tests use mocked API clients — no real API keys required.

---

## Architecture

The backend follows a strict layered architecture. Each layer has a single responsibility and is independently testable.

```
User question
     │
     ▼
 FastAPI Route          ← HTTP transport only, no logic
     │
     ▼
 StockInsightService    ← Orchestration: coordinates all steps
     ├── OpenAIService.extract_tickers()     ← NLP: question → ticker list
     ├── FinnhubService.get_quote()          ← Real-time price data
     ├── FinnhubService.get_company_profile()← Company metadata
     ├── FinnhubService.get_candles()        ← Historical OHLC (if period detected)
     └── OpenAIService.generate_summary()    ← LLM summary from structured data
```

**Symbol normalisation** happens in `FinnhubService.normalise_symbol()` before any API call. US tickers pass through unchanged; crypto becomes `BINANCE:<TICKER>USDT`; forex becomes `OANDA:<BASE>_<QUOTE>`; international stocks get their exchange prefix (e.g. `LSE:VOD`).

**Ticker extraction** uses a dedicated GPT-4o-mini call with a structured prompt that handles company names, typos, slang, case variations, and multiple asset classes before the main summary call.

---

## Trade-offs & Decisions

**Two-call OpenAI approach** — Ticker extraction and summary generation are separate API calls. This keeps each prompt focused and makes the extraction step independently testable. The cost trade-off (two calls vs one) is acceptable given the improved reliability and clarity of intent.

**Symbol normaliser over a database** — Rather than maintaining a ticker lookup database, asset class routing (crypto, forex, international) is handled by in-memory lookup tables in `finnhub.py`. This is fast and zero-dependency, though it requires manual updates for new markets.

**Candle data is supplementary** — Historical candle failures are silently skipped (`_fetch_candles` never raises). The insight can always be generated from the real-time quote alone, so a Finnhub candle API failure doesn't break the user's query.

**Streamlit for the frontend** — Chosen for rapid development. The trade-off is limited UI customisation (e.g. sidebar button behaviour requires `st.rerun()` workarounds) compared to a React frontend.

---

## What I'd Improve With More Time

- **Charts** — render a price chart in the UI using the candle data already being fetched
- **Streaming responses** — stream the OpenAI summary token-by-token for a better UX
- **Caching** — cache quotes for 15–30 seconds to avoid redundant Finnhub calls on repeated queries
- **More historical resolutions** — weekly/monthly candles for multi-year views
- **Portfolio mode** — allow users to track a watchlist across sessions
- **Better international coverage** — expand the exchange prefix table or integrate a ticker search API

---

## AI Tools Used

**GitHub Copilot / Claude** was used throughout development to:
- Scaffold the initial FastAPI and Streamlit boilerplate
- Draft and iterate on the OpenAI system prompts (ticker extraction and summary formatting)
- Debug Docker networking issues and Finnhub symbol format edge cases
- Suggest the two-call OpenAI architecture and the `normalise_symbol` abstraction
- Write and refine this README

All generated code was reviewed, tested, and adapted to fit the project's architecture and requirements.
