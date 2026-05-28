from fastapi import APIRouter, Depends

from app.config import settings
from app.models.schemas import CompanyProfileResponse, InsightResponse, StockQuoteResponse
from app.services.finnhub import FinnhubService
from app.services.insight import StockInsightService
from app.services.openai import OpenAIService

router = APIRouter(prefix="/stocks", tags=["stocks"])


def get_finnhub_service() -> FinnhubService:
    return FinnhubService(api_key=settings.finnhub_api_key)


def get_insight_service() -> StockInsightService:
    """Dependency factory — swap out finnhub/openai with mocks in tests."""
    return StockInsightService(
        finnhub=get_finnhub_service(),
        openai=OpenAIService(api_key=settings.openai_api_key),
    )


@router.get("/quote", response_model=StockQuoteResponse)
async def get_stock_quote(symbol: str) -> StockQuoteResponse:
    return await get_finnhub_service().get_quote(symbol)


@router.get("/profile", response_model=CompanyProfileResponse)
async def get_company_profile(symbol: str) -> CompanyProfileResponse:
    return await get_finnhub_service().get_company_profile(symbol)


@router.get("/insight", response_model=InsightResponse)
async def get_stock_insight(
    question: str,
    service: StockInsightService = Depends(get_insight_service),
) -> InsightResponse:
    return await service.get_insight(question)
