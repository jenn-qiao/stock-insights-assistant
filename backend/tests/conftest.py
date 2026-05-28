from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.schemas import CompanyProfileResponse, StockQuoteResponse
from app.services.insight import StockInsightService


def make_quote(symbol: str = "AAPL") -> StockQuoteResponse:
    return StockQuoteResponse(
        symbol=symbol,
        current_price=150.0,
        high=155.0,
        low=145.0,
        open=148.0,
        previous_close=147.0,
        change=3.0,
        percent_change=2.04,
    )


def make_profile(symbol: str = "AAPL") -> CompanyProfileResponse:
    return CompanyProfileResponse(
        name="Apple Inc.",
        ticker=symbol,
        exchange="NASDAQ",
        industry="Technology",
        market_cap=3000000.0,
        logo="https://logo.clearbit.com/apple.com",
        weburl="https://www.apple.com",
    )


@pytest.fixture
def mock_finnhub():
    client = MagicMock()
    client.get_quote = AsyncMock(return_value=make_quote())
    client.get_company_profile = AsyncMock(return_value=make_profile())
    return client


@pytest.fixture
def mock_openai():
    client = MagicMock()
    client.extract_tickers = AsyncMock(return_value=["AAPL"])
    client.generate_stock_summary = AsyncMock(return_value="Apple is up 2% today.")
    return client


@pytest.fixture
def service(mock_finnhub, mock_openai):
    return StockInsightService(finnhub=mock_finnhub, openai=mock_openai)
