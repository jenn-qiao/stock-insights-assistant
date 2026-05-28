import asyncio
import logging
import time

from app.models.schemas import CandleResponse, CompanyProfileResponse, InsightResponse, StockQuoteResponse
from app.services.finnhub import FinnhubService
from app.services.openai import OpenAIService

logger = logging.getLogger(__name__)

# Keywords that indicate the user wants historical/trend data
HISTORICAL_KEYWORDS = {
    "week", "weekly", "this week", "past week", "last week",
    "month", "monthly", "this month", "past month", "last month",
    "year", "yearly", "this year", "past year", "last year", "ytd", "year to date",
    "yoy", "year over year", "6 month", "6-month", "3 month", "3-month",
    "trend", "performance", "history", "historical", "over time",
    "52 week", "52-week", "all time", "ath",
}

def _detect_period(question: str) -> tuple[int, int, str] | None:
    """Return (from_ts, to_ts, label) if the question asks for historical data, else None."""
    q = question.lower()
    now = int(time.time())

    if any(k in q for k in ("this week", "past week", "last week", "week")):
        return now - 7 * 86400, now, "past week"
    if any(k in q for k in ("this month", "past month", "last month", "month")):
        return now - 30 * 86400, now, "past month"
    if any(k in q for k in ("3 month", "3-month", "three month")):
        return now - 90 * 86400, now, "past 3 months"
    if any(k in q for k in ("6 month", "6-month", "six month")):
        return now - 180 * 86400, now, "past 6 months"
    if any(k in q for k in ("ytd", "year to date")):
        import datetime
        jan1 = int(datetime.datetime(datetime.datetime.now().year, 1, 1).timestamp())
        return jan1, now, "year to date"
    if any(k in q for k in ("yoy", "year over year")):
        return now - 365 * 86400, now, "year over year"
    if any(k in q for k in ("this year", "past year", "last year", "year", "52 week", "52-week", "annual")):
        return now - 365 * 86400, now, "past year"
    if any(k in q for k in ("trend", "performance", "history", "historical", "over time")):
        return now - 90 * 86400, now, "past 3 months"
    return None


class StockInsightService:
    """Orchestrates the full stock insight flow.

    Sits between the route and the individual API clients.
    The route calls get_insight(); this service handles everything else.
    """

    def __init__(self, finnhub: FinnhubService, openai: OpenAIService):
        self.finnhub = finnhub
        self.openai = openai

    async def get_insight(self, question: str) -> InsightResponse:
        """Entry point for the insight flow.

        Parses the question, fetches all required data, builds the context,
        and returns a summarised response.
        """
        symbols = await self._parse_query(question)
        period = _detect_period(question)
        quotes, profiles = await self._fetch_stock_data(symbols)
        candles = await self._fetch_candles(symbols, period) if period else {}
        stock_data = self._build_context(symbols, quotes, profiles, candles, period)
        summary = await self.openai.generate_stock_summary(question, stock_data)
        return InsightResponse(symbols=symbols, summary=summary)

    def _build_context(
        self,
        symbols: list[str],
        quotes: list,
        profiles: list[CompanyProfileResponse | None],
        candles: dict[str, CandleResponse],
        period: tuple | None,
    ) -> dict:
        """Format quotes, profiles, and optional candles into a flat dict for the LLM prompt."""
        stock_data = {}
        for symbol, quote, profile in zip(symbols, quotes, profiles):
            stock_data[f"{symbol} Current Price"] = f"${quote.current_price:.2f}"
            stock_data[f"{symbol} Open"] = f"${quote.open:.2f}"
            stock_data[f"{symbol} High"] = f"${quote.high:.2f}"
            stock_data[f"{symbol} Low"] = f"${quote.low:.2f}"
            stock_data[f"{symbol} Previous Close"] = f"${quote.previous_close:.2f}"
            stock_data[f"{symbol} Change"] = f"${quote.change:.2f} ({quote.percent_change:.2f}%)"
            if profile:
                stock_data[f"{symbol} Company Name"] = profile.name
                stock_data[f"{symbol} Industry"] = profile.industry
                stock_data[f"{symbol} Market Cap"] = f"${profile.market_cap:.2f}M"
                stock_data[f"{symbol} Exchange"] = profile.exchange

            if symbol in candles and period:
                candle = candles[symbol]
                label = period[2]
                if candle.closes:
                    start_price = candle.closes[0]
                    end_price = candle.closes[-1]
                    pct = ((end_price - start_price) / start_price) * 100
                    period_high = max(candle.highs)
                    period_low = min(candle.lows)
                    stock_data[f"{symbol} {label} Start Price"] = f"${start_price:.2f}"
                    stock_data[f"{symbol} {label} End Price"] = f"${end_price:.2f}"
                    stock_data[f"{symbol} {label} Change"] = f"{pct:+.2f}%"
                    stock_data[f"{symbol} {label} High"] = f"${period_high:.2f}"
                    stock_data[f"{symbol} {label} Low"] = f"${period_low:.2f}"
                    stock_data[f"{symbol} {label} Data Points"] = str(len(candle.closes))
        return stock_data

    async def _fetch_candles(
        self, symbols: list[str], period: tuple[int, int, str]
    ) -> dict[str, CandleResponse]:
        """Fetch daily candles for all symbols over the given period.

        Failures are silently skipped — candle data is supplementary.
        """
        from_ts, to_ts, _ = period
        results = {}
        for symbol in symbols:
            try:
                results[symbol] = await self.finnhub.get_candles(symbol, from_ts, to_ts)
            except Exception:
                logger.warning("Could not fetch candles for %s — skipping", symbol)
        return results

    async def _parse_query(self, question: str) -> list[str]:
        """Extract ticker symbols from the user's natural language question.

        Delegates to OpenAIService.extract_tickers.
        Testable in isolation by mocking OpenAIService.
        """
        return await self.openai.extract_tickers(question)

    async def _fetch_stock_data(
        self, symbols: list[str]
    ) -> tuple[list, list[CompanyProfileResponse | None]]:
        """Fetch quotes and company profiles for all symbols in parallel.

        Quotes are required — any failure raises immediately.
        Profiles are optional — failures return None for that symbol
        so the insight can still be generated from price data alone.
        """
        quotes, profiles = await asyncio.gather(
            asyncio.gather(*[self.finnhub.get_quote(s) for s in symbols]),
            asyncio.gather(*[self._safe_profile(s) for s in symbols]),
        )
        return list(quotes), list(profiles)

    async def _safe_profile(self, symbol: str) -> CompanyProfileResponse | None:
        """Fetch a company profile, returning None on any failure.

        Keeps _fetch_stock_data fault-tolerant — a missing profile does
        not prevent the quote data from reaching the summarisation step.
        Testable by mocking FinnhubService.get_company_profile to raise.
        """
        try:
            return await self.finnhub.get_company_profile(symbol)
        except Exception:
            logger.warning("Could not fetch profile for %s — skipping", symbol)
            return None
