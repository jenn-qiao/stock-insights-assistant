from fastapi import APIRouter, Depends

from app.config import settings
from app.models.schemas import InsightResponse
from app.services.finnhub import FinnhubService
from app.services.insight import StockInsightService
from app.services.openai import OpenAIService

# Create router for all stock-related endpoints
router = APIRouter(prefix="/stocks", tags=["stocks"])


def get_insight_service() -> StockInsightService:
    """
    Dependency injection factory.

    Creates and returns a StockInsightService instance
    with all required external service dependencies.

    Services can be swapped with mocks during unit tests.
    """

    return StockInsightService(
        # Service responsible for retrieving stock market data
        finnhub=FinnhubService(api_key=settings.finnhub_api_key),
        # Service responsible for generating AI insights
        openai=OpenAIService(api_key=settings.openai_api_key),
    )


@router.get("/insight", response_model=InsightResponse)
async def get_stock_insight(
    question: str,
    service: StockInsightService = Depends(get_insight_service),
) -> InsightResponse:
    """Accept a natural language question and return an AI-generated stock summary."""
    return await service.get_insight(question)
