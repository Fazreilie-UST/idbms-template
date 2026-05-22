import os
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 🔧 App
    ENV: str = os.getenv("ENV", "dev")  # dev or prod
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

    # 🔐 Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # 🗄️ Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # 🌐 CORS
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")

    # 🔐 Auth config
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    MAX_FAILED_LOGIN_ATTEMPTS: int = 5
    LOGIN_LOCK_MINUTES: int = 15

    # 🚦 Rate limiting
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
    RATE_LIMIT_STORAGE_URI: str = os.getenv("RATE_LIMIT_STORAGE_URI", "redis://localhost:6379/0")
    RATE_LIMIT_LOGIN: str = os.getenv("RATE_LIMIT_LOGIN", "5/minute")
    RATE_LIMIT_REFRESH: str = os.getenv("RATE_LIMIT_REFRESH", "20/minute")
    
    # 🍪 Cookie config
    REFRESH_COOKIE_NAME: str = "refresh_token"
    ACCESS_COOKIE_NAME: str = "access_token"
    CSRF_COOKIE_NAME: str = "csrf_token"
    CSRF_HEADER_NAME: str = "X-CSRF-Token"
    COOKIE_SECURE: bool = ENV == "prod"
    COOKIE_SAMESITE: str = "none" if ENV == "prod" else "lax"
    # Comma-separated list of additional origins allowed by CORS (besides FRONTEND_URL).
    CORS_EXTRA_ORIGINS: str = os.getenv("CORS_EXTRA_ORIGINS", "")
    # Strict-Transport-Security max-age (only emitted in prod).
    HSTS_MAX_AGE: int = int(os.getenv("HSTS_MAX_AGE", str(60 * 60 * 24 * 365)))

    # 📦 Request body cap (applies globally; route handlers may enforce tighter).
    MAX_REQUEST_BODY_BYTES: int = int(
        os.getenv("MAX_REQUEST_BODY_BYTES", str(100 * 1024 * 1024))  # 100 MB
    )

    #  Build plan bulk import storage (Excel files uploaded by PM)
    BUILD_PLAN_IMPORT_DIR: str = os.getenv(
        "BUILD_PLAN_IMPORT_DIR",
        "/home/fbinalex/NPI-IDBMS/db/build-plans",
    )

    # 📁 Shipping bulk import storage (Master Board Tracker files uploaded by PM)
    SHIPPING_IMPORT_DIR: str = os.getenv(
        "SHIPPING_IMPORT_DIR",
        "/home/fbinalex/NPI-IDBMS/db/shippings",
    )

    # 🖼️ Profile picture storage (uploaded by users from the account page)
    PROFILE_PICTURE_DIR: str = os.getenv(
        "PROFILE_PICTURE_DIR",
        "/home/fbinalex/NPI-IDBMS/db/profile-pictures",
    )
    # URL path the static mount is exposed at; the stored value in the
    # database is `<PROFILE_PICTURE_URL_PREFIX>/<filename>` so the frontend
    # only needs to prepend the API origin.
    PROFILE_PICTURE_URL_PREFIX: str = "/static/profile-pictures"
    PROFILE_PICTURE_MAX_BYTES: int = int(
        os.getenv("PROFILE_PICTURE_MAX_BYTES", str(2 * 1024 * 1024))  # 2 MB
    )

    # 📚 Documentation (user-facing guides + developer references). Markdown
    # files and image assets are stored in the project repo under this path
    # so updates are tracked via version control.
    DOCS_DIR: str = os.getenv(
        "DOCS_DIR",
        "/home/fbinalex/NPI-IDBMS/docs",
    )
    # The assets sub-folder is mounted as a public static directory and
    # referenced from markdown via the URL prefix below.
    DOCS_ASSETS_SUBDIR: str = "assets"
    DOCS_ASSETS_URL_PREFIX: str = "/static/docs-assets"
    DOCS_ASSET_MAX_BYTES: int = int(
        os.getenv("DOCS_ASSET_MAX_BYTES", str(10 * 1024 * 1024))  # 10 MB
    )
    # Role required to edit documentation (create/update markdown pages and
    # manage assets). Defaults to "Admin"; override via env if needed.
    DOCS_EDIT_ROLE: str = os.getenv("DOCS_EDIT_ROLE", "Admin")

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache
def get_settings():
    return Settings()


settings = get_settings()