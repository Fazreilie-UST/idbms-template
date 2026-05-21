from app.main import app
from app.core.config import settings

print("APP_OK routes=" + str(len(app.routes)))
print("MAX_REQUEST_BODY_BYTES=" + str(settings.MAX_REQUEST_BODY_BYTES))
print("middleware=" + str([m.cls.__name__ for m in app.user_middleware]))
