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


async def test_get_insight_calls_extract_tickers_with_question(service, mock_openai):
    await service.get_insight("How is Apple doing?")

    mock_openai.extract_tickers.assert_called_once_with("How is Apple doing?")


async def test_get_insight_calls_generate_summary_with_context(service, mock_openai):
    await service.get_insight("How is Apple doing?")

    mock_openai.generate_stock_summary.assert_called_once()
    call_args = mock_openai.generate_stock_summary.call_args
    assert call_args[0][0] == "How is Apple doing?"   # question passed through
    assert "AAPL Current Price" in call_args[0][1]    # context dict passed


async def test_get_insight_multiple_stocks(service, mock_finnhub, mock_openai):
    mock_openai.extract_tickers.return_value = ["AAPL", "MSFT"]
    mock_finnhub.get_quote = AsyncMock(side_effect=[make_quote("AAPL"), make_quote("MSFT")])
    mock_finnhub.get_company_profile = AsyncMock(
        side_effect=[make_profile("AAPL"), make_profile("MSFT")]
    )

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
    mock_openai.generate_stock_summary.assert_called_once()


# ---------------------------------------------------------------------------
# _safe_profile
# ---------------------------------------------------------------------------


async def test_safe_profile_returns_profile_on_success(service):
    result = await service._safe_profile("AAPL")

    assert result is not None
    assert result.ticker == "AAPL"


async def test_safe_profile_returns_none_on_api_error(service, mock_finnhub):
    mock_finnhub.get_company_profile.side_effect = ExternalAPIError("Not found")

    result = await service._safe_profile("AAPL")

    assert result is None


async def test_safe_profile_returns_none_on_any_exception(service, mock_finnhub):
    mock_finnhub.get_company_profile.side_effect = Exception("Unexpected error")

    result = await service._safe_profile("AAPL")

    assert result is None


# ---------------------------------------------------------------------------
# _build_context — pure function, no mocking needed
# ---------------------------------------------------------------------------


def test_build_context_includes_all_quote_fields(service):
    quote = make_quote("AAPL")
    result = service._build_context(["AAPL"], [quote], [None])

    assert result["AAPL Current Price"] == "$150.00"
    assert result["AAPL High"] == "$155.00"
    assert result["AAPL Low"] == "$145.00"
    assert result["AAPL Open"] == "$148.00"
    assert result["AAPL Previous Close"] == "$147.00"
    assert result["AAPL Change"] == "$3.00 (2.04%)"


def test_build_context_includes_profile_fields_when_present(service):
    result = service._build_context(["AAPL"], [make_quote()], [make_profile()])

    assert result["AAPL Company Name"] == "Apple Inc."
    assert result["AAPL Industry"] == "Technology"
    assert result["AAPL Exchange"] == "NASDAQ"
    assert "AAPL Market Cap" in result


def test_build_context_omits_profile_fields_when_none(service):
    result = service._build_context(["AAPL"], [make_quote()], [None])

    assert "AAPL Company Name" not in result
    assert "AAPL Industry" not in result
    assert "AAPL Market Cap" not in result


def test_build_context_handles_multiple_stocks(service):
    quotes = [make_quote("AAPL"), make_quote("MSFT")]
    profiles = [make_profile("AAPL"), None]

    result = service._build_context(["AAPL", "MSFT"], quotes, profiles)

    assert "AAPL Current Price" in result
    assert "MSFT Current Price" in result
    assert "AAPL Industry" in result       # profile present
    assert "MSFT Industry" not in result   # profile missing
