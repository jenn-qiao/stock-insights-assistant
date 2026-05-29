import logging
import time

from app.models.schemas import InsightResponse
from app.services.finnhub import FinnhubService
from app.services.openai import OpenAIService

logger = logging.getLogger(__name__)


def _detect_period(question: str) -> tuple | None:
    """Check if the question is asking about a time period (week, month, year).
    Returns None if the question is just asking about today's price.
    """
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

    def __init__(self, finnhub: FinnhubService, openai: OpenAIService):
        self.finnhub = finnhub
        self.openai = openai

    async def get_insight(self, question: str) -> InsightResponse:
        # ask OpenAI what stock(s) the user is asking about
        symbols = await self.openai.extract_tickers(question)

        # check if they're asking about a specific time period
        period = _detect_period(question)

        # get current price, company info, and P/E ratio for each stock
        quotes, profiles, pe_ratios = await self._fetch_stock_data(symbols)

        # if they asked about a time period, also get historical price data
        candles = {}
        if period:
            from_ts, to_ts, _ = period
            for symbol in symbols:
                try:
                    candles[symbol] = await self.finnhub.get_candles(symbol, from_ts, to_ts)
                except Exception:
                    logger.warning("Could not fetch candles for %s — skipping", symbol)

        # put all the data into a dictionary for OpenAI to read
        stock_data = self._build_context(symbols, quotes, profiles, pe_ratios, candles, period)

        # ask OpenAI to turn that data into a plain English summary
        summary = await self.openai.generate_stock_summary(question, stock_data)

        return InsightResponse(symbols=symbols, summary=summary)

    def _build_context(
        self,
        symbols: list,
        quotes: list,
        profiles: list,
        pe_ratios: list,
        candles: dict,
        period: tuple | None,
    ) -> dict:
        """Build a dictionary of stock data to send to OpenAI.
        Keys are plain labels like "AAPL Current Price" so the AI knows what each value means.
        """
        stock_data = {}
        for symbol, quote, profile, pe in zip(symbols, quotes, profiles, pe_ratios):
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

            if pe is not None:
                stock_data[f"{symbol} P/E Ratio"] = f"{pe:.2f}"

            if symbol in candles and period:
                candle = candles[symbol]
                label = period[2]
                if candle.closes:
                    start_price = candle.closes[0]
                    end_price = candle.closes[-1]
                    pct = ((end_price - start_price) / start_price) * 100
                    stock_data[f"{symbol} {label} Start Price"] = f"${start_price:.2f}"
                    stock_data[f"{symbol} {label} End Price"] = f"${end_price:.2f}"
                    stock_data[f"{symbol} {label} Change"] = f"{pct:+.2f}%"
                    stock_data[f"{symbol} {label} High"] = f"${max(candle.highs):.2f}"
                    stock_data[f"{symbol} {label} Low"] = f"${min(candle.lows):.2f}"

        return stock_data

    async def _fetch_stock_data(self, symbols: list) -> tuple:
        """Get price, company info, and P/E ratio for each stock.
        Price is required. Company info and P/E are optional — skipped if unavailable.
        """
        quotes = []
        profiles = []
        pe_ratios = []
        for symbol in symbols:
            quotes.append(await self.finnhub.get_quote(symbol))

            try:
                profiles.append(await self.finnhub.get_company_profile(symbol))
            except Exception:
                logger.warning("Could not fetch profile for %s — skipping", symbol)
                profiles.append(None)

            try:
                pe_ratios.append(await self.finnhub.get_pe_ratio(symbol))
            except Exception:
                logger.warning("Could not fetch P/E ratio for %s — skipping", symbol)
                pe_ratios.append(None)

        return quotes, profiles, pe_ratios
