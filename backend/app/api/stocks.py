from fastapi import APIRouter, Depends

from app.config import settings
from app.models.schemas import InsightResponse
from app.services.finnhub import FinnhubService
from app.services.insight import StockInsightService
from app.services.openai import OpenAIService

# Create router for all stock-related endpoints
router = APIRouter(prefix="/stocks", tags=["stocks"])


def get_insight_service() -> StockInsightService:
    # builds the service with real API clients on each request
    # in tests, we skip this and pass in mocked clients directly
    return StockInsightService(
        finnhub=FinnhubService(api_key=settings.finnhub_api_key),
        openai=OpenAIService(api_key=settings.openai_api_key),
    )


@router.get("/insight", response_model=InsightResponse)
async def get_stock_insight(
    question: str,
    service: StockInsightService = Depends(get_insight_service),
) -> InsightResponse:
    """Accept a natural language question and return an AI-generated stock summary."""
    return await service.get_insight(question)
