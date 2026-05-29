"""
Unit tests for StockInsightService.

All external calls (Finnhub, OpenAI) are mocked.
No real API calls are made.
"""

import pytest
from unittest.mock import AsyncMock

from app.models.schemas import InsightResponse
from app.utils.exceptions import ExternalAPIError, StockNotFoundError
from tests.conftest import make_profile, make_quote


# ---------------------------------------------------------------------------
# get_insight — full flow
# ---------------------------------------------------------------------------


async def test_get_insight_returns_insight_response(service):
    result = await service.get_insight("How is Apple doing?")

    assert isinstance(result, InsightResponse)
    assert result.symbols == ["AAPL"]
    assert result.summary == "Apple is up 2% today."


async def test_get_insight_calls_generate_summary_with_context(service, mock_openai):
    await service.get_insight("How is Apple doing?")

    mock_openai.generate_stock_summary.assert_called_once()
    call_args = mock_openai.generate_stock_summary.call_args
    assert call_args[0][0] == "How is Apple doing?"
    assert "AAPL Current Price" in call_args[0][1]


async def test_get_insight_multiple_stocks(service, mock_finnhub, mock_openai):
    mock_openai.extract_tickers.return_value = ["AAPL", "MSFT"]
    mock_finnhub.get_quote = AsyncMock(side_effect=[make_quote("AAPL"), make_quote("MSFT")])
    mock_finnhub.get_company_profile = AsyncMock(
        side_effect=[make_profile("AAPL"), make_profile("MSFT")]
    )
    mock_finnhub.get_pe_ratio = AsyncMock(side_effect=[28.5, 32.1])

    result = await service.get_insight("Compare Apple and Microsoft")

    assert result.symbols == ["AAPL", "MSFT"]


# ---------------------------------------------------------------------------
# get_insight — failure scenarios
# ---------------------------------------------------------------------------


async def test_get_insight_raises_when_ticker_extraction_fails(service, mock_openai):
    mock_openai.extract_tickers.side_effect = ExternalAPIError(
        "Could not identify any stocks from the question"
    )

    with pytest.raises(ExternalAPIError, match="Could not identify"):
        await service.get_insight("what is the weather like?")


async def test_get_insight_raises_when_quote_fetch_fails(service, mock_finnhub):
    mock_finnhub.get_quote.side_effect = ExternalAPIError("Finnhub request timed out")

    with pytest.raises(ExternalAPIError, match="timed out"):
        await service.get_insight("How is Apple doing?")


async def test_get_insight_raises_when_stock_not_found(service, mock_finnhub):
    mock_finnhub.get_quote.side_effect = StockNotFoundError("FAKE")

    with pytest.raises(StockNotFoundError):
        await service.get_insight("How is FAKE doing?")


async def test_get_insight_succeeds_when_profile_fetch_fails(service, mock_finnhub, mock_openai):
    """Profile failure should not block the insight — quote data is enough."""
    mock_finnhub.get_company_profile.side_effect = ExternalAPIError("Profile not found")

    result = await service.get_insight("How is Apple doing?")

    assert isinstance(result, InsightResponse)


# ---------------------------------------------------------------------------
# _build_context
# ---------------------------------------------------------------------------


def test_build_context_includes_all_quote_fields(service):
    result = service._build_context(["AAPL"], [make_quote("AAPL")], [None], [None], {}, None)

    assert result["AAPL Current Price"] == "$150.00"
    assert result["AAPL High"] == "$155.00"
    assert result["AAPL Low"] == "$145.00"
    assert result["AAPL Open"] == "$148.00"
    assert result["AAPL Previous Close"] == "$147.00"
    assert result["AAPL Change"] == "$3.00 (2.04%)"


def test_build_context_includes_profile_and_pe_when_present(service):
    result = service._build_context(["AAPL"], [make_quote()], [make_profile()], [28.5], {}, None)

    assert result["AAPL Company Name"] == "Apple Inc."
    assert result["AAPL Industry"] == "Technology"
    assert result["AAPL Exchange"] == "NASDAQ"
    assert "AAPL Market Cap" in result
    assert result["AAPL P/E Ratio"] == "28.50"


def test_build_context_omits_profile_and_pe_when_none(service):
    result = service._build_context(["AAPL"], [make_quote()], [None], [None], {}, None)

    assert "AAPL Company Name" not in result
    assert "AAPL Industry" not in result
    assert "AAPL Market Cap" not in result
    assert "AAPL P/E Ratio" not in result
