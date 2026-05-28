from openai import AsyncOpenAI

from app.config import settings
from app.models.schemas import InsightResponse, StockQuoteResponse


class OpenAIService:
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)

    async def get_insight(self, symbol: str, quote: StockQuoteResponse) -> InsightResponse:
        raise NotImplementedError


openai_service = OpenAIService(api_key=settings.openai_api_key)
