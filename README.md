# Stock Insights Assistant

AI-powered stock analysis application built with FastAPI, Finnhub, and OpenAI.

Users can ask natural language questions about stocks and receive intelligent, summarized responses powered by real-time financial data and LLM-based analysis.

---

## Features

- Natural language stock queries
- Real-time stock market data via Finnhub
- AI-generated summaries via OpenAI
- Multi-stock comparison support
- FastAPI backend with modular architecture
- Streamlit chat-style frontend
- Async HTTP requests with `httpx`
- Structured Pydantic schemas
- Graceful error handling

---

## Example Queries

- "How is Apple doing today?"
- "Compare Tesla and Ford"
- "What sector is AAPL in?"

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI |
| Frontend | Streamlit |
| AI | OpenAI API (gpt-4o-mini) |
| Market Data | Finnhub API |
| HTTP Client | httpx |
| Validation | Pydantic |

---

## Project Structure

```text
backend/
├── app/
│   ├── api/           # Route handlers (thin)
│   ├── services/      # Business logic + external API clients
│   ├── models/        # Pydantic schemas
│   ├── utils/         # Exceptions and helpers
│   ├── config.py      # Environment variable loading
│   └── main.py        # FastAPI entry point
├── tests/             # Unit tests
├── Dockerfile
└── requirements.txt

frontend/
├── app.py             # Streamlit UI
├── Dockerfile
└── requirements.txt

.env.example
```

---

## Prerequisites

- Python 3.11+
- Finnhub API key — [finnhub.io](https://finnhub.io)
- OpenAI API key — [platform.openai.com](https://platform.openai.com)

---

## Environment Variables

Copy the example file and fill in your keys:

```bash
cp .env.example .env
```

```env
FINNHUB_API_KEY=your_finnhub_key
OPENAI_API_KEY=your_openai_key
```

---

## Local Development

### 1. Create and activate virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r backend/requirements.txt
```

### 3. Run the backend

```bash
cd backend
uvicorn app.main:app --reload
```

### 4. Run the frontend (separate terminal)

```bash
cd frontend
streamlit run app.py
```

### 5. Open in browser

| Service | URL |
|---|---|
| Backend API | http://localhost:8000 |
| Swagger docs | http://localhost:8000/docs |
| Streamlit UI | http://localhost:8501 |

---

## Docker

First time or after any code changes:

```bash
docker compose up --build
```

Subsequent runs (no code changes):

```bash
docker compose up
```

| Service | URL |
|---|---|
| Backend API | http://localhost:8000 |
| Swagger docs | http://localhost:8000/docs |
| Streamlit UI | http://localhost:8501 |

> **Note:** `--build` tells Docker to rebuild the images. You need it the first time and any time you change code or dependencies. Without it, Docker reuses cached images and won't pick up your changes.

---

## Running Tests

### Locally

```bash
cd backend
pytest
```

### In Docker

```bash
docker compose run --rm backend pytest
```

> **Note:** This does not build the image. If you haven't built yet or have made code changes, run `docker compose run --rm --build backend pytest` instead.

### Standard workflow (clone → run → test)

```bash
cd jenniferq-stock-insights-assistant

docker compose up --build

docker compose exec backend pytest
```

Tests use mocked API clients — no real API calls are made.

---

## Architecture

```
Route → StockInsightService → FinnhubService  (market data)
                            → OpenAIService   (AI summarization)
```

| Layer | Responsibility |
|---|---|
| Route | HTTP transport only |
| StockInsightService | Workflow orchestration |
| FinnhubService | Finnhub API client |
| OpenAIService | OpenAI API client |
