import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Integer, DateTime
from app.core.database import Base
from app.core.sa_types import GUID


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    key_hash = Column(String, nullable=False, unique=True, index=True)
    client_name = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    rate_limit_per_minute = Column(Integer, default=60)
    created_at = Column(DateTime, default=datetime.utcnow)
