# core/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    OPENAI_API_KEY: str
    OPENAI_API_ENDPOINT: str
    OPENAI_API_VERSION: str
    OPENAI_API_DEPLOYMENT_NAME: str

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
