from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with Render/Postgres URL normalization.

    Render provides PostgreSQL URLs as ``postgres://``/``postgresql://``.
    SQLAlchemy's async PostgreSQL driver needs the ``+asyncpg`` scheme, so the
    conversion is kept in one place instead of being duplicated across the app.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
    )

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
    def database_url_async(self) -> str:
        url = self.database_url.strip()
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://") :]
        if url.startswith("postgresql://"):
            url = "postgresql+asyncpg://" + url[len("postgresql://") :]
        if not url.startswith("postgresql+asyncpg://"):
            raise ValueError(
                "DATABASE_URL must be a PostgreSQL URL "
                "(postgresql:// or postgresql+asyncpg://)"
            )
        return url

    @property
    def database_url_sync(self) -> str:
        return self.database_url_async.replace("+asyncpg", "", 1)

    @property
    def admin_id_set(self) -> set[int]:
        return {
            int(x.strip())
            for x in self.admin_ids.split(",")
            if x.strip().isdigit()
        }


settings = Settings()
