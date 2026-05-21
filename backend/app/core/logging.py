import logging
import sys

from app.core.config import settings


def setup_logging():
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


security_logger = logging.getLogger("app.security")
rbac_logger = logging.getLogger("app.rbac")
audit_logger = logging.getLogger("app.audit")