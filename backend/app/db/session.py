from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Pool sized so long-running bulk imports (build plan / shipping streams that
# hold a Session for the entire duration of one file) don't starve regular
# request traffic. `pool_pre_ping` ensures stale connections are recycled
# transparently after the DB or a load balancer drops them.
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=20,
    pool_recycle=1800,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)