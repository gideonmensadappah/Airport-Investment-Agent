from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Airport Investment Agent API"
    api_prefix: str = "/api/v1"
    aerodatabox_api_key: str | None = None
    aerodatabox_base_url: str = "https://aerodatabox.p.rapidapi.com"
    aerodatabox_rapidapi_host: str = "aerodatabox.p.rapidapi.com"
    aerodatabox_timeout_seconds: float = 3.0
    use_aerodatabox: bool = True

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
