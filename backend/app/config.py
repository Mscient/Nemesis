from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/stocksense"
    ai_enabled: bool = False
    llm_provider: str = "mock"
    llm_model: str = "mock-model"
    llm_api_key: str = ""
    mock_mode: bool = False
    log_level: str = "INFO"

    def model_post_init(self, __context) -> None:
        """
        Normalize the DATABASE_URL so it always uses the asyncpg driver scheme.
        Render (and many other platforms) inject a plain `postgresql://` or
        `postgres://` URL — SQLAlchemy async requires `postgresql+asyncpg://`.
        """
        url = self.database_url
        if url.startswith("postgres://"):
            object.__setattr__(self, "database_url", url.replace("postgres://", "postgresql+asyncpg://", 1))
        elif url.startswith("postgresql://"):
            object.__setattr__(self, "database_url", url.replace("postgresql://", "postgresql+asyncpg://", 1))


settings = Settings()
