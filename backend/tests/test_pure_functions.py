"""
Tests for pure utility functions — no mocking, no I/O.
"""

from app.services.insight import _detect_period


# _detect_period


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


def test_year_query():
    result = _detect_period("How has Apple performed this year?")
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
    for question in ["AAPL this week", "TSLA this month", "NVDA this year"]:
        result = _detect_period(question)
        assert result is not None
        from_ts, to_ts, _ = result
        assert from_ts < to_ts
