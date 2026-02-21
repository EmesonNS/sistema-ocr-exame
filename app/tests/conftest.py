import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base
from app.main import app
from app.core.database import get_db
from app.models.api_key import ApiKey
from app.core.auth import hash_api_key

# Database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database override"""

    from app.core.celery_app import celery_app

    original_send_task = celery_app.send_task
    celery_app.send_task = lambda *args, **kwargs: None

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        celery_app.send_task = original_send_task
    app.dependency_overrides.clear()


@pytest.fixture
def test_api_key(db_session) -> str:
    """Create a test API key and return the plain key"""
    plain_key = "test_key_12345678"
    hashed_key = hash_api_key(plain_key)

    api_key = ApiKey(
        key_hash=hashed_key,
        client_name="Test Client",
        is_active=True,
        rate_limit_per_minute=60,
    )
    db_session.add(api_key)
    db_session.commit()

    return plain_key


@pytest.fixture
def auth_headers(test_api_key) -> dict:
    """Return headers with valid API key"""
    return {"X-API-Key": test_api_key}


@pytest.fixture
def master_headers() -> dict:
    """Return headers with master key for admin operations"""
    from app.core.config import settings

    return {"X-Master-Key": settings.MASTER_API_KEY or "test_master_key"}
