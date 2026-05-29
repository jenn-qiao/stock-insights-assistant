import logging
import time

from app.models.schemas import CandleResponse, CompanyProfileResponse, InsightResponse, StockMetricsResponse
from app.services.finnhub import FinnhubService
from app.services.openai import OpenAIService

logger = logging.getLogger(__name__)


def _detect_period(question: str) -> tuple[int, int, str] | None:
    """Return (from_ts, to_ts, label) if the question asks for weekly, monthly, or yearly data, else None."""
    q = question.lower()
    now = int(time.time())

    if "week" in q:
        return now - 7 * 86400, now, "past week"
    if "month" in q:
        return now - 30 * 86400, now, "past month"
    if "year" in q:
        return now - 365 * 86400, now, "past year"
    return None


class StockInsightService:
    """Orchestrates the full stock insight flow."""

    def __init__(self, finnhub: FinnhubService, openai: OpenAIService):
        self.finnhub = finnhub
        self.openai = openai

    async def get_insight(self, question: str) -> InsightResponse:
        symbols = await self.openai.extract_tickers(question)
        period = _detect_period(question)
        quotes, profiles, metrics_list = await self._fetch_stock_data(symbols)
        candles = {}
        if period:
            from_ts, to_ts, _ = period
            for symbol in symbols:
                try:
                    candles[symbol] = await self.finnhub.get_candles(symbol, from_ts, to_ts)
                except Exception:
                    logger.warning("Could not fetch candles for %s — skipping", symbol)
        stock_data = self._build_context(symbols, quotes, profiles, metrics_list, candles, period)
        summary = await self.openai.generate_stock_summary(question, stock_data)
        return InsightResponse(symbols=symbols, summary=summary)

    def _build_context(
        self,
        symbols: list[str],
        quotes: list,
        profiles: list[CompanyProfileResponse | None],
        metrics_list: list[StockMetricsResponse | None],
        candles: dict[str, CandleResponse],
        period: tuple | None,
    ) -> dict:
        """Format quotes, profiles, metrics, and optional candles into a flat dict for the LLM prompt."""
        stock_data = {}
        for symbol, quote, profile, metrics in zip(symbols, quotes, profiles, metrics_list):
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
            if metrics and metrics.pe_ratio is not None:
                stock_data[f"{symbol} P/E Ratio"] = f"{metrics.pe_ratio:.2f}"

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
        return stock_data

    async def _fetch_stock_data(
        self, symbols: list[str]
    ) -> tuple[list, list[CompanyProfileResponse | None], list[StockMetricsResponse | None]]:
        """Fetch quotes, profiles, and metrics for each symbol sequentially."""
        quotes = []
        profiles = []
        metrics_list = []
        for symbol in symbols:
            quotes.append(await self.finnhub.get_quote(symbol))
            profiles.append(await self._safe_profile(symbol))
            metrics_list.append(await self._safe_metrics(symbol))
        return quotes, profiles, metrics_list

    async def _safe_profile(self, symbol: str) -> CompanyProfileResponse | None:
        """Fetch a company profile, returning None on any failure."""
        try:
            return await self.finnhub.get_company_profile(symbol)
        except Exception:
            logger.warning("Could not fetch profile for %s — skipping", symbol)
            return None

    async def _safe_metrics(self, symbol: str) -> StockMetricsResponse | None:
        """Fetch fundamental metrics, returning None on any failure."""
        try:
            return await self.finnhub.get_metrics(symbol)
        except Exception:
            logger.warning("Could not fetch metrics for %s — skipping", symbol)
            return None
