from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./stocksense.db"
    ai_enabled: bool = False
    llm_provider: str = "mock"
    llm_model: str = "mock-model"
    llm_api_key: str = ""
    mock_mode: bool = False
    log_level: str = "INFO"


settings = Settings()
