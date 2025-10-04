# core/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    OPENAI_API_KEY: str
    OPENAI_API_ENDPOINT: str
    OPENAI_API_VERSION: str
    OPENAI_API_DEPLOYMENT_NAME: str

    NEO4J_URI: str
    NEO4J_USER: str
    NEO4J_PASSWORD: str

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
