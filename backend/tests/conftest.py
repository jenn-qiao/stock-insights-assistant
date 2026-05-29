from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.schemas import CandleResponse, CompanyProfileResponse, StockQuoteResponse
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
    )


def make_candle(symbol: str = "AAPL") -> CandleResponse:
    return CandleResponse(
        symbol=symbol,
        closes=[145.0, 148.0, 150.0],
        highs=[146.0, 149.0, 152.0],
        lows=[139.0, 144.0, 147.0],
    )


@pytest.fixture
def mock_finnhub():
    client = MagicMock()
    client.get_quote = AsyncMock(return_value=make_quote())
    client.get_company_profile = AsyncMock(return_value=make_profile())
    client.get_pe_ratio = AsyncMock(return_value=28.5)
    client.get_candles = AsyncMock(return_value=make_candle())
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
