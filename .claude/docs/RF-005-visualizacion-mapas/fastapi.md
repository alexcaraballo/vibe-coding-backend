# FastAPI Implementation Plan: RF-005 - Map Visualization & Routing

**Status**: READY
**Version**: 1.0.0
**Last Updated**: 2025-11-13
**Related Docs**:
- Functional Requirements: `.claude/plans/06-RF-005-visualizacion-mapas.md`
- Issue: #5

---

## Summary

This implementation plan details the FastAPI service architecture for integrating external map services (OpenStreetMap, Mapbox, Google Maps) to provide geocoding and routing capabilities for the carpooling platform. The design follows Clean Architecture principles with a strong emphasis on provider abstraction, enabling seamless switching between map service providers.

The implementation uses **async SQLAlchemy** with SQLite3 for caching geocoding results, reducing external API calls and improving response times. The architecture separates domain logic (pure business rules) from infrastructure concerns (HTTP clients, database, external APIs), ensuring testability and maintainability.

**Core Features:**
- Geocoding (address → coordinates) with caching
- Reverse geocoding (coordinates → address)
- Route calculation with polyline, distance, and duration
- Multi-provider support (OpenStreetMap, Mapbox, Google Maps)
- Integration endpoint to get routes for existing trips
- Rate limiting and error handling for external API failures

---

## Architecture Mapping

### Domain → FastAPI Mapping

| Domain Concept | FastAPI Construct | Location | Notes |
|---------------|------------------|----------|-------|
| Coordinates ValueObject | Pydantic Model | `domain/models.py` | Immutable lat/lng pair with validation |
| Location ValueObject | Pydantic Model | `domain/models.py` | Named location with coordinates |
| Route Entity | Pydantic Model | `domain/models.py` | Complete route with polyline, distance, duration |
| IMapService Interface | Abstract Base Class | `domain/services/map_service.py` | Contract for all map providers |
| GeocodingCache Entity | SQLAlchemy Model | `infrastructure/persistence/models.py` | Cache table for geocoding results |
| OpenStreetMapService | Concrete Implementation | `infrastructure/external/osm_service.py` | Nominatim + OSRM implementation |
| MapboxService | Concrete Implementation | `infrastructure/external/mapbox_service.py` | Mapbox API implementation |
| GoogleMapsService | Concrete Implementation | `infrastructure/external/google_maps_service.py` | Google Maps API implementation |
| CachedMapService | Decorator/Wrapper | `infrastructure/services/cached_map_service.py` | Caching layer over any provider |
| GeocodeCacheRepository | Repository Pattern | `infrastructure/repositories/geocode_cache_repo.py` | DB operations for cache |
| Geocode Command | POST endpoint | `entrypoints/http/routers/maps.py` | `/api/v1/maps/geocode` |
| Route Calculation Command | POST endpoint | `entrypoints/http/routers/maps.py` | `/api/v1/maps/route` |
| Trip Route Query | GET endpoint | `entrypoints/http/routers/maps.py` | `/api/v1/maps/trip/{id}/route` |

### Layer Responsibilities

**Domain Layer** (`domain/`):
- Define value objects: `Coordinates`, `Location`, `Route`
- Define service interface: `IMapService` (abstract methods for geocode, reverse_geocode, get_route)
- Define domain exceptions: `GeocodingError`, `RoutingError`, `MapServiceUnavailable`
- NO framework dependencies, NO I/O operations, pure Python business logic

**Application Layer** (`application/`):
- Define use cases: `GeocodeAddressUseCase`, `CalculateRouteUseCase`, `GetTripRouteUseCase`
- Orchestrate domain services and repositories
- Handle application-level validation and error translation
- Transaction boundaries (if needed)

**Infrastructure/Adapters Layer** (`infrastructure/`):
- **Persistence**: SQLAlchemy models for `geocode_cache` table, repository implementations
- **External Services**: HTTP clients for OpenStreetMap, Mapbox, Google Maps
- **Caching**: Redis or in-memory cache adapters (optional enhancement)
- **Configuration**: Settings for API keys, timeouts, rate limits

**HTTP Entrypoints Layer** (`entrypoints/http/`):
- FastAPI routers with request/response models
- Dependency injection setup
- HTTP-specific error handling (exception handlers)
- Request validation using Pydantic
- OpenAPI documentation

### Dependency Flow

```
HTTP Entrypoints (FastAPI Router)
        ↓ depends on
Application Use Cases
        ↓ depends on
Domain Services (IMapService) + Repositories
        ↑ implemented by
Infrastructure Adapters (OSM, Mapbox, Google, Cache)
```

**Critical Rule**: Domain layer NEVER imports from infrastructure or HTTP layers. All dependencies point inward.

---

## File Actions

### Create New Files

#### Domain Layer

- **`apps/maps/domain/__init__.py`**
  - Package initialization

- **`apps/maps/domain/models.py`**
  - `Coordinates` - ValueObject with latitude/longitude validation
  - `Location` - ValueObject with name and coordinates
  - `Route` - Entity with origin, destination, distance_km, duration_minutes, polyline

- **`apps/maps/domain/services/__init__.py`**
  - Package initialization

- **`apps/maps/domain/services/map_service.py`**
  - `IMapService` - Abstract base class defining contract:
    - `async def geocode(address: str) -> Optional[Coordinates]`
    - `async def reverse_geocode(coordinates: Coordinates) -> Optional[str]`
    - `async def get_route(origin: Coordinates, destination: Coordinates) -> Optional[Route]`

- **`apps/maps/domain/exceptions.py`**
  - `MapServiceError` - Base exception
  - `GeocodingError` - Failed to geocode address
  - `RoutingError` - Failed to calculate route
  - `MapServiceUnavailableError` - External service unavailable
  - `RateLimitExceededError` - Rate limit hit

#### Application Layer

- **`apps/maps/application/__init__.py`**
  - Package initialization

- **`apps/maps/application/use_cases/__init__.py`**
  - Package initialization

- **`apps/maps/application/use_cases/geocode_address.py`**
  - `GeocodeAddressUseCase` class with `async def execute(address: str) -> Coordinates`
  - Handles caching logic and error translation

- **`apps/maps/application/use_cases/calculate_route.py`**
  - `CalculateRouteUseCase` class with `async def execute(origin, destination) -> Route`
  - Handles geocoding if needed, then route calculation

- **`apps/maps/application/use_cases/get_trip_route.py`**
  - `GetTripRouteUseCase` class with `async def execute(trip_id: str) -> Route`
  - Integrates with trip repository to fetch trip details
  - Updates trip with geocoded coordinates if missing

#### Infrastructure Layer - Persistence

- **`apps/maps/infrastructure/__init__.py`**
  - Package initialization

- **`apps/maps/infrastructure/persistence/__init__.py`**
  - Package initialization

- **`apps/maps/infrastructure/persistence/models.py`**
  - `GeocodeCacheModel` - SQLAlchemy model:
    - `id: int` (primary key)
    - `address: str` (unique index)
    - `latitude: float`
    - `longitude: float`
    - `provider: str` (which service provided the result)
    - `created_at: datetime`
    - `accessed_at: datetime` (for LRU cache eviction)

- **`apps/maps/infrastructure/repositories/__init__.py`**
  - Package initialization

- **`apps/maps/infrastructure/repositories/geocode_cache_repo.py`**
  - `IGeocodeCacheRepository` - Abstract interface
  - `SQLAlchemyGeocodeCacheRepository` - Async SQLAlchemy implementation:
    - `async def get_by_address(address: str) -> Optional[Coordinates]`
    - `async def save(address: str, coordinates: Coordinates, provider: str) -> None`
    - `async def update_accessed_at(address: str) -> None`
    - `async def evict_old_entries(days: int = 90) -> int`

#### Infrastructure Layer - External Services

- **`apps/maps/infrastructure/external/__init__.py`**
  - Package initialization

