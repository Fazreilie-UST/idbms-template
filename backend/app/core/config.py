from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # 🔧 App
    ENV: str = "prod"
    DEBUG: bool = False

    # 🔐 Security
    SECRET_KEY: str = "supersecret"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # 🗄️ Database
    DATABASE_URL: str

    # 🌐 CORS
    FRONTEND_URL: str = "http://localhost:5173"

    class Config:
        env_file = ".env"
        case_sensitive = True


# Cache settings so it's only loaded once
@lru_cache
def get_settings():
    return Settings()


settings = get_settings()