from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from db.database import DATABASE_FILE


class Settings(BaseSettings):
    app_name: str = "Airport Investment Agent API"
    api_prefix: str = "/api/v1"
    cors_allowed_origins: str = (
        "http://127.0.0.1:5173,http://localhost:5173"
    )
    airport_database_file: Path = DATABASE_FILE
    aerodatabox_api_key: str | None = None
    aerodatabox_base_url: str = "https://aerodatabox.p.rapidapi.com"
    aerodatabox_rapidapi_host: str = "aerodatabox.p.rapidapi.com"
    aerodatabox_timeout_seconds: float = 3.0
    use_aerodatabox: bool = True
    openai_api_key: str | None = None
    openai_model: str = "gpt-5-mini"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_timeout_seconds: float = 30.0
    use_openai: bool = True

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def allowed_origins(self) -> list[str]:
        return [
            origin.strip().rstrip("/")
            for origin in self.cors_allowed_origins.split(",")
            if origin.strip()
        ]


settings = Settings()
