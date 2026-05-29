import logging

import httpx

from app.models.schemas import CandleResponse, CompanyProfileResponse, StockQuoteResponse
from app.utils.exceptions import ExternalAPIError, StockNotFoundError

BASE_URL = "https://finnhub.io/api/v1"
TIMEOUT = httpx.Timeout(10.0)

logger = logging.getLogger(__name__)


class FinnhubService:
    """Handles all requests to the Finnhub stock market API."""

    def __init__(self, api_key: str | None):
        self.api_key = api_key

    async def get_quote(self, symbol: str) -> StockQuoteResponse:
        if not self.api_key:
            logger.warning("No Finnhub key found, using mock data")
            return StockQuoteResponse(
                symbol=symbol,
                current_price=150.0,
                high=155.0,
                low=145.0,
                open=148.0,
                previous_close=147.0,
                change=3.0,
                percent_change=2.04,
            )

        data = await self._get("/quote", {"symbol": symbol.upper()})

        # Finnhub returns all zeros for unknown symbols instead of a 404,
        # so we check the price field and raise our own error
        if data.get("c", 0) == 0:
            raise StockNotFoundError(symbol)

        # Finnhub doesn't include the symbol in the response so we add it manually
        data["symbol"] = symbol
        return StockQuoteResponse.model_validate(data)

    async def get_company_profile(self, symbol: str) -> CompanyProfileResponse:
        if not self.api_key:
            logger.warning("No Finnhub key found, using mock data")
            return CompanyProfileResponse(
                name="Mock Company Inc.",
                ticker=symbol,
                exchange="NASDAQ",
                industry="Technology",
                market_cap=1000000.0,
            )

        data = await self._get("/stock/profile2", {"symbol": symbol.upper()})

        # Finnhub returns an empty dict for unknown symbols instead of a 404
        if not data:
            raise StockNotFoundError(symbol)

        return CompanyProfileResponse.model_validate(data)

    async def get_pe_ratio(self, symbol: str) -> float | None:
        """Returns the P/E ratio for a stock, or None if not available."""
        if not self.api_key:
            return None

        data = await self._get("/stock/metric", {"symbol": symbol.upper(), "metric": "all"})
        metric = data.get("metric", {})
        # try the trailing twelve months P/E first, fall back to the annual figure
        pe = metric.get("peBasicExclExtraTTM") or metric.get("peNormalizedAnnual")
        return pe if pe and pe > 0 else None

    async def get_candles(self, symbol: str, from_ts: int, to_ts: int) -> CandleResponse:
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
            {"symbol": symbol.upper(), "resolution": "D", "from": from_ts, "to": to_ts},
        )

        # Finnhub returns {"s": "no_data"} when there are no candles for the date range
        if data.get("s") == "no_data" or not data.get("c"):
            raise StockNotFoundError(symbol)

        return CandleResponse(
            symbol=symbol,
            closes=data["c"],
            highs=data["h"],
            lows=data["l"],
        )

    async def _get(self, path: str, params: dict) -> dict:
        """Make a GET request to Finnhub with the API key attached."""
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                response = await client.get(
                    f"{BASE_URL}{path}",
                    params={**params, "token": self.api_key},
                )
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException:
            raise ExternalAPIError("Finnhub request timed out")
        except httpx.HTTPStatusError as e:
            raise ExternalAPIError(f"Finnhub returned unexpected status {e.response.status_code}")
        except httpx.RequestError as e:
            raise ExternalAPIError(f"Could not reach Finnhub: {e}")
