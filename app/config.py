from pydantic_settings import BaseSettings
class Settings(BaseSettings):
    BOT_TOKEN:str=""
    DATABASE_URL:str="postgresql+asyncpg://postgres:postgres@localhost:5432/vldst"
    WEBAPP_URL:str="http://localhost:8000"
    PUBLIC_URL:str="http://localhost:8000"
    ADMIN_IDS:str=""
    SECRET_KEY:str="change-me"
    class Config:
        env_file=".env"
        extra="ignore"
settings=Settings()
