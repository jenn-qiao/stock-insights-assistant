from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.stocks import router as stocks_router
from app.models.schemas import HealthResponse
from app.utils.exceptions import ExternalAPIError, StockNotFoundError

app = FastAPI(title="Stock Insights Assistant", version="0.1.0")

app.include_router(stocks_router)


# Custom exception handlers convert domain errors into consistent JSON responses.
# Without these, FastAPI would return a generic 500 for any unhandled exception.

@app.exception_handler(StockNotFoundError)
async def stock_not_found_handler(request: Request, exc: StockNotFoundError) -> JSONResponse:
    # 404 — the ticker was valid but Finnhub doesn't recognise it
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ExternalAPIError)
async def external_api_error_handler(request: Request, exc: ExternalAPIError) -> JSONResponse:
    # 502 Bad Gateway — our server got a bad response from an upstream service (Finnhub or OpenAI)
    return JSONResponse(status_code=502, content={"detail": str(exc)})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # Catch-all for anything unexpected — hides internal details from the client
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health() -> HealthResponse:
    return HealthResponse(status="ok")
