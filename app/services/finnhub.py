import httpx

from app.config import settings
from app.models.schemas import StockQuoteResponse
from app.utils.exceptions import ExternalAPIError, StockNotFoundError

BASE_URL = "https://finnhub.io/api/v1"


class FinnhubService:
    def __init__(self, api_key: str):
        self.api_key = api_key


    #for testing purposes, remove later 
    async def get_quote(self, symbol: str) -> StockQuoteResponse:
        return StockQuoteResponse(
            symbol=symbol,
            current_price=100.0,
            high=105.0,
            low=95.0,
            open=99.0,
            previous_close=98.0,
        )
    
    # CHANGE back later
    # async def get_quote(self, symbol: str) -> StockQuoteResponse:
    #     raise NotImplementedError


finnhub_service = FinnhubService(api_key=settings.finnhub_api_key)
