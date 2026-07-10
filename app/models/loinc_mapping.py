import uuid

from sqlalchemy import Column, String

from app.core.database import Base
from app.core.sa_types import GUID


class LoincMapping(Base):
    __tablename__ = "loinc_mappings"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    keyword = Column(String(255), nullable=False, unique=True, index=True)
    loinc_code = Column(String(20), nullable=False, index=True)
    description = Column(String(255), nullable=True)
