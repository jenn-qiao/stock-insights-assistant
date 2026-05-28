from pathlib import Path

from pydantic_settings import BaseSettings

# .env lives at the project root, two levels above this file (backend/app/config.py)
ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    finnhub_api_key: str
    openai_api_key: str

    model_config = {"env_file": str(ENV_FILE)}


settings = Settings()
