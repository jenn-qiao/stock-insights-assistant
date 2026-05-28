# Stock Insights Assistant

AI-powered stock analysis application built with FastAPI, Finnhub, and OpenAI.

Users can ask natural language questions about stocks and receive intelligent, summarized responses powered by real-time financial data and LLM-based analysis.

---

# Features

- Natural language stock queries
- Real-time stock market data via Finnhub
- AI-generated summaries via OpenAI
- FastAPI backend with modular architecture
- Async HTTP requests with `httpx`
- Structured Pydantic schemas
- Graceful error handling

---

# Example Queries

- "How is AAPL doing today?"
- "Compare Tesla and Ford"
- "What are the top gainers in tech?"

---

# Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI |
| AI | OpenAI API |
| Market Data | Finnhub API |
| HTTP Client | httpx |
| Validation | Pydantic |

---

# Project Structure

```text
app/
├── api/               # FastAPI routes/endpoints
├── services/          # Business logic + external API integrations
├── models/            # Pydantic schemas
├── utils/             # Exceptions and helpers
├── config.py          # Environment variables
└── main.py            # FastAPI entrypoint

tests/

requirements.txt
README.md
```

---

# Prerequisites

- Python 3.11+
- Finnhub API key
- OpenAI API key

---

# Environment Variables

Create a `.env` file in the project root:

```env
FINNHUB_API_KEY=your_finnhub_key
OPENAI_API_KEY=your_openai_key
```

You can copy from:

```bash
cp .env.example .env
```

---

# Local Development Setup

## 1. Create virtual environment

```bash
python3 -m venv .venv
```

## 2. Activate virtual environment

Mac/Linux:

```bash
source .venv/bin/activate
```

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

## 4. Run the application

```bash
uvicorn app.main:app --reload
```

## 5. Open Swagger docs

```text
http://localhost:8000/docs
```

---

# Architecture Overview

The application follows a layered architecture separating:

- API routes
- business logic/services
- external integrations
- schemas/models

External API logic is isolated in service classes to keep routes thin and improve testability.

---

# Current Status

Implemented so far:

- FastAPI backend scaffold
- health check endpoint
- Finnhub async service client
- structured Pydantic response models
- timeout/error handling
- environment variable configuration
- Swagger documentation
- modular project structure