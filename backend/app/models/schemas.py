from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str


class StockQuoteResponse(BaseModel):
    """Maps Finnhub's single-letter quote fields to readable names."""

    symbol: str
    current_price: float = Field(alias="c")
    high: float = Field(alias="h")
    low: float = Field(alias="l")
    open: float = Field(alias="o")
    previous_close: float = Field(alias="pc")
    change: float = Field(alias="d")
    percent_change: float = Field(alias="dp")

    model_config = {"populate_by_name": True}


class CompanyProfileResponse(BaseModel):
    """Maps Finnhub's camelCase profile fields to readable names."""

    name: str
    ticker: str
    exchange: str
    industry: str = Field(alias="finnhubIndustry")
    market_cap: float = Field(alias="marketCapitalization")  # in millions USD

    model_config = {"populate_by_name": True}


class CandleResponse(BaseModel):
    """Historical price data for a symbol over a date range, used for trend queries."""

    symbol: str
    closes: list[float]
    highs: list[float]
    lows: list[float]


class StockMetricsResponse(BaseModel):
    """Key fundamental metrics for a stock."""

    symbol: str
    pe_ratio: float | None = None  # trailing twelve months P/E


class InsightResponse(BaseModel):
    symbols: list[str]
    summary: str


