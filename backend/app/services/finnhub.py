import logging

import httpx

from app.models.schemas import CandleResponse, CompanyProfileResponse, StockMetricsResponse, StockQuoteResponse
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
)


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

        data = await self._get("/quote", {"symbol": symbol.upper()})

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

        data = await self._get("/stock/profile2", {"symbol": symbol.upper()})

        if not data:
            raise StockNotFoundError(symbol)

        return CompanyProfileResponse.model_validate(data)

    async def get_metrics(self, symbol: str) -> StockMetricsResponse:
        """Fetch key fundamental metrics (P/E ratio) for the given symbol.

        Falls back to empty metrics if no API key is configured.

        Raises:
            ExternalAPIError: On timeout, HTTP error, or network failure.
        """
        if not self.api_key:
            logger.warning("No Finnhub key found, using mock metrics")
            return StockMetricsResponse(symbol=symbol, pe_ratio=None)

        data = await self._get("/stock/metric", {"symbol": symbol.upper(), "metric": "all"})

        metric = data.get("metric", {})
        pe = metric.get("peBasicExclExtraTTM") or metric.get("peNormalizedAnnual")
        return StockMetricsResponse(symbol=symbol, pe_ratio=pe if pe and pe > 0 else None)

    async def get_candles(self, symbol: str, from_ts: int, to_ts: int, resolution: str = "D") -> CandleResponse:
        """Fetch historical OHLC candles for a symbol between two Unix timestamps."""
        if not self.api_key:
            logger.warning("No Finnhub key found, using mock candle data")
            return CandleResponse(
                symbol=symbol,
                closes=[101.0, 102.0, 103.0],
                highs=[103.0, 104.0, 105.0],
                lows=[99.0, 100.0, 101.0],
            )

        data = await self._get(
            "/stock/candle",
            {"symbol": symbol.upper(), "resolution": resolution, "from": from_ts, "to": to_ts},
        )

        if data.get("s") == "no_data" or not data.get("c"):
            raise StockNotFoundError(symbol)

        return CandleResponse(
            symbol=symbol,
            closes=data["c"],
            highs=data["h"],
            lows=data["l"],
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
