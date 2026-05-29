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
| "What are the top gainers in tech?" | Sector scan — ranked by % change |
| "Top losers in finance today?" | Sector scan — bottom 5 by % change |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python 3.11) |
| Frontend | Streamlit |
| AI | OpenAI API (gpt-4o-mini) |
| Market Data | Finnhub API |
| HTTP Client | httpx |
| Validation | Pydantic v2 |
| Containerisation | Docker + Docker Compose |

---

## Project Structure

The backend follows a layered architecture. The API layer handles HTTP routing only and delegates all logic to the service layer. `StockInsightService` orchestrates each request — extracting tickers via OpenAI, fetching market data from Finnhub, and generating a plain-English summary. The Finnhub and OpenAI clients are separate services injected at startup, which makes them easy to mock in tests.

The frontend is a single Streamlit file that sends questions to the backend and renders the response as a chat message. It has no direct knowledge of Finnhub or OpenAI — all data fetching and AI logic lives in the backend.

Each layer has one clear responsibility, which makes the codebase easy to follow and extend. Adding a new data source means touching only the service layer. Swapping the frontend wouldn't require any changes to the backend. Tests can run against the service layer directly using mocked clients, without needing real API keys or a running server.

**Request flow:** The user types a question in the Streamlit UI, which sends it to the FastAPI backend. The API route passes it to `StockInsightService`, which first calls OpenAI to extract the ticker symbol(s) from the question. It then fetches the relevant data from Finnhub — quote, company profile, P/E ratio, and historical candles if a time period was mentioned. That data is passed back to OpenAI to generate a plain-English summary, which is returned to the frontend and displayed in the chat.

```
User asks a question
        ↓
Backend fetches stock data from Finnhub
        ↓
Backend sends question + data to OpenAI
        ↓
OpenAI generates a plain-English summary
        ↓
App displays the response
```

**Service layer detail:**

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
     ├── FinnhubService.get_pe_ratio()        ← P/E ratio
     ├── FinnhubService.get_candles()         ← historical data (if period detected)
     └── OpenAIService.generate_summary()     ← LLM summary from structured data
```

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
- Backend API: http://localhost:8000
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

## Trade-offs & Decisions

**Two-call OpenAI approach** — Ticker extraction and summary generation are separate OpenAI calls. This keeps prompts focused and makes ticker extraction independently testable. The trade-off is an additional LLM request per query.

**Keeping the architecture simple** — I separated the application into a frontend, API layer, and service layer to keep responsibilities clear and make testing easier. For the scope of this project, I avoided introducing additional complexity such as databases, message queues, or caching layers.

**Using OpenAI for interpretation, not market data** — OpenAI is used to understand the user's question and summarise the results, while all stock data comes directly from Finnhub. This helps reduce the risk of the model inventing financial information and keeps responses grounded in real market data.

**Streamlit over a custom frontend** — I chose Streamlit because it allowed me to focus on the backend architecture and AI workflow rather than spending time building a frontend from scratch. The trade-off is less flexibility and customisation in the user interface.

**Favouring reliability over completeness** — If some non-essential data cannot be retrieved (for example a company profile or P/E ratio), the application still returns a useful response rather than failing completely. This provides a better user experience, although some context may be missing.

**Focusing on US-listed stocks and ETFs** — To keep the scope manageable, I focused on US-listed securities. Supporting multiple exchanges and regions would require additional symbol resolution and market-specific handling.

---

## What I'd Improve With More Time

- **Richer financial data** — Expand the data fetched from Finnhub to include additional metrics such as moving averages, RSI, earnings per share, and dividend yield, as well as broader context like earnings calendars, analyst ratings, and macroeconomic indicators.
- **News & sentiment analysis** — Incorporate recent company news, earnings coverage, and sentiment signals to provide richer context beyond market data alone.
- **International markets** — Expand beyond US-listed equities to support international exchanges and additional asset classes.
- **Request validation and guardrails** — Improve handling of ambiguous or unsupported prompts and add stricter validation around ticker extraction.
- **Caching & rate limiting** — Introduce in-memory caching to reduce duplicate API requests and better manage third-party API quotas.
- **Authentication & persistence** — Add user authentication and persistent storage for saved portfolios, preferences, and query history.
- **Monitoring & observability** — Add structured logs, metrics dashboards, health checks, and alerting for production visibility.
- **Better testing** — Add integration and end-to-end tests covering API failures, edge cases, and full request flows.
- **Deployment pipeline** — Add automated deployment workflows and container registry publishing.
- **Richer frontend experience** — Replace Streamlit with a React/Next.js frontend to support more advanced interactions and greater UI flexibility.

---

## AI Tools Used

I used ChatGPT and Claude throughout the project as development assistants.

ChatGPT was most helpful for high-level decisions, theoretical questions, and exploring ideas, such as architecture discussions, testing approaches, and general software engineering concepts. Claude was most helpful for hands-on coding and debugging, such as iterating on implementation details, fixing issues, refining prompts, and reviewing code structure.

Both tools helped speed up development and explore alternative approaches, but all code, design decisions, testing, and final implementation choices were reviewed and validated by me.
