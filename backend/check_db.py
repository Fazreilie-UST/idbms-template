from app.db.base import Base
import app.models
from sqlalchemy.orm import configure_mappers
configure_mappers()
print('OK', len(Base.metadata.tables), 'tables')
print('addresses' in Base.metadata.tables, 'build_plan_shippings' in Base.metadata.tables)
