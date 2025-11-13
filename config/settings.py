"""Application configuration using Pydantic Settings."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    # Application
    APP_NAME: str = "Vibe Coding Carpooling API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # Database (SQLite)
    DATABASE_URL: str = "sqlite+aiosqlite:///./carpooling.db"
    # For testing: "sqlite+aiosqlite:///:memory:"
    # For specific path: "sqlite+aiosqlite:///./data/carpooling.db"

    # Authentication & Security
    SECRET_KEY: str = "your-secret-key-change-this-in-production-use-openssl-rand-hex-32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # External Services (optional for MVP)
    MAPS_API_KEY: Optional[str] = None
    MAPS_PROVIDER: str = "openstreetmap"  # openstreetmap, mapbox, google
    GEOCODING_API_KEY: Optional[str] = None

    # Matching Engine
    DEFAULT_MAX_DETOUR_MINUTES: int = 30
    DEFAULT_PROXIMITY_RADIUS_KM: float = 10.0

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8000"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )


# Global settings instance
settings = Settings()
