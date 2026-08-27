from pydantic_settings import BaseSettings, SettingsConfigDict

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
