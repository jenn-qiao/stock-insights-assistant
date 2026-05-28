"""
Tests for pure utility functions — no mocking, no I/O.
"""

from app.services.finnhub import normalise_symbol
from app.services.insight import _detect_period


# ---------------------------------------------------------------------------
# normalise_symbol
# ---------------------------------------------------------------------------


def test_us_stock_passes_through():
    assert normalise_symbol("AAPL") == "AAPL"


def test_us_stock_lowercased_input():
    assert normalise_symbol("aapl") == "AAPL"


def test_international_routes_to_exchange():
    assert normalise_symbol("VOD") == "LSE:VOD"
    assert normalise_symbol("SAP") == "XETRA:SAP"
    assert normalise_symbol("7203") == "TSE:7203"


def test_etf_passes_through():
    assert normalise_symbol("SPY") == "SPY"
    assert normalise_symbol("QQQ") == "QQQ"


# ---------------------------------------------------------------------------
# _detect_period
# ---------------------------------------------------------------------------


def test_week_query():
    result = _detect_period("How has AAPL done this week?")
    assert result is not None
    _, _, label = result
    assert label == "past week"


def test_month_query():
    result = _detect_period("How is Tesla performing this month?")
    assert result is not None
    _, _, label = result
    assert label == "past month"


def test_three_month_query():
    result = _detect_period("Show me NVDA over 3 months")
    assert result is not None
    _, _, label = result
    assert label == "past 3 months"


def test_six_month_query():
    result = _detect_period("AAPL performance over 6 months")
    assert result is not None
    _, _, label = result
    assert label == "past 6 months"


def test_three_month_not_swallowed_by_month():
    """'3 month' must resolve to 90 days, not 30 — ordering bug regression test."""
    result = _detect_period("How has AAPL done over 3 months?")
    assert result is not None
    _, _, label = result
    assert label == "past 3 months"


def test_six_month_not_swallowed_by_month():
    result = _detect_period("AAPL over 6 months")
    assert result is not None
    _, _, label = result
    assert label == "past 6 months"


def test_ytd_query():
    result = _detect_period("How has MSFT done YTD?")
    assert result is not None
    _, _, label = result
    assert label == "year to date"


def test_yoy_query():
    result = _detect_period("What is TSLA YoY performance?")
    assert result is not None
    _, _, label = result
    assert label == "year over year"


def test_year_query():
    result = _detect_period("How has Apple performed this year?")
    assert result is not None
    _, _, label = result
    assert label == "past year"


def test_52_week_query():
    result = _detect_period("What is AAPL's 52-week range?")
    assert result is not None
    _, _, label = result
    assert label == "past year"


def test_current_price_query_returns_none():
    """A plain price question should not trigger historical data fetch."""
    assert _detect_period("How is Apple doing today?") is None
    assert _detect_period("What is TSLA's current price?") is None
    assert _detect_period("Compare AAPL and MSFT") is None


def test_period_timestamps_are_ordered():
    """from_ts must always be before to_ts."""
    for question in [
        "AAPL this week",
        "TSLA this month",
        "NVDA this year",
        "MSFT YTD",
    ]:
        result = _detect_period(question)
        assert result is not None
        from_ts, to_ts, _ = result
        assert from_ts < to_ts
