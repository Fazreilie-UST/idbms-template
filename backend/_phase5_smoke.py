import os
os.environ.setdefault("SECRET_KEY", "test")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("FRONTEND_URL", "http://localhost")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
from app.main import app
print("APP_OK routes=" + str(len(app.routes)))
# sanity-check the cookie-name + csrf settings are present
from app.core.config import settings
print("ACCESS_COOKIE=" + settings.ACCESS_COOKIE_NAME)
print("CSRF_COOKIE=" + settings.CSRF_COOKIE_NAME)
print("CSRF_HEADER=" + settings.CSRF_HEADER_NAME)
