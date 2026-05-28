import logging
import time

import httpx

from app.models.schemas import CandleResponse, CompanyProfileResponse, StockQuoteResponse
from app.utils.exceptions import ExternalAPIError, StockNotFoundError

BASE_URL = "https://finnhub.io/api/v1"
TIMEOUT = httpx.Timeout(10.0)

logger = logging.getLogger(__name__)

# Returned when FINNHUB_API_KEY is not set — keeps the app runnable without credentials
MOCK_QUOTE = StockQuoteResponse(
    symbol="MOCK",
    current_price=150.0,
    high=155.0,
    low=145.0,
    open=148.0,
    previous_close=147.0,
    change=3.0,
    percent_change=2.04,
)

MOCK_PROFILE = CompanyProfileResponse(
    name="Mock Company Inc.",
    ticker="MOCK",
    exchange="NASDAQ",
    industry="Technology",
    market_cap=1000000.0,
    logo="",
    weburl="https://example.com",
)


# International exchange prefixes for known tickers
INTERNATIONAL_TICKERS = {
    # UK (LSE)
    "VOD": "LSE:VOD", "HSBA": "LSE:HSBA", "BP": "LSE:BP", "SHEL": "LSE:SHEL",
    "AZN": "LSE:AZN", "GSK": "LSE:GSK", "RIO": "LSE:RIO", "BHP": "LSE:BHP",
    # Germany (XETRA)
    "SAP": "XETRA:SAP", "SIE": "XETRA:SIE", "BMW": "XETRA:BMW",
    "VOW3": "XETRA:VOW3", "BAYN": "XETRA:BAYN", "DTE": "XETRA:DTE",
    # Japan (TSE)
    "7203": "TSE:7203",  # Toyota
    "6758": "TSE:6758",  # Sony
    "9984": "TSE:9984",  # SoftBank
    # Hong Kong (HKEX)
    "0700": "HKEX:0700",  # Tencent
    "9988": "HKEX:9988",  # Alibaba HK
}


def normalise_symbol(symbol: str) -> str:
    """Convert a raw ticker to the Finnhub-compatible symbol format.

    - Known international tickers get their exchange prefix (e.g. VOD -> LSE:VOD)
    - Everything else is passed through unchanged (US stocks, ETFs)
    """
    upper = symbol.upper()
    if upper in INTERNATIONAL_TICKERS:
        return INTERNATIONAL_TICKERS[upper]
    return upper


class FinnhubService:
    """Async client for the Finnhub stock market API."""

    def __init__(self, api_key: str | None):
        self.api_key = api_key

    async def get_quote(self, symbol: str) -> StockQuoteResponse:
        """Fetch a real-time stock quote for the given symbol.

        Falls back to mock data if no API key is configured.

        Raises:
            StockNotFoundError: If the symbol is unknown (Finnhub returns all zeros).
            ExternalAPIError: On timeout, HTTP error, or network failure.
        """
        if not self.api_key:
            logger.warning("No Finnhub key found, using mock data")
            return MOCK_QUOTE.model_copy(update={"symbol": symbol})

        finnhub_symbol = normalise_symbol(symbol)
        data = await self._get("/quote", {"symbol": finnhub_symbol})

        # Finnhub returns all zeros for unrecognised symbols
        if data.get("c", 0) == 0:
            raise StockNotFoundError(symbol)

        data["symbol"] = symbol
        return StockQuoteResponse.model_validate(data)

    async def get_company_profile(self, symbol: str) -> CompanyProfileResponse:
        """Fetch company profile information for the given symbol.

        Falls back to mock data if no API key is configured.

        Raises:
            StockNotFoundError: If the symbol is unknown (Finnhub returns empty dict).
            ExternalAPIError: On timeout, HTTP error, or network failure.
        """
        if not self.api_key:
            logger.warning("No Finnhub key found, using mock data")
            return MOCK_PROFILE.model_copy(update={"ticker": symbol})

        finnhub_symbol = normalise_symbol(symbol)
        data = await self._get("/stock/profile2", {"symbol": finnhub_symbol})

        if not data:
            raise StockNotFoundError(symbol)

        return CompanyProfileResponse.model_validate(data)

    async def get_candles(self, symbol: str, from_ts: int, to_ts: int, resolution: str = "D") -> CandleResponse:
        """Fetch historical OHLC candles for a symbol between two Unix timestamps."""
        if not self.api_key:
            logger.warning("No Finnhub key found, using mock candle data")
            now = int(time.time())
            return CandleResponse(
                symbol=symbol,
                opens=[100.0, 101.0, 102.0],
                closes=[101.0, 102.0, 103.0],
                highs=[103.0, 104.0, 105.0],
                lows=[99.0, 100.0, 101.0],
                timestamps=[now - 172800, now - 86400, now],
            )

        finnhub_symbol = normalise_symbol(symbol)
        data = await self._get(
            "/stock/candle",
            {"symbol": finnhub_symbol, "resolution": resolution, "from": from_ts, "to": to_ts},
        )

        if data.get("s") == "no_data" or not data.get("c"):
            raise StockNotFoundError(symbol)

        return CandleResponse(
            symbol=symbol,
            opens=data["o"],
            closes=data["c"],
            highs=data["h"],
            lows=data["l"],
            timestamps=data["t"],
        )

    async def _get(self, path: str, params: dict) -> dict:
        """Make an authenticated GET request to the Finnhub API.

        Raises:
            ExternalAPIError: On timeout, non-2xx response, or connection error.
        """
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                response = await client.get(
                    f"{BASE_URL}{path}",
                    params={**params, "token": self.api_key},
                )
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException as e:
            raise ExternalAPIError("Finnhub request timed out") from e
        except httpx.HTTPStatusError as e:
            raise ExternalAPIError(
                f"Finnhub returned unexpected status {e.response.status_code}"
            ) from e
        except httpx.RequestError as e:
            raise ExternalAPIError(f"Could not reach Finnhub: {e}") from e
