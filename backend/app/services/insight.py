import asyncio
import logging

from app.models.schemas import CompanyProfileResponse, InsightResponse, StockQuoteResponse
from app.services.finnhub import FinnhubService
from app.services.openai import OpenAIService

logger = logging.getLogger(__name__)


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
        quotes, profiles = await self._fetch_stock_data(symbols)
        stock_data = self._build_context(symbols, quotes, profiles)
        summary = await self.openai.generate_stock_summary(question, stock_data)
        return InsightResponse(symbols=symbols, summary=summary)

    def _build_context(
        self,
        symbols: list[str],
        quotes: list,
        profiles: list[CompanyProfileResponse | None],
    ) -> dict:
        """Format quotes and profiles into a flat dict for the LLM prompt.

        This is pure data transformation — no I/O, no API calls.
        Easily unit tested without mocking anything.
        """
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
        return stock_data

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
