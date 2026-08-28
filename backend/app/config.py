from pydantic_settings import BaseSettings, SettingsConfigDict

def normalize_database_url(url: str) -> str:
    """Normalize Render/libpq PostgreSQL URLs for SQLAlchemy asyncpg."""
    url = (url or "").strip()
    if url.startswith("postgres://"):
        return "postgresql+asyncpg://" + url[len("postgres://"): ]
    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url[len("postgresql://"): ]
    if url.startswith("postgresql+psycopg://"):
        return "postgresql+asyncpg://" + url[len("postgresql+psycopg://"): ]
    return url

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    bot_token: str = ""
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/vldst"
    public_url: str = "http://localhost:8000"
    webapp_url: str = "http://localhost:8000/"
    admin_url: str = "http://localhost:8000/admin/"
    bot_username: str = "vldst_bot"
    admin_ids: str = ""
    secret_key: str = "dev-only-change-me"
    stars_provider_token: str = ""
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:8000"

    @property
    def admin_id_set(self):
        return {int(x.strip()) for x in self.admin_ids.split(",") if x.strip().isdigit()}

settings = Settings()
settings.database_url = normalize_database_url(settings.database_url)
