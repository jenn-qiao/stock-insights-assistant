from fastapi import APIRouter, Depends

from app.config import settings
from app.models.schemas import InsightResponse
from app.services.finnhub import FinnhubService
from app.services.insight import StockInsightService
from app.services.openai import OpenAIService

router = APIRouter(prefix="/stocks", tags=["stocks"])


def get_insight_service() -> StockInsightService:
    """Dependency factory — swap out finnhub/openai with mocks in tests."""
    return StockInsightService(
        finnhub=FinnhubService(api_key=settings.finnhub_api_key),
        openai=OpenAIService(api_key=settings.openai_api_key),
    )


@router.get("/insight", response_model=InsightResponse)
async def get_stock_insight(
    question: str,
    service: StockInsightService = Depends(get_insight_service),
) -> InsightResponse:
    return await service.get_insight(question)
