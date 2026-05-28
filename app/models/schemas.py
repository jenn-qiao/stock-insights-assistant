from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str


class StockQuoteResponse(BaseModel):
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
    name: str
    ticker: str
    exchange: str
    industry: str = Field(alias="finnhubIndustry")
    market_cap: float = Field(alias="marketCapitalization")
    logo: str
    weburl: str

    model_config = {"populate_by_name": True}


class InsightResponse(BaseModel):
    symbol: str
    summary: str


class ErrorResponse(BaseModel):
    detail: str
