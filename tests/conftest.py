"""Pytest configuration and fixtures for testing."""
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from typing import AsyncGenerator

from main import app
from config.database import Base, get_async_session
from config.settings import settings


# In-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    future=True,
)

# Create test session factory
test_async_session_maker = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest_asyncio.fixture
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Provide a clean database session for each test.

    Creates all tables before test, drops after test.
    Uses in-memory SQLite for fast testing.
    """
    # Create all tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Provide session
    async with test_async_session_maker() as session:
        yield session

    # Drop all tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def async_client(test_db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Provide an async HTTP client for API tests.

    Overrides get_async_session dependency to use test database.
    """
    async def override_get_async_session():
        yield test_db

    app.dependency_overrides[get_async_session] = override_get_async_session

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def sample_user_data():
    """Sample user data for tests."""
    return {
        "email": "test@example.com",
        "password": "SecurePassword123!",
        "full_name": "Test User",
        "phone": "+34612345678"
    }


@pytest.fixture
def sample_trip_data():
    """Sample trip data for tests."""
    return {
        "origin": "Madrid, Spain",
        "origin_lat": 40.4168,
        "origin_lng": -3.7038,
        "destination": "Barcelona, Spain",
        "destination_lat": 41.3851,
        "destination_lng": 2.1734,
        "departure_datetime": "2025-11-20T10:00:00",
        "available_seats": 3,
        "price_per_seat": 25.0,
        "preferences": {
            "smoking_allowed": False,
            "pets_allowed": False,
            "music_preferences": "No preference"
        }
    }


@pytest.fixture
def sample_booking_data():
    """Sample booking data for tests."""
    return {
        "seats_requested": 2,
        "pickup_location": "Madrid Centro",
        "pickup_lat": 40.4200,
        "pickup_lng": -3.7000,
        "notes": "I'll be waiting at the main entrance"
    }
