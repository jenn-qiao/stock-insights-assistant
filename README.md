# Stock Insights Assistant

Ask natural language questions about US stocks and ETFs — and get AI-powered, data-backed summaries in plain English.

Built with FastAPI, Streamlit, Finnhub, and OpenAI.

---

## Features

- Real-time quotes — US stocks, ETFs, and indices
- Historical trend analysis — week, month, year
- P/E ratio and company profile data
- Multi-stock comparisons
- Top gainers and losers by sector — tech, finance, healthcare, energy, retail, consumer, crypto
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

The backend follows a layered architecture. The API layer handles HTTP routing only and delegates all logic to the service layer. `StockInsightService` orchestrates each request — extracting tickers via OpenAI, fetching market data from Finnhub, and generating a plain-English summary. The Finnhub and OpenAI clients are separate services injected at startup, which makes them easy to mock in tests.

The frontend is a single Streamlit file that sends questions to the backend and renders the response as a chat message. It has no direct knowledge of Finnhub or OpenAI — all data fetching and AI logic lives in the backend.

Each layer has one clear responsibility, which makes the codebase easy to follow and extend. Adding a new data source means touching only the service layer. Swapping the frontend wouldn't require any changes to the backend. Tests can run against the service layer directly using mocked clients, without needing real API keys or a running server.

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

### Quick start

```bash
git clone https://github.com/jenn-qiao/jenniferq-stock-insights-assistant.git
cd jenniferq-stock-insights-assistant
cp .env.example .env
# Fill in FINNHUB_API_KEY and OPENAI_API_KEY in .env
docker compose up --build
```

## Access the Application

- Frontend (Streamlit): http://localhost:8501
- Backend API Docs (FastAPI Swagger): http://localhost:8000/docs

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

## Troubleshooting

If ports are already in use, stop existing Docker containers:

```bash
docker compose down
```

Or update the port mappings in `docker-compose.yml`.

Example:

```yaml
ports:
  - "8502:8501"
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

**Two-call OpenAI approach** — Ticker extraction and summary generation are separate OpenAI calls. This keeps prompts focused and makes ticker extraction independently testable. The trade-off is an additional LLM request per query.

**Keeping the architecture simple** — I separated the application into a frontend, API layer, and service layer to keep responsibilities clear and make testing easier. For the scope of this project, I avoided introducing additional complexity such as databases, message queues, or caching layers.

**Using OpenAI for interpretation, not market data** — OpenAI is used to understand the user's question and summarise the results, while all stock data comes directly from Finnhub. This helps reduce the risk of the model inventing financial information and keeps responses grounded in real market data.

**Streamlit over a custom frontend** — I chose Streamlit because it allowed me to focus on the backend architecture and AI workflow rather than spending time building a frontend from scratch. The trade-off is less flexibility in the user interface.

**Favouring reliability over completeness** — If some non-essential data cannot be retrieved (for example historical candle data), the application still returns a useful response rather than failing completely. This provides a better user experience, although some context may be missing.

**Focusing on US-listed stocks and ETFs** — To keep the scope manageable, I focused on US-listed securities. Supporting multiple exchanges and regions would require additional symbol resolution and market-specific handling.

---

## What I'd Improve With More Time

- **Interactive charts & technical indicators** — Render historical price charts using the candle data already being fetched and add indicators such as moving averages, RSI, and trend analysis.
- **News & sentiment analysis** — Incorporate recent company news, earnings coverage, and sentiment signals to provide richer context beyond market data alone.
- **Portfolio & watchlist support** — Allow users to save favourite stocks, build watchlists, and track portfolio performance across sessions.
- **Streaming responses** — Stream OpenAI responses token-by-token for a more responsive conversational experience.
- **Caching & rate limiting** — Introduce in-memory or Redis-based caching to reduce duplicate API requests, improve latency, and better manage third-party API limits.
- **Authentication & persistence** — Add user authentication and persistent storage for saved portfolios, preferences, and query history.
- **Improved observability** — Implement structured logging, metrics, health checks, and tracing to improve monitoring and debugging in production environments.
- **Scalability improvements** — Move slower enrichment tasks, such as sentiment analysis and news aggregation, into background workers and introduce API throttling and queueing mechanisms for higher-volume workloads.
- **Richer frontend experience** — Replace Streamlit with a React/Next.js frontend to support richer visualisations, more advanced interactions, and greater UI flexibility.

---

## AI Tools Used

I used ChatGPT and Claude throughout the project as development assistants.

ChatGPT was most helpful for discussing architecture decisions, Docker setup, CI/CD, testing approaches, and general software engineering questions.
Claude was most helpful when iterating on implementation details, debugging issues, refining prompts, and reviewing code structure.

Both tools helped speed up development and explore alternative approaches, but all code, design decisions, testing, and final implementation choices were reviewed and validated by me.
