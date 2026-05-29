import logging
import time

from app.models.schemas import InsightResponse
from app.services.finnhub import FinnhubService
from app.services.openai import OpenAIService

logger = logging.getLogger(__name__)

# curated stock lists by sector — used when the user asks for top gainers/losers
SECTOR_TICKERS: dict[str, list[str]] = {
    "tech": ["AAPL", "MSFT", "NVDA", "META", "GOOGL", "AMZN", "TSLA", "AMD", "INTC", "QCOM", "ORCL", "CRM", "NFLX", "ADBE", "PLTR"],
    "finance": ["JPM", "GS", "BAC", "WFC", "MS", "BLK", "V", "MA", "PYPL", "C"],
    "healthcare": ["JNJ", "PFE", "UNH", "ABBV", "MRK", "LLY", "TMO", "ABT"],
    "energy": ["XOM", "CVX", "COP", "SLB", "EOG", "PXD"],
    "retail": ["WMT", "AMZN", "TGT", "COST", "HD", "LOW", "EBAY", "ETSY", "SHOP", "NKE"],
    "consumer": ["MCD", "SBUX", "KO", "PEP", "PG", "CL", "DIS", "NFLX", "ABNB", "UBER"],
    "crypto": ["COIN", "MSTR", "HOOD", "RIOT", "MARA"],
    # fallback list when no sector is mentioned
    "general": ["AAPL", "MSFT", "NVDA", "META", "GOOGL", "AMZN", "TSLA", "AMD", "JPM", "V", "NFLX", "DIS", "UBER", "COIN", "PLTR"],
}

# words that map a user's sector mention to a key in SECTOR_TICKERS
SECTOR_KEYWORDS: dict[str, str] = {
    "tech": "tech", "technology": "tech", "software": "tech",
    "finance": "finance", "financial": "finance", "banking": "finance", "bank": "finance",
    "health": "healthcare", "healthcare": "healthcare", "pharma": "healthcare", "pharmaceutical": "healthcare",
    "energy": "energy", "oil": "energy",
    "retail": "retail", "shopping": "retail",
    "consumer": "consumer", "food": "consumer", "beverage": "consumer",
    "crypto": "crypto", "cryptocurrency": "crypto", "bitcoin": "crypto",
}


def _detect_scan(question: str) -> tuple[str, str] | None:
    """Check if the user is asking for top gainers or losers (with optional sector).
    Returns (direction, sector) e.g. ("gainer", "tech"), or None if not a scan question.
    """
    q = question.lower()

    is_gainer = any(w in q for w in ["gainer", "gaining", "best performing", "biggest gain", "top gain", "up today", "rising","winners"])
    is_loser = any(w in q for w in ["loser", "losing", "worst performing", "biggest loss", "top loss", "down today", "falling", "dropping"])

    if not (is_gainer or is_loser):
        return None

    direction = "gainer" if is_gainer else "loser"

    # check if the user mentioned a sector
    sector = "general"
    for keyword, sector_key in SECTOR_KEYWORDS.items():
        if keyword in q:
            sector = sector_key
            break

    return direction, sector


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
        # check if they want top gainers/losers — handled differently from a single stock lookup
        scan = _detect_scan(question)
        if scan:
            return await self._get_scan_insight(question, scan)

        # ask OpenAI what stock(s) the user is asking about
        symbols = await self.openai.extract_tickers(question)

        # check if they're asking about a specific time period
        period = _detect_period(question)

        # get current price, company info, and P/E ratio for each stock
        quotes, profiles, pe_ratios = await self._fetch_stock_data(symbols)

        # only fetch historical data if the question mentions a time period —
        # no point calling Finnhub for candles if they just want today's price
        candles = {}
        if period:
            from_ts, to_ts, _ = period
            for symbol in symbols:
                try:
                    candles[symbol] = await self.finnhub.get_candles(symbol, from_ts, to_ts)
                except Exception:
                    # if historical data fails, skip it — we can still show today's price
                    logger.warning("Could not fetch candles for %s — skipping", symbol)

        # put all the data into a dictionary for OpenAI to read
        stock_data = self._build_context(symbols, quotes, profiles, pe_ratios, candles, period)

        # ask OpenAI to turn that data into a plain English summary
        summary = await self.openai.generate_stock_summary(question, stock_data)

        return InsightResponse(symbols=symbols, summary=summary)

    async def _get_scan_insight(self, question: str, scan: tuple[str, str]) -> InsightResponse:
        """Fetch quotes for a sector's stock list, rank by % change, return the top 5."""
        direction, sector = scan
        tickers = SECTOR_TICKERS[sector]

        # fetch a quote for every ticker in the list — skip any that fail
        results: list[tuple[str, object]] = []
        for ticker in tickers:
            try:
                quote = await self.finnhub.get_quote(ticker)
                results.append((ticker, quote))
            except Exception:
                logger.warning("Could not fetch quote for %s — skipping", ticker)

        # sort by % change: highest first for gainers, lowest first for losers
        results.sort(key=lambda x: x[1].percent_change, reverse=(direction == "gainer"))
        top5 = results[:5]

        # build a ranked data dict for OpenAI — "#1 NVDA", "#2 META", etc.
        stock_data: dict[str, str] = {}
        for rank, (symbol, quote) in enumerate(top5, start=1):
            stock_data[f"#{rank} {symbol} Price"] = f"${quote.current_price:.2f}"
            stock_data[f"#{rank} {symbol} Change"] = f"{quote.percent_change:+.2f}%"

        summary = await self.openai.generate_stock_summary(question, stock_data)
        return InsightResponse(symbols=[s for s, _ in top5], summary=summary)

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

            # company info isn't always available (e.g. some ETFs), so only add it if we got it
            if profile:
                stock_data[f"{symbol} Company Name"] = profile.name
                stock_data[f"{symbol} Industry"] = profile.industry
                stock_data[f"{symbol} Market Cap"] = f"${profile.market_cap:.2f}M"
                stock_data[f"{symbol} Exchange"] = profile.exchange

            # same for P/E — not all stocks have one, so skip it if missing
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
        Price is required — if that fails the whole request fails.
        Company info and P/E are optional — skipped if unavailable so a partial failure
        doesn't block the whole response.
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
