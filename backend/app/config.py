from pathlib import Path

from pydantic_settings import BaseSettings

# .env lives at the project root, two levels above this file (backend/app/config.py)
ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    # both keys are optional so the app still runs in CI without real credentials
    finnhub_api_key: str | None = None
    openai_api_key: str | None = None

    model_config = {"env_file": str(ENV_FILE)}


settings = Settings()
