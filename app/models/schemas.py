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

    model_config = {"populate_by_name": True}


class InsightResponse(BaseModel):
    symbol: str
    summary: str


class ErrorResponse(BaseModel):
    detail: str
