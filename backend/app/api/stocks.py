from fastapi import APIRouter, Depends

from app.models.schemas import CompanyProfileResponse, InsightResponse, StockQuoteResponse
from app.services.finnhub import FinnhubService, finnhub_service
from app.services.insight import StockInsightService
from app.services.openai import OpenAIService, openai_service

router = APIRouter(prefix="/stocks", tags=["stocks"])


def get_insight_service() -> StockInsightService:
    """Dependency factory — swap out finnhub/openai with mocks in tests."""
    return StockInsightService(finnhub=finnhub_service, openai=openai_service)


@router.get("/quote", response_model=StockQuoteResponse)
async def get_stock_quote(symbol: str) -> StockQuoteResponse:
    return await finnhub_service.get_quote(symbol)


@router.get("/profile", response_model=CompanyProfileResponse)
async def get_company_profile(symbol: str) -> CompanyProfileResponse:
    return await finnhub_service.get_company_profile(symbol)


@router.get("/insight", response_model=InsightResponse)
async def get_stock_insight(
    question: str,
    service: StockInsightService = Depends(get_insight_service),
) -> InsightResponse:
    return await service.get_insight(question)