- **`apps/maps/infrastructure/external/base_http_client.py`**
  - `BaseHTTPClient` - Shared async HTTP client wrapper with:
    - Timeout configuration
    - Retry logic with exponential backoff
    - Rate limiting
    - Error handling

- **`apps/maps/infrastructure/external/osm_service.py`**
  - `OpenStreetMapService` - Implementation of `IMapService`:
    - Uses Nominatim for geocoding (https://nominatim.openstreetmap.org)
    - Uses OSRM for routing (https://router.project-osrm.org)
    - Respects rate limits (1 req/sec for Nominatim)
    - Includes required User-Agent header

- **`apps/maps/infrastructure/external/mapbox_service.py`**
  - `MapboxService` - Implementation of `IMapService`:
    - Uses Mapbox Geocoding API
    - Uses Mapbox Directions API
    - Requires API key from config

- **`apps/maps/infrastructure/external/google_maps_service.py`**
  - `GoogleMapsService` - Implementation of `IMapService`:
    - Uses Google Geocoding API
    - Uses Google Directions API
    - Requires API key from config

#### Infrastructure Layer - Caching & Services

- **`apps/maps/infrastructure/services/__init__.py`**
  - Package initialization

- **`apps/maps/infrastructure/services/cached_map_service.py`**
  - `CachedMapService` - Decorator implementing `IMapService`:
    - Wraps any `IMapService` implementation
    - Checks cache before calling external service
    - Saves results to cache
    - Updates access timestamps for LRU

- **`apps/maps/infrastructure/config.py`**
  - `MapSettings` - Pydantic BaseSettings:
    - `MAP_PROVIDER: str` - Default provider (osm, mapbox, google)
    - `MAPBOX_API_KEY: Optional[str]`
    - `GOOGLE_MAPS_API_KEY: Optional[str]`
    - `GEOCODING_CACHE_ENABLED: bool = True`
    - `GEOCODING_CACHE_TTL_DAYS: int = 90`
    - `OSM_RATE_LIMIT_PER_SECOND: float = 1.0`
    - `REQUEST_TIMEOUT_SECONDS: float = 10.0`

- **`apps/maps/infrastructure/dependencies.py`**
  - FastAPI dependency injection functions:
    - `async def get_db_session() -> AsyncSession` (yields session)
    - `async def get_geocode_cache_repository(session) -> IGeocodeCacheRepository`
    - `async def get_map_service(cache_repo, settings) -> IMapService`
      - Factory function to instantiate correct provider
      - Wraps with `CachedMapService` if caching enabled

#### HTTP Entrypoints Layer

- **`apps/maps/entrypoints/__init__.py`**
  - Package initialization

- **`apps/maps/entrypoints/http/__init__.py`**
  - Package initialization

- **`apps/maps/entrypoints/http/schemas/__init__.py`**
  - Package initialization

- **`apps/maps/entrypoints/http/schemas/requests.py`**
  - `GeocodeRequest` - Pydantic model with `address: str` validation
  - `RouteRequest` - Pydantic model with optional address or coordinate inputs
  - `ReverseGeocodeRequest` - Pydantic model with `latitude: float, longitude: float`

- **`apps/maps/entrypoints/http/schemas/responses.py`**
  - `CoordinatesResponse` - Based on `Coordinates` domain model
  - `LocationResponse` - Based on `Location` domain model
  - `RouteResponse` - Based on `Route` domain model
  - `ErrorResponse` - Standard error format

- **`apps/maps/entrypoints/http/routers/__init__.py`**
  - Package initialization

- **`apps/maps/entrypoints/http/routers/maps.py`**
  - FastAPI router with endpoints:
    - `POST /geocode` - Geocode an address
    - `POST /reverse-geocode` - Reverse geocode coordinates
    - `POST /route` - Calculate route between two points
    - `GET /trip/{trip_id}/route` - Get route for existing trip

- **`apps/maps/entrypoints/http/exception_handlers.py`**
  - Exception handlers mapping domain exceptions to HTTP responses:
    - `GeocodingError` → 404 Not Found
    - `RoutingError` → 500 Internal Server Error
    - `MapServiceUnavailableError` → 503 Service Unavailable
    - `RateLimitExceededError` → 429 Too Many Requests

#### Database Migrations

- **`alembic/versions/XXXX_add_geocode_cache_table.py`**
  - Migration to create `geocode_cache` table with indexes

#### Testing Files

- **`tests/unit/maps/domain/test_models.py`**
  - Unit tests for `Coordinates`, `Location`, `Route` validation

- **`tests/unit/maps/application/test_use_cases.py`**
  - Unit tests for use cases with mocked dependencies

- **`tests/unit/maps/infrastructure/test_osm_service.py`**
  - Unit tests for OpenStreetMap service with mocked HTTP

- **`tests/integration/maps/test_map_endpoints.py`**
  - Integration tests for API endpoints with test database

- **`tests/integration/maps/test_geocode_caching.py`**
  - Integration tests verifying cache behavior

- **`tests/fixtures/maps/__init__.py`**
  - Test fixtures for map services, mock responses

### Modify Existing Files

- **`main.py`**
  - Import and include maps router: `app.include_router(maps_router, prefix="/api/v1/maps", tags=["Maps"])`
  - Register exception handlers from `apps.maps.entrypoints.http.exception_handlers`

- **`config/settings.py`** (if exists)
  - Include `MapSettings` configuration

- **`apps/trips/domain/models.py`** (if not already present)
  - Add optional fields to Trip model:
    - `origin_lat: Optional[float]`
    - `origin_lng: Optional[float]`
    - `destination_lat: Optional[float]`
    - `destination_lng: Optional[float]`

- **`alembic/env.py`**
  - Import `GeocodeCacheModel` to ensure metadata is registered

---

## API Endpoints

| Method | Path | Request Model | Response Model | Use Case | Auth | Notes |
|--------|------|--------------|----------------|----------|------|-------|
| POST | `/api/v1/maps/geocode` | `GeocodeRequest` | `CoordinatesResponse` | Geocode address to coordinates | None | Cached |
| POST | `/api/v1/maps/reverse-geocode` | `ReverseGeocodeRequest` | `LocationResponse` | Coordinates to address | None | Not cached |
| POST | `/api/v1/maps/route` | `RouteRequest` | `RouteResponse` | Calculate route with polyline | None | Not cached |
| GET | `/api/v1/maps/trip/{trip_id}/route` | Path param | `RouteResponse` | Get route for existing trip | Optional | Updates trip coords |

### Endpoint Details

#### POST `/api/v1/maps/geocode`

**Purpose**: Convert a text address to geographic coordinates (latitude, longitude).

**Request Body**:
```json
{
  "address": "Cádiz, España"
}
```

**Response** (200 OK):
```json
{
  "latitude": 36.5271,
  "longitude": -6.2886
}
```

**Error Responses**:
- `404 Not Found` - Address not found by geocoding service
- `503 Service Unavailable` - External map service is down
- `429 Too Many Requests` - Rate limit exceeded

**Implementation Notes**:
- Check cache first (database lookup)
- If cache miss, call external service via `IMapService.geocode()`
- Save result to cache on success
- Update `accessed_at` timestamp on cache hit

---

#### POST `/api/v1/maps/reverse-geocode`

**Purpose**: Convert coordinates to a human-readable address.

**Request Body**:
```json
{
  "latitude": 36.5271,
  "longitude": -6.2886
}
```

**Response** (200 OK):
```json
{
  "name": "Cádiz, Andalucía, España",
  "coordinates": {
    "latitude": 36.5271,
    "longitude": -6.2886
  }
}
```

**Error Responses**:
- `404 Not Found` - Coordinates not found or invalid location
- `503 Service Unavailable` - External map service is down

**Implementation Notes**:
- NOT cached (reverse geocoding results vary by zoom level and can change)
- Call `IMapService.reverse_geocode()` directly

---

#### POST `/api/v1/maps/route`

**Purpose**: Calculate a route between two points with distance, duration, and polyline.

**Request Body** (Option 1 - Addresses):
```json
{
  "origin_address": "Cádiz, España",
  "destination_address": "Sevilla, España"
}
```

**Request Body** (Option 2 - Coordinates):
```json
{
  "origin_lat": 36.5271,
  "origin_lng": -6.2886,
  "destination_lat": 37.3891,
  "destination_lng": -5.9845
}
```

**Response** (200 OK):
```json
{
  "origin": {
    "name": "Cádiz, España",
    "coordinates": {
      "latitude": 36.5271,
      "longitude": -6.2886
    }
  },
  "destination": {
    "name": "Sevilla, España",
    "coordinates": {
      "latitude": 37.3891,
      "longitude": -5.9845
    }
  },
  "distance_km": 125.5,
  "duration_minutes": 90,
  "polyline": [
    {"latitude": 36.5271, "longitude": -6.2886},
    {"latitude": 36.5280, "longitude": -6.2900},
    ...
    {"latitude": 37.3891, "longitude": -5.9845}
  ]
}
```

**Validation Rules**:
- Must provide EITHER addresses OR coordinates for both origin and destination
- Cannot mix and match (e.g., origin_address with destination_lat)

**Error Responses**:
- `400 Bad Request` - Missing or invalid input combination
- `404 Not Found` - Address geocoding failed
- `500 Internal Server Error` - Route calculation failed
- `503 Service Unavailable` - External map service is down

**Implementation Notes**:
- If addresses provided, geocode them first (with caching)
- Call `IMapService.get_route()` with coordinates
- Polyline format: array of coordinate objects (not encoded string)

---

#### GET `/api/v1/maps/trip/{trip_id}/route`

**Purpose**: Get the route for an existing trip by its ID. Integrates with the trips module.

**Path Parameters**:
- `trip_id`: UUID or MongoDB ObjectId of the trip

**Response** (200 OK):
```json
{
  "origin": {
    "name": "Cádiz, España",
    "coordinates": {
      "latitude": 36.5271,
      "longitude": -6.2886
    }
  },
  "destination": {
    "name": "Sevilla, España",
    "coordinates": {
      "latitude": 37.3891,
      "longitude": -5.9845
    }
  },
  "distance_km": 125.5,
  "duration_minutes": 90,
  "polyline": [...]
}
```

**Error Responses**:
- `404 Not Found` - Trip not found OR geocoding failed
- `500 Internal Server Error` - Route calculation failed

**Implementation Notes**:
- Fetch trip from `ITripRepository.get_by_id()`
- Check if trip already has `origin_lat/lng` and `destination_lat/lng`
- If coordinates missing:
  - Geocode `trip.origin` and `trip.destination` addresses
  - Update trip with coordinates via `ITripRepository.update()`
- Calculate route using coordinates
- This endpoint is the PRIMARY integration point with the trips feature

---

## Dependencies

### Required Python Packages

```toml
[tool.poetry.dependencies]
# Core Framework
python = "^3.11"
fastapi = "^0.104.0"
uvicorn = {extras = ["standard"], version = "^0.24.0"}
pydantic = "^2.5.0"
pydantic-settings = "^2.1.0"

# Async Database
sqlalchemy = {extras = ["asyncio"], version = "^2.0.23"}
aiosqlite = "^0.19.0"  # Async SQLite driver
alembic = "^1.12.1"

# HTTP Client
httpx = "^0.25.0"  # Async HTTP client for external APIs

# Optional: Redis for caching (future enhancement)
# redis = {extras = ["hiredis"], version = "^5.0.0"}
# aioredis = "^2.0.1"

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.0"
pytest-asyncio = "^0.21.0"
pytest-cov = "^4.1.0"
httpx = "^0.25.0"  # For testing HTTP endpoints
respx = "^0.20.2"  # Mock httpx requests in tests
faker = "^20.0.0"  # Generate test data
```

### Dependency Injection Hierarchy

```
FastAPI Router Handler
    ↓ Depends
GetTripRouteUseCase
    ↓ Depends
[IMapService, ITripRepository, AsyncSession]
    ↓ Depends
CachedMapService (wraps provider)
    ↓ Depends
[OpenStreetMapService, GeocodeCacheRepository]
    ↓ Depends
[AsyncSession, MapSettings]
```

**Dependency Injection Setup** (in `infrastructure/dependencies.py`):

```python
from functools import lru_cache
from typing import AsyncGenerator
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from apps.maps.domain.services.map_service import IMapService
from apps.maps.infrastructure.config import MapSettings
from apps.maps.infrastructure.external.osm_service import OpenStreetMapService
from apps.maps.infrastructure.external.mapbox_service import MapboxService
from apps.maps.infrastructure.external.google_maps_service import GoogleMapsService
from apps.maps.infrastructure.services.cached_map_service import CachedMapService
from apps.maps.infrastructure.repositories.geocode_cache_repo import (
    IGeocodeCacheRepository,
    SQLAlchemyGeocodeCacheRepository
)

# Database setup
DATABASE_URL = "sqlite+aiosqlite:///./app.db"
engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide database session."""
    async with AsyncSessionLocal() as session:
        yield session

@lru_cache
def get_settings() -> MapSettings:
    """Cached settings instance."""
    return MapSettings()

async def get_geocode_cache_repository(
    session: AsyncSession = Depends(get_db_session)
) -> IGeocodeCacheRepository:
    """Provide geocoding cache repository."""
    return SQLAlchemyGeocodeCacheRepository(session)

async def get_map_service(
    cache_repo: IGeocodeCacheRepository = Depends(get_geocode_cache_repository),
    settings: MapSettings = Depends(get_settings)
) -> IMapService:
    """
    Factory function to provide map service with correct provider.

    Wraps the provider with caching if enabled in settings.
    """
    # Instantiate base provider
    provider_map = {
        "osm": OpenStreetMapService,
        "mapbox": MapboxService,
        "google": GoogleMapsService,
    }

    provider_class = provider_map.get(settings.MAP_PROVIDER, OpenStreetMapService)
    base_service = provider_class(settings)

    # Wrap with caching if enabled
    if settings.GEOCODING_CACHE_ENABLED:
        return CachedMapService(base_service, cache_repo, settings)
    else:
        return base_service
```

---

## Data Persistence

### Repository Interfaces

**`IGeocodeCacheRepository`** (Abstract Interface):

```python
from abc import ABC, abstractmethod
from typing import Optional
from datetime import datetime
from apps.maps.domain.models import Coordinates

class IGeocodeCacheRepository(ABC):
    """Repository for geocoding cache operations."""

    @abstractmethod
    async def get_by_address(self, address: str) -> Optional[Coordinates]:
        """Retrieve cached coordinates for an address."""
        pass

    @abstractmethod
    async def save(
        self,
        address: str,
        coordinates: Coordinates,
        provider: str
    ) -> None:
        """Save geocoding result to cache."""
        pass

    @abstractmethod
    async def update_accessed_at(self, address: str) -> None:
        """Update the last accessed timestamp for cache entry."""
        pass

    @abstractmethod
    async def evict_old_entries(self, days: int = 90) -> int:
        """Remove cache entries older than specified days. Returns count."""
        pass
```

### SQLAlchemy Models

**`GeocodeCacheModel`** (in `infrastructure/persistence/models.py`):

```python
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Index
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class GeocodeCacheModel(Base):
    """
    Cache table for geocoding results to reduce external API calls.

    Indexes:
    - address (unique): Fast lookup by address string
    - accessed_at: Support for LRU eviction policies
    """
    __tablename__ = "geocode_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    address = Column(String(500), nullable=False, unique=True, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    provider = Column(String(50), nullable=False)  # osm, mapbox, google
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    accessed_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index('ix_geocode_cache_accessed_at', 'accessed_at'),
    )
```

### Migration Strategy

**Alembic Migration** (auto-generated with manual review):

```bash
# Generate migration
alembic revision --autogenerate -m "Add geocode_cache table"

# Review the generated migration file
# Ensure indexes are created correctly

# Apply migration
alembic upgrade head
```

**Migration File Template**:

```python
"""Add geocode_cache table

Revision ID: xxxxxxxxxxxx
Revises:
Create Date: 2025-11-13
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'geocode_cache',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('address', sa.String(length=500), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('accessed_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_geocode_cache_address', 'geocode_cache', ['address'], unique=True)
    op.create_index('ix_geocode_cache_accessed_at', 'geocode_cache', ['accessed_at'], unique=False)

def downgrade():
    op.drop_index('ix_geocode_cache_accessed_at', table_name='geocode_cache')
    op.drop_index('ix_geocode_cache_address', table_name='geocode_cache')
    op.drop_table('geocode_cache')
```

---

## Background Tasks

### Event Processing

**Not applicable for this feature.** Map services are synchronous request-response operations. No background task processing is required initially.

**Future Enhancement**: Consider background tasks for:
- Periodic cache eviction (clean up old entries)
- Pre-warming cache for popular routes
- Batch geocoding for newly created trips

### Task Queue Integration

**Not planned for MVP.** If implementing background tasks in the future, use:
- **Celery** with Redis as broker for distributed task processing
- **FastAPI BackgroundTasks** for lightweight async operations
- **APScheduler** for periodic maintenance tasks

---

## Error Handling

### Domain Error Mapping

| Domain Error | HTTP Status | Response Format | Retry? |
|--------------|-------------|----------------|--------|
| `GeocodingError` | 404 Not Found | `{"detail": "Address not found: {address}"}` | No |
| `RoutingError` | 500 Internal Server Error | `{"detail": "Unable to calculate route"}` | Yes (may be transient) |
| `MapServiceUnavailableError` | 503 Service Unavailable | `{"detail": "Map service temporarily unavailable"}` | Yes (exponential backoff) |
| `RateLimitExceededError` | 429 Too Many Requests | `{"detail": "Rate limit exceeded, please retry later", "retry_after": 60}` | Yes (after delay) |
| `InvalidCoordinatesError` | 400 Bad Request | `{"detail": "Invalid coordinates: lat={lat}, lng={lng}"}` | No |

### Exception Handlers

**File**: `entrypoints/http/exception_handlers.py`

```python
from fastapi import Request, status
from fastapi.responses import JSONResponse
from apps.maps.domain.exceptions import (
    GeocodingError,
    RoutingError,
    MapServiceUnavailableError,
    RateLimitExceededError,
    InvalidCoordinatesError
)

async def geocoding_error_handler(request: Request, exc: GeocodingError):
    """Handle geocoding failures as 404."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": str(exc)}
    )

async def routing_error_handler(request: Request, exc: RoutingError):
    """Handle routing failures as 500."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Unable to calculate route. Please try again."}
    )

async def map_service_unavailable_handler(request: Request, exc: MapServiceUnavailableError):
    """Handle external service downtime as 503."""
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "detail": "Map service temporarily unavailable. Please retry.",
            "service": exc.service_name if hasattr(exc, 'service_name') else "unknown"
        },
        headers={"Retry-After": "60"}
    )

async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceededError):
    """Handle rate limiting as 429."""
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "detail": "Rate limit exceeded. Please wait before retrying.",
            "retry_after": exc.retry_after if hasattr(exc, 'retry_after') else 60
        },
        headers={"Retry-After": str(exc.retry_after if hasattr(exc, 'retry_after') else 60)}
    )

async def invalid_coordinates_handler(request: Request, exc: InvalidCoordinatesError):
    """Handle invalid coordinates as 400."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)}
    )

# Register in main.py:
# from apps.maps.entrypoints.http.exception_handlers import *
#
# app.add_exception_handler(GeocodingError, geocoding_error_handler)
# app.add_exception_handler(RoutingError, routing_error_handler)
# app.add_exception_handler(MapServiceUnavailableError, map_service_unavailable_handler)
# app.add_exception_handler(RateLimitExceededError, rate_limit_exceeded_handler)
# app.add_exception_handler(InvalidCoordinatesError, invalid_coordinates_handler)
```

### Retry Logic

**Base HTTP Client** (in `infrastructure/external/base_http_client.py`):

```python
import asyncio
import httpx
from typing import Optional
from apps.maps.domain.exceptions import MapServiceUnavailableError, RateLimitExceededError

class BaseHTTPClient:
    """
    Shared HTTP client with retry logic and error handling.

    Features:
    - Exponential backoff for transient failures
    - Rate limiting respect (429 responses)
    - Timeout configuration
    - Connection pooling
    """

    def __init__(
        self,
        timeout: float = 10.0,
        max_retries: int = 3,
        base_delay: float = 1.0
    ):
        self.timeout = timeout
        self.max_retries = max_retries
        self.base_delay = base_delay

    async def get(
        self,
        url: str,
        params: Optional[dict] = None,
        headers: Optional[dict] = None
    ) -> httpx.Response:
        """
        GET request with retry logic.

        Raises:
            MapServiceUnavailableError: After max retries exhausted
            RateLimitExceededError: If rate limit hit and no retry-after
        """
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(url, params=params, headers=headers)

                    # Handle rate limiting
                    if response.status_code == 429:
                        retry_after = int(response.headers.get('Retry-After', 60))
                        if attempt < self.max_retries - 1:
                            await asyncio.sleep(retry_after)
                            continue
                        else:
                            raise RateLimitExceededError(retry_after=retry_after)

                    # Raise for other HTTP errors
                    response.raise_for_status()
                    return response

            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500 and attempt < self.max_retries - 1:
                    # Exponential backoff for server errors
                    delay = self.base_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise MapServiceUnavailableError(f"HTTP {e.response.status_code}: {e.response.text}")

            except (httpx.ConnectError, httpx.TimeoutException) as e:
                if attempt < self.max_retries - 1:
                    delay = self.base_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise MapServiceUnavailableError(f"Connection failed: {str(e)}")

        raise MapServiceUnavailableError("Max retries exceeded")
```

---

## Caching Strategy

### Cache Architecture

**Two-Tier Caching Approach**:

1. **Database Cache (SQLite)** - Persistent, long-lived cache
   - Store geocoding results indefinitely (with TTL-based eviction)
   - Survives application restarts
   - Shared across all instances (if using shared SQLite file)
   - Handles cache invalidation via `accessed_at` timestamps

2. **In-Memory Cache (Optional Future Enhancement)** - Fast, short-lived cache
   - Redis or application-level dict cache
   - Cache routing results (which change less frequently than geocoding)
   - TTL: 1 hour for route polylines
   - Requires cache key generation: `f"route:{origin_lat},{origin_lng}:{dest_lat},{dest_lng}"`

### Caching Flow

```
┌─────────────────────┐
│  Geocode Request    │
└──────────┬──────────┘
           │
           ▼
    ┌──────────────┐
    │ Check SQLite │◄──── Cache Hit
    │    Cache     │      (return cached)
    └──────┬───────┘
           │ Cache Miss
           ▼
   ┌────────────────┐
   │ Call External  │
   │  Map Service   │
   └────────┬───────┘
            │
            ▼
    ┌──────────────┐
    │ Save to Cache│
    │ (SQLite)     │
    └──────────────┘
```

### Cache Implementation

**`CachedMapService`** (Decorator Pattern):

```python
from typing import Optional
from apps.maps.domain.models import Coordinates, Route
from apps.maps.domain.services.map_service import IMapService
from apps.maps.infrastructure.repositories.geocode_cache_repo import IGeocodeCacheRepository
from apps.maps.infrastructure.config import MapSettings

class CachedMapService(IMapService):
    """
    Decorator that adds caching to any IMapService implementation.

    Caching Strategy:
    - Geocoding: Cache hits avoid external API calls entirely
    - Reverse Geocoding: NOT cached (varies by zoom/precision)
    - Routing: NOT cached (too many permutations, would need route simplification)
    """

    def __init__(
        self,
        wrapped_service: IMapService,
        cache_repo: IGeocodeCacheRepository,
        settings: MapSettings
    ):
        self.wrapped = wrapped_service
        self.cache_repo = cache_repo
        self.settings = settings

    async def geocode(self, address: str) -> Optional[Coordinates]:
        """
        Geocode with caching.

        Flow:
        1. Normalize address (lowercase, strip)
        2. Check cache
        3. If hit: update accessed_at, return cached
        4. If miss: call wrapped service, save to cache, return result
        """
        # Normalize address for consistent cache keys
        normalized_address = address.strip().lower()

        # Check cache
        cached_coords = await self.cache_repo.get_by_address(normalized_address)
        if cached_coords:
            # Update access timestamp for LRU
            await self.cache_repo.update_accessed_at(normalized_address)
            return cached_coords

        # Cache miss - call external service
        coords = await self.wrapped.geocode(address)

        # Save to cache if successful
        if coords:
            provider = self.wrapped.__class__.__name__  # e.g., "OpenStreetMapService"
            await self.cache_repo.save(normalized_address, coords, provider)

        return coords

    async def reverse_geocode(self, coordinates: Coordinates) -> Optional[str]:
        """
        Reverse geocoding - NOT cached.

        Rationale: Results depend on zoom level and can change over time
        as map data is updated. Caching would provide stale data.
        """
        return await self.wrapped.reverse_geocode(coordinates)

    async def get_route(
        self,
        origin: Coordinates,
        destination: Coordinates
    ) -> Optional[Route]:
        """
        Route calculation - NOT cached in MVP.

        Future Enhancement: Cache with composite key
        (origin_lat, origin_lng, dest_lat, dest_lng) rounded to 3 decimals
        for ~100m precision. TTL: 1 hour.
        """
        return await self.wrapped.get_route(origin, destination)
```

### Cache Eviction

**Periodic Cleanup Task** (optional background job):

```python
# In a scheduled task or startup event
async def cleanup_old_cache_entries():
    """Remove cache entries not accessed in 90 days."""
    async with AsyncSessionLocal() as session:
        repo = SQLAlchemyGeocodeCacheRepository(session)
        deleted_count = await repo.evict_old_entries(days=90)
        print(f"Evicted {deleted_count} old geocoding cache entries")
```

### Cache Performance Metrics

**Expected Performance**:
- Cache hit rate: 70-80% for geocoding (addresses are frequently reused)
- Response time:
  - Cache hit: <10ms (SQLite lookup)
  - Cache miss: 200-500ms (external API + SQLite insert)
- Storage: ~100 bytes per cache entry (address + coordinates + metadata)

**Monitoring**:
- Log cache hit/miss rates
- Alert if cache hit rate drops below 50%
- Track external API call counts

---

## Configuration Management

### Environment Variables

**File**: `.env` (not committed to git)

```bash
# Map Service Provider (osm, mapbox, google)
MAP_PROVIDER=osm

# API Keys (only needed for paid providers)
MAPBOX_API_KEY=pk.your-mapbox-key-here
GOOGLE_MAPS_API_KEY=your-google-maps-key-here

# Caching Configuration
GEOCODING_CACHE_ENABLED=true
GEOCODING_CACHE_TTL_DAYS=90

# Rate Limiting
OSM_RATE_LIMIT_PER_SECOND=1.0
REQUEST_TIMEOUT_SECONDS=10.0
HTTP_MAX_RETRIES=3

# Database
DATABASE_URL=sqlite+aiosqlite:///./app.db
```

### Settings Class

**File**: `infrastructure/config.py`

```python
from pydantic_settings import BaseSettings
from typing import Optional

class MapSettings(BaseSettings):
    """
    Configuration for map services.

    Loaded from environment variables with validation.
    """
    # Provider Selection
    MAP_PROVIDER: str = "osm"  # osm, mapbox, google

    # API Keys (optional, provider-dependent)
    MAPBOX_API_KEY: Optional[str] = None
    GOOGLE_MAPS_API_KEY: Optional[str] = None

    # Caching
    GEOCODING_CACHE_ENABLED: bool = True
    GEOCODING_CACHE_TTL_DAYS: int = 90

    # Rate Limiting & Timeouts
    OSM_RATE_LIMIT_PER_SECOND: float = 1.0
    REQUEST_TIMEOUT_SECONDS: float = 10.0
    HTTP_MAX_RETRIES: int = 3

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./app.db"

    class Config:
        env_file = ".env"
        case_sensitive = False

    def validate_provider_config(self) -> None:
        """Validate that required API keys are present for selected provider."""
        if self.MAP_PROVIDER == "mapbox" and not self.MAPBOX_API_KEY:
            raise ValueError("MAPBOX_API_KEY required when MAP_PROVIDER=mapbox")
        if self.MAP_PROVIDER == "google" and not self.GOOGLE_MAPS_API_KEY:
            raise ValueError("GOOGLE_MAPS_API_KEY required when MAP_PROVIDER=google")

# Usage:
# settings = MapSettings()
# settings.validate_provider_config()
```

---

## Testing Strategy

### Test Pyramid

```
       ┌─────────────────┐
       │   E2E Tests     │  (Optional - full system)
       │   (Playwright)  │
       └────────┬────────┘
              ┌─┴──────────────────┐
              │ Integration Tests  │  (API endpoints with test DB)
              │   (pytest + httpx) │
              └────────┬───────────┘
                     ┌─┴────────────────────┐
                     │    Unit Tests        │  (Domain, Services, Repos)
                     │    (pytest)          │
                     └──────────────────────┘
```

### Unit Tests

**Domain Models** (`tests/unit/maps/domain/test_models.py`):

```python
import pytest
from pydantic import ValidationError
from apps.maps.domain.models import Coordinates, Location, Route

class TestCoordinates:
    def test_valid_coordinates(self):
        coords = Coordinates(latitude=36.5271, longitude=-6.2886)
        assert coords.latitude == 36.5271
        assert coords.longitude == -6.2886

    def test_latitude_out_of_range(self):
        with pytest.raises(ValidationError):
            Coordinates(latitude=91.0, longitude=0.0)  # >90

    def test_longitude_out_of_range(self):
        with pytest.raises(ValidationError):
            Coordinates(latitude=0.0, longitude=181.0)  # >180

class TestRoute:
    def test_route_without_polyline(self):
        """Route can be created without polyline (simplified response)."""
        route = Route(
            origin=Location(name="A", coordinates=Coordinates(latitude=0, longitude=0)),
            destination=Location(name="B", coordinates=Coordinates(latitude=1, longitude=1)),
            distance_km=100.0,
            duration_minutes=60
        )
        assert route.polyline is None
```

**Use Cases** (`tests/unit/maps/application/test_use_cases.py`):

```python
import pytest
from unittest.mock import AsyncMock, Mock
from apps.maps.application.use_cases.geocode_address import GeocodeAddressUseCase
from apps.maps.domain.models import Coordinates
from apps.maps.domain.exceptions import GeocodingError

@pytest.mark.asyncio
async def test_geocode_address_success():
    """Use case successfully geocodes address."""
    # Arrange
    mock_service = AsyncMock()
    mock_service.geocode.return_value = Coordinates(latitude=36.5, longitude=-6.2)
    use_case = GeocodeAddressUseCase(map_service=mock_service)

    # Act
    result = await use_case.execute("Cádiz, España")

    # Assert
    assert result.latitude == 36.5
    assert result.longitude == -6.2
    mock_service.geocode.assert_called_once_with("Cádiz, España")

@pytest.mark.asyncio
async def test_geocode_address_not_found():
    """Use case raises GeocodingError when address not found."""
    # Arrange
    mock_service = AsyncMock()
    mock_service.geocode.return_value = None  # Address not found
    use_case = GeocodeAddressUseCase(map_service=mock_service)

    # Act & Assert
    with pytest.raises(GeocodingError):
        await use_case.execute("NonexistentPlace12345")
```

**External Services** (`tests/unit/maps/infrastructure/test_osm_service.py`):

```python
import pytest
import respx
import httpx
from apps.maps.infrastructure.external.osm_service import OpenStreetMapService
from apps.maps.domain.models import Coordinates

@pytest.mark.asyncio
@respx.mock
async def test_osm_geocode_success():
    """OpenStreetMapService geocodes address successfully."""
    # Mock Nominatim API response
    respx.get("https://nominatim.openstreetmap.org/search").mock(
        return_value=httpx.Response(
            200,
            json=[{
                "lat": "36.5271",
                "lon": "-6.2886",
                "display_name": "Cádiz, España"
            }]
        )
    )

    # Act
    service = OpenStreetMapService()
    result = await service.geocode("Cádiz, España")

    # Assert
    assert result is not None
    assert result.latitude == 36.5271
    assert result.longitude == -6.2886

@pytest.mark.asyncio
@respx.mock
async def test_osm_geocode_not_found():
    """OpenStreetMapService returns None for unknown address."""
    respx.get("https://nominatim.openstreetmap.org/search").mock(
        return_value=httpx.Response(200, json=[])  # Empty results
    )

    service = OpenStreetMapService()
    result = await service.geocode("NonexistentPlace12345")

    assert result is None
```

### Integration Tests

**API Endpoints** (`tests/integration/maps/test_map_endpoints.py`):

```python
import pytest
from httpx import AsyncClient
from fastapi import status
from main import app

@pytest.mark.asyncio
async def test_geocode_endpoint_success():
    """POST /api/v1/maps/geocode returns coordinates."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/maps/geocode",
            json={"address": "Cádiz, España"}
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "latitude" in data
    assert "longitude" in data
    assert isinstance(data["latitude"], float)
    assert isinstance(data["longitude"], float)

@pytest.mark.asyncio
async def test_route_endpoint_with_addresses():
    """POST /api/v1/maps/route calculates route from addresses."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/maps/route",
            json={
                "origin_address": "Cádiz, España",
                "destination_address": "Sevilla, España"
            }
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "origin" in data
    assert "destination" in data
    assert "distance_km" in data
    assert "duration_minutes" in data
    assert "polyline" in data
    assert data["distance_km"] > 0
    assert len(data["polyline"]) > 0

@pytest.mark.asyncio
async def test_route_endpoint_with_coordinates():
    """POST /api/v1/maps/route works with coordinates."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/maps/route",
            json={
                "origin_lat": 36.5271,
                "origin_lng": -6.2886,
                "destination_lat": 37.3891,
                "destination_lng": -5.9845
            }
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["distance_km"] > 100  # Roughly 125km between cities

@pytest.mark.asyncio
async def test_route_endpoint_invalid_input():
    """POST /api/v1/maps/route validates input."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/maps/route",
            json={}  # Missing all required fields
        )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
```

**Cache Behavior** (`tests/integration/maps/test_geocode_caching.py`):

```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from apps.maps.infrastructure.repositories.geocode_cache_repo import SQLAlchemyGeocodeCacheRepository
from apps.maps.domain.models import Coordinates

@pytest.mark.asyncio
async def test_cache_saves_geocoding_result(db_session: AsyncSession):
    """Cache repository saves geocoding result."""
    repo = SQLAlchemyGeocodeCacheRepository(db_session)

    coords = Coordinates(latitude=36.5, longitude=-6.2)
    await repo.save("cadiz, españa", coords, "osm")

    # Retrieve from cache
    cached = await repo.get_by_address("cadiz, españa")
    assert cached is not None
    assert cached.latitude == 36.5
    assert cached.longitude == -6.2

@pytest.mark.asyncio
async def test_cache_hit_updates_accessed_at(db_session: AsyncSession):
    """Cache hit updates accessed_at timestamp."""
    repo = SQLAlchemyGeocodeCacheRepository(db_session)

    # Save initial entry
    coords = Coordinates(latitude=36.5, longitude=-6.2)
    await repo.save("test address", coords, "osm")

    # Get initial accessed_at
    initial_entry = await db_session.execute(
        "SELECT accessed_at FROM geocode_cache WHERE address = 'test address'"
    )
    initial_time = initial_entry.scalar()

    # Simulate cache hit
    await repo.update_accessed_at("test address")

    # Get updated accessed_at
    updated_entry = await db_session.execute(
        "SELECT accessed_at FROM geocode_cache WHERE address = 'test address'"
    )
    updated_time = updated_entry.scalar()

    assert updated_time > initial_time

@pytest.mark.asyncio
async def test_cache_eviction(db_session: AsyncSession):
    """Cache evicts old entries."""
    repo = SQLAlchemyGeocodeCacheRepository(db_session)

    # Create old entry (manually set accessed_at to 100 days ago)
    # ... implementation depends on database manipulation

    deleted_count = await repo.evict_old_entries(days=90)
    assert deleted_count > 0
```

### Contract Tests

**OpenAPI Schema Validation** (`tests/contract/test_api_schema.py`):

```python
import pytest
from httpx import AsyncClient
from main import app

@pytest.mark.asyncio
async def test_openapi_schema_available():
    """OpenAPI schema is accessible."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()

    # Verify map endpoints are documented
    assert "/api/v1/maps/geocode" in schema["paths"]
    assert "/api/v1/maps/route" in schema["paths"]
    assert "/api/v1/maps/trip/{trip_id}/route" in schema["paths"]

@pytest.mark.asyncio
async def test_response_matches_schema():
    """Actual responses match declared schema."""
    # Use OpenAPI schema to validate responses
    # Tool: schemathesis or openapi-spec-validator
    pass
```

### Test Fixtures

**File**: `tests/fixtures/maps.py`

```python
import pytest
from unittest.mock import AsyncMock
from apps.maps.domain.models import Coordinates, Location, Route
from apps.maps.domain.services.map_service import IMapService

@pytest.fixture
def mock_coordinates() -> Coordinates:
    """Sample coordinates (Cádiz)."""
    return Coordinates(latitude=36.5271, longitude=-6.2886)

@pytest.fixture
def mock_location(mock_coordinates) -> Location:
    """Sample location."""
    return Location(name="Cádiz, España", coordinates=mock_coordinates)

@pytest.fixture
def mock_route() -> Route:
    """Sample route."""
    origin = Location(
        name="Cádiz",
        coordinates=Coordinates(latitude=36.5271, longitude=-6.2886)
    )
    destination = Location(
        name="Sevilla",
        coordinates=Coordinates(latitude=37.3891, longitude=-5.9845)
    )
    return Route(
        origin=origin,
        destination=destination,
        distance_km=125.5,
        duration_minutes=90,
        polyline=[
            Coordinates(latitude=36.5271, longitude=-6.2886),
            Coordinates(latitude=36.6, longitude=-6.3),
            Coordinates(latitude=37.3891, longitude=-5.9845)
        ]
    )

@pytest.fixture
def mock_map_service() -> IMapService:
    """Mock map service for testing."""
    service = AsyncMock(spec=IMapService)
    service.geocode.return_value = Coordinates(latitude=36.5, longitude=-6.2)
    service.reverse_geocode.return_value = "Cádiz, España"
    service.get_route.return_value = Route(
        origin=Location(name="Origin", coordinates=Coordinates(0, 0)),
        destination=Location(name="Destination", coordinates=Coordinates(1, 1)),
        distance_km=100.0,
        duration_minutes=60
    )
    return service
```

### Test Coverage Requirements

**Minimum Coverage Targets**:
- Domain layer: 100% (pure logic, no I/O)
- Application use cases: 95%
- Infrastructure adapters: 80% (external dependencies harder to test)
- HTTP endpoints: 90%

**Coverage Report**:
```bash
pytest --cov=apps/maps --cov-report=html --cov-report=term
```

---

## Observability

### Logging

**Structured Logging Strategy**:

```python
import logging
import json
from datetime import datetime

# Configure structured JSON logging
class StructuredLogger:
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)

    def log_geocode_request(self, address: str, cached: bool):
        """Log geocoding request."""
        self.logger.info(json.dumps({
            "event": "geocode_request",
            "address": address,
            "cached": cached,
            "timestamp": datetime.utcnow().isoformat()
        }))

    def log_geocode_error(self, address: str, error: str):
        """Log geocoding error."""
        self.logger.error(json.dumps({
            "event": "geocode_error",
            "address": address,
            "error": error,
            "timestamp": datetime.utcnow().isoformat()
        }))

    def log_route_calculation(
        self,
        origin: str,
        destination: str,
        duration_ms: float
    ):
        """Log route calculation."""
        self.logger.info(json.dumps({
            "event": "route_calculation",
            "origin": origin,
            "destination": destination,
            "duration_ms": duration_ms,
            "timestamp": datetime.utcnow().isoformat()
        }))

# Usage in service classes:
# logger = StructuredLogger(__name__)
# logger.log_geocode_request(address, cached=True)
```

**Log Levels**:
- `DEBUG`: Individual HTTP requests to external APIs
- `INFO`: Successful operations (geocoding, routing)
- `WARNING`: Rate limits approaching, cache misses
- `ERROR`: Failed API calls, geocoding errors
- `CRITICAL`: Service completely unavailable

### Metrics

**Prometheus Metrics** (future enhancement):

```python
from prometheus_client import Counter, Histogram

# Define metrics
geocode_requests_total = Counter(
    'geocode_requests_total',
    'Total geocoding requests',
    ['provider', 'cached']
)

geocode_duration_seconds = Histogram(
    'geocode_duration_seconds',
    'Geocoding request duration',
    ['provider']
)

route_calculation_total = Counter(
    'route_calculation_total',
    'Total route calculations',
    ['provider']
)

external_api_errors_total = Counter(
    'external_api_errors_total',
    'External API errors',
    ['provider', 'error_type']
)

# Usage:
# geocode_requests_total.labels(provider='osm', cached=True).inc()
# with geocode_duration_seconds.labels(provider='osm').time():
#     result = await service.geocode(address)
```

**Key Metrics to Track**:
- Geocoding cache hit rate (target: >70%)
- Average response time by provider
- External API error rate (target: <1%)
- Rate limit events per hour
- Total requests per endpoint

### Tracing

**OpenTelemetry Integration** (future enhancement):

```python
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# Instrument FastAPI app
FastAPIInstrumentor.instrument_app(app)

# Manual span creation in service methods
tracer = trace.get_tracer(__name__)

async def geocode(self, address: str) -> Optional[Coordinates]:
    with tracer.start_as_current_span("geocode") as span:
        span.set_attribute("address", address)

        # Check cache
        with tracer.start_as_current_span("cache_lookup"):
            cached = await self.cache_repo.get_by_address(address)

        if cached:
            span.set_attribute("cache_hit", True)
            return cached

        # Call external API
        with tracer.start_as_current_span("external_api_call"):
            result = await self._call_nominatim(address)

        span.set_attribute("cache_hit", False)
        return result
```

---

## Open Questions

### Technical Decisions Requiring Input

1. **Cache Eviction Policy**:
   - **Question**: Should we use LRU (Least Recently Used) or TTL (Time To Live) for cache eviction?
   - **Recommendation**: LRU with 90-day TTL hybrid (evict entries not accessed in 90 days)
   - **Requires Decision From**: Tech Lead

2. **Route Caching**:
   - **Question**: Should we cache route calculations? They're expensive but have many permutations.
   - **Trade-off**: Storage cost vs. API call reduction
   - **Recommendation**: Start without route caching, add if external API costs become significant
   - **Requires Decision From**: Product Owner (cost analysis)

3. **Rate Limiting Implementation**:
   - **Question**: Should we implement application-level rate limiting for external APIs?
   - **Options**:
     a. Simple sleep() delays (current approach)
     b. Token bucket algorithm with Redis
     c. Rely on external service rate limit responses (429)
   - **Recommendation**: Start with (a), upgrade to (b) if scaling to multiple instances
   - **Requires Decision From**: Backend Architect

4. **Provider Failover**:
   - **Question**: Should we implement automatic failover between providers (e.g., OSM → Mapbox if OSM is down)?
   - **Complexity**: Requires coordinating API keys, handling different response formats
   - **Recommendation**: Not for MVP, add in Phase 2 if uptime is critical
   - **Requires Decision From**: Product Owner

5. **Coordinate Precision**:
   - **Question**: How many decimal places should we store for coordinates?
   - **Context**:
     - 6 decimals = ~0.1m precision (overkill for city-to-city routes)
     - 4 decimals = ~11m precision (sufficient for carpooling)
   - **Recommendation**: Store full precision from APIs, round to 4 decimals for comparison/caching
   - **Requires Decision From**: Domain Expert

6. **Trip Coordinate Storage**:
   - **Question**: Should we automatically update Trip entities with geocoded coordinates?
   - **Current Plan**: Yes, to avoid repeated geocoding of same addresses
   - **Concern**: Adds coupling between maps module and trips module
   - **Alternative**: Separate geocoding cache is sufficient, don't modify trips
   - **Requires Decision From**: DDD Architect (aggregate boundaries)

7. **Background Task for Pre-warming**:
   - **Question**: Should we pre-geocode popular cities/addresses on startup?
   - **Benefit**: Instant responses for common routes
   - **Cost**: Startup time delay, external API calls
   - **Recommendation**: Optional feature, configurable via settings
   - **Requires Decision From**: Performance Team

---

## Implementation Checklist

### Phase 1: Core Infrastructure (Days 1-2)

- [ ] **Project Structure**
  - [ ] Create `apps/maps/` directory structure
  - [ ] Initialize Python packages (`__init__.py` files)
  - [ ] Set up `pyproject.toml` dependencies

- [ ] **Domain Layer**
  - [ ] Define `Coordinates` value object with validation
  - [ ] Define `Location` value object
  - [ ] Define `Route` entity
  - [ ] Create `IMapService` abstract interface
  - [ ] Define domain exceptions (GeocodingError, RoutingError, etc.)
  - [ ] Write unit tests for domain models (100% coverage)

- [ ] **Database Setup**
  - [ ] Create `GeocodeCacheModel` SQLAlchemy model
  - [ ] Generate Alembic migration for `geocode_cache` table
  - [ ] Test migration (upgrade/downgrade)
  - [ ] Create indexes on `address` and `accessed_at`

### Phase 2: External Service Integration (Days 3-4)

- [ ] **Infrastructure - External Services**
  - [ ] Implement `BaseHTTPClient` with retry logic
  - [ ] Implement `OpenStreetMapService`:
    - [ ] Geocoding via Nominatim
    - [ ] Reverse geocoding via Nominatim
    - [ ] Routing via OSRM
    - [ ] Rate limiting (1 req/sec for Nominatim)
  - [ ] Write unit tests with mocked HTTP (using `respx`)
  - [ ] Test against live OpenStreetMap APIs (manual verification)

- [ ] **Optional: Additional Providers**
  - [ ] Implement `MapboxService` (if API key available)
  - [ ] Implement `GoogleMapsService` (if API key available)
  - [ ] Write unit tests for additional providers

### Phase 3: Caching Layer (Day 5)

- [ ] **Infrastructure - Repositories**
  - [ ] Implement `IGeocodeCacheRepository` interface
  - [ ] Implement `SQLAlchemyGeocodeCacheRepository`:
    - [ ] `get_by_address()`
    - [ ] `save()`
    - [ ] `update_accessed_at()`
    - [ ] `evict_old_entries()`
  - [ ] Write integration tests with test database

- [ ] **Infrastructure - Cached Service**
  - [ ] Implement `CachedMapService` decorator
  - [ ] Test cache hit/miss behavior
  - [ ] Verify accessed_at updates on cache hits

### Phase 4: Application Layer (Day 6)

- [ ] **Use Cases**
  - [ ] Implement `GeocodeAddressUseCase`
  - [ ] Implement `CalculateRouteUseCase`
  - [ ] Implement `GetTripRouteUseCase` (integrates with trips module)
  - [ ] Write unit tests with mocked services

- [ ] **Configuration**
  - [ ] Create `MapSettings` with Pydantic
  - [ ] Validate provider configuration
  - [ ] Add `.env.example` with all settings
  - [ ] Document environment variables in README

### Phase 5: HTTP API (Days 7-8)

- [ ] **Request/Response Schemas**
  - [ ] Create `GeocodeRequest`, `RouteRequest` Pydantic models
  - [ ] Create `CoordinatesResponse`, `RouteResponse` models
  - [ ] Add validation and examples

- [ ] **FastAPI Router**
  - [ ] Implement `POST /geocode` endpoint
  - [ ] Implement `POST /reverse-geocode` endpoint
  - [ ] Implement `POST /route` endpoint
  - [ ] Implement `GET /trip/{trip_id}/route` endpoint
  - [ ] Add endpoint documentation (docstrings)

- [ ] **Dependency Injection**
  - [ ] Create `get_db_session()` dependency
  - [ ] Create `get_geocode_cache_repository()` dependency
  - [ ] Create `get_map_service()` factory dependency
  - [ ] Test DI wiring

- [ ] **Exception Handling**
  - [ ] Implement exception handlers for domain errors
  - [ ] Map domain exceptions to HTTP status codes
  - [ ] Test error responses

- [ ] **Main App Integration**
  - [ ] Register maps router in `main.py`
  - [ ] Register exception handlers
  - [ ] Verify in `/docs` (Swagger UI)

### Phase 6: Testing (Days 9-10)

- [ ] **Unit Tests**
  - [ ] Domain models (100% coverage)
  - [ ] Use cases (95% coverage)
  - [ ] External services with mocked HTTP (80% coverage)

- [ ] **Integration Tests**
  - [ ] API endpoints with test database
  - [ ] Cache behavior (hit/miss, eviction)
  - [ ] Trip route integration (requires trips module)

- [ ] **Contract Tests**
  - [ ] Validate OpenAPI schema
  - [ ] Verify response formats match schema

- [ ] **Load Testing** (optional)
  - [ ] Use `locust` or `k6` to simulate load
  - [ ] Verify cache improves performance
  - [ ] Check rate limiting behavior

### Phase 7: Documentation & Deployment (Day 11)

- [ ] **API Documentation**
  - [ ] Verify Swagger UI at `/docs`
  - [ ] Add endpoint examples and descriptions
  - [ ] Document error responses

- [ ] **Code Documentation**
  - [ ] Add docstrings to all public methods
  - [ ] Document architecture decisions in code comments
  - [ ] Create ADR (Architecture Decision Record) if needed

- [ ] **Deployment Preparation**
  - [ ] Create `requirements.txt` or `poetry.lock`
  - [ ] Add health check endpoint (optional)
  - [ ] Configure logging for production
  - [ ] Set up monitoring (if Prometheus available)

- [ ] **Final Review**
  - [ ] Code review with team
  - [ ] Security review (API key handling)
  - [ ] Performance review (response times)

### Phase 8: Optional Enhancements (Post-MVP)

- [ ] **Performance**
  - [ ] Implement Redis cache for route results
  - [ ] Add background task for cache pre-warming
  - [ ] Optimize polyline compression (encoded polylines)

- [ ] **Observability**
  - [ ] Add Prometheus metrics
  - [ ] Integrate OpenTelemetry tracing
  - [ ] Set up dashboards (Grafana)

- [ ] **Features**
  - [ ] Multi-waypoint routing (intermediate stops)
  - [ ] Route alternatives (fastest, shortest, avoid tolls)
  - [ ] Traffic-aware routing (Google Maps only)
  - [ ] Provider failover mechanism

---

## Acceptance Criteria

### Functional Requirements (from Issue #5)

- [x] **User can request "View on Map" for any trip**
  - Endpoint: `GET /api/v1/maps/trip/{trip_id}/route`
  - Returns route with polyline

- [x] **System displays map with visualized route**
  - Route includes polyline (array of coordinates)
  - Frontend can render using Leaflet.js or similar

- [x] **Clear markers for origin and destination**
  - Route response includes origin and destination Location objects with names

- [x] **Route drawn as line/polyline between points**
  - Polyline array included in response

- [x] **Map has appropriate zoom level**
  - Handled by frontend based on route bounds

- [x] **Works without authentication (public)**
  - No authentication required on endpoints

- [x] **Functional integration with map service (OpenStreetMap)**
  - OpenStreetMapService implemented and tested

### Non-Functional Requirements

- [ ] **Performance**:
  - Geocoding: <500ms (with cache miss)
  - Geocoding: <50ms (with cache hit)
  - Route calculation: <2s
  - Cache hit rate: >70%

- [ ] **Reliability**:
  - Handle external service downtime gracefully (503 errors)
  - Retry failed requests with exponential backoff
  - Respect rate limits (no bans from external services)

- [ ] **Scalability**:
  - Support 100 concurrent requests
  - Cache reduces external API calls by >70%

- [ ] **Maintainability**:
  - Test coverage >85%
  - All public APIs documented
  - Clean Architecture principles maintained

---

## Related Documentation

- **Functional Requirements**: `.claude/plans/06-RF-005-visualizacion-mapas.md`
- **Context Map**: `.claude/docs/context-map.md` (if exists)
- **Trip Module**: Integration point for `GET /trip/{id}/route` endpoint
- **OpenStreetMap Nominatim API**: https://nominatim.org/release-docs/latest/api/Overview/
- **OSRM API**: http://project-osrm.org/docs/v5.24.0/api/
- **FastAPI Dependency Injection**: https://fastapi.tiangolo.com/tutorial/dependencies/
- **SQLAlchemy Async**: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html

---

## Notes for Implementers

### Critical Architecture Rules

1. **Domain Purity**: Domain layer (`domain/`) must have ZERO dependencies on FastAPI, SQLAlchemy, httpx, or any framework. It should contain only Pydantic models and abstract interfaces.

2. **Dependency Inversion**: Infrastructure depends on domain, not the other way around. Use abstract interfaces (`IMapService`, `IGeocodeCacheRepository`) in application layer, inject concrete implementations via FastAPI DI.

3. **Async/Await Everywhere**: All I/O operations (HTTP, database) must be async. Use `async def` and `await` consistently. Do NOT block the event loop.

4. **Error Handling**: NEVER let external service errors propagate raw. Catch `httpx` exceptions, translate to domain exceptions, let FastAPI exception handlers convert to HTTP responses.

5. **Configuration Security**: NEVER commit `.env` files or API keys. Use environment variables, validate at startup.

### Common Pitfalls to Avoid

- **Don't cache reverse geocoding**: Results vary by zoom level and change over time.
- **Don't cache routes in MVP**: Too many permutations, add later if needed.
- **Don't forget User-Agent**: Nominatim REQUIRES a User-Agent header or it will block you.
- **Don't ignore rate limits**: OSM Nominatim is 1 req/sec, respect it or get banned.
- **Don't use sync SQLAlchemy**: Must use `sqlalchemy.ext.asyncio` for compatibility with FastAPI async.
- **Don't couple map service to trip repository**: Use application layer to orchestrate, keep services independent.

### Testing Best Practices

- **Mock external HTTP in unit tests**: Use `respx` to mock OpenStreetMap APIs, don't hit live services in tests.
- **Use test database for integration tests**: Create a separate SQLite file for tests, reset between test runs.
- **Test cache behavior explicitly**: Write tests that verify cache hits, misses, and eviction.
- **Verify error handling**: Test 404, 429, 500, 503 responses from external services.

---

**End of Implementation Plan**

This plan is ready for implementation. Developers should start with Phase 1 (Core Infrastructure) and proceed sequentially through the checklist. All architectural decisions are documented and justified. Open questions should be resolved before reaching their respective implementation phases.
