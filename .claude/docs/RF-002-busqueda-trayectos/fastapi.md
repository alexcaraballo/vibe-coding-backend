# FastAPI Implementation Plan: RF-002 - Búsqueda de Trayectos

**Status**: READY
**Version**: 1.0.0
**Last Updated**: 2025-11-13
**Related Docs**:
- Functional Requirement: `.claude/plans/03-RF-002-busqueda-trayectos.md`
- RF-001 Trip Entity: `.claude/plans/02-RF-001-publicacion-trayectos.md`

---

## Summary

This implementation plan details the FastAPI search endpoint for trips using SQLAlchemy async with SQLite3. The search functionality enables passengers to find available trips by origin, destination, and date range with case-insensitive partial matching. The implementation leverages SQLAlchemy's async ORM capabilities, proper indexing for performance, and follows Clean Architecture principles by building upon the existing Trip entity from RF-001.

**Key Features:**
- Case-insensitive partial text search using SQLAlchemy ILIKE
- Date range filtering with SQLAlchemy date comparison
- Availability filtering (only trips with available_seats > 0)
- Pagination with skip/limit using SQLAlchemy offset/limit
- Sorting by departure date using SQLAlchemy order_by
- Public endpoint (no authentication required)
- Optimized with SQLite indexes for search performance

---

## Architecture Mapping

### Domain → FastAPI Mapping

| Domain Concept | FastAPI Construct | Location | Notes |
|---------------|------------------|----------|-------|
| Trip Aggregate | SQLAlchemy ORM Model | `apps/trips/infrastructure/database/models.py` | Async ORM with Base |
| Trip Search Query | Repository Method | `apps/trips/infrastructure/repositories/trip_repository.py` | async def search() |
| Search Parameters | Pydantic Query Model | `apps/trips/api/versioning/v1/schemas/requests.py` | Query parameter validation |
| Search Results | Response Schema | `apps/trips/api/versioning/v1/schemas/responses.py` | TripListResponse |
| Search Endpoint | FastAPI Router | `apps/trips/api/versioning/v1/views.py` | GET /search |
| Database Session | FastAPI Dependency | `config/database.py` | AsyncSession injection |

### Layer Responsibilities

- **Domain Layer** (`apps/trips/domain/`):
  - Pure Python Trip entity (Pydantic model) with business logic
  - ITripRepository interface defining search contract
  - Business rules: has_available_seats(), validation logic

- **Application Layer** (`apps/trips/application/`):
  - Use case orchestration (if complex logic needed)
  - Currently handled directly in views for simple CRUD

- **Infrastructure Layer** (`apps/trips/infrastructure/`):
  - SQLAlchemy ORM models for persistence
  - TripRepository implementation with async SQLAlchemy queries
  - Database session management
  - Indexes and query optimization

- **HTTP Entrypoints** (`apps/trips/api/`):
  - FastAPI routers with search endpoint
  - Query parameter validation via Pydantic
  - Response serialization
  - HTTP error handling

---

## SQLAlchemy ORM Model

### File: `apps/trips/infrastructure/database/models.py`

The Trip SQLAlchemy model must map to the domain Trip entity with proper indexes for search performance.

```python
from sqlalchemy import (
    Column, String, Integer, Float, Boolean,
    DateTime, Date, Time, Index, Text
)
from sqlalchemy.sql import func
from config.database import Base


class TripModel(Base):
    """SQLAlchemy ORM model for trips"""
    __tablename__ = "trips"

    # Primary Key
    id = Column(String(36), primary_key=True)

    # Trip Information
    origin = Column(String(200), nullable=False, index=True)
    destination = Column(String(200), nullable=False, index=True)
    departure_date = Column(Date, nullable=False, index=True)
    departure_time = Column(Time, nullable=False)

    # Geographic Coordinates (for future matching)
    origin_lat = Column(Float, nullable=True)
    origin_lng = Column(Float, nullable=True)
    destination_lat = Column(Float, nullable=True)
    destination_lng = Column(Float, nullable=True)

    # Seat Management
    available_seats = Column(Integer, nullable=False, index=True)
    total_seats = Column(Integer, nullable=False)

    # Matching Fields
    estimated_arrival_time = Column(Time, nullable=True)
    max_detour_minutes = Column(Integer, default=30)
    current_detour_minutes = Column(Integer, default=0)
    roadmap = Column(Text, nullable=True)  # JSON string

    # Driver Reference
    driver_id = Column(String(36), nullable=False, index=True)

    # Metadata
    status = Column(String(20), nullable=False, default="active", index=True)
    price_per_seat = Column(Float, nullable=True)
    description = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, onupdate=func.now(), nullable=True)

    # Composite Indexes for Search Performance
    __table_args__ = (
        # Index for origin + destination search
        Index('idx_origin_destination', 'origin', 'destination'),

        # Index for date-based filtering
        Index('idx_departure_date_status', 'departure_date', 'status', 'is_active'),

        # Index for availability filtering
        Index('idx_available_seats_active', 'available_seats', 'is_active', 'status'),

        # Composite index for full search query
        Index(
            'idx_search_composite',
            'origin', 'destination', 'departure_date',
            'status', 'is_active', 'available_seats'
        ),
    )
```

**Key Design Decisions:**
- Use `String(36)` for IDs (UUID format)
- Index individual fields: origin, destination, departure_date, available_seats, status, is_active
- Composite indexes for common query patterns
- `roadmap` stored as JSON text (parse in application layer)
- `func.now()` for automatic timestamps

---

## Repository Implementation

### File: `apps/trips/infrastructure/repositories/trip_repository.py`

Extend the existing repository with an optimized async search method using SQLAlchemy filters.

```python
from typing import Optional
from datetime import date, datetime
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from apps.trips.domain.models import Trip
from apps.trips.domain.repositories.trip_repository import ITripRepository
from apps.trips.infrastructure.database.models import TripModel


class TripRepository(ITripRepository):
    """SQLAlchemy async implementation of Trip repository"""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def search(
        self,
        origin: Optional[str] = None,
        destination: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        min_seats: int = 1,
        skip: int = 0,
        limit: int = 100
    ) -> list[Trip]:
        """
        Search trips with filters using SQLAlchemy async queries.

        Search Behavior:
        - Case-insensitive partial matching for origin/destination (ILIKE)
        - Only active trips (status='active', is_active=True)
        - Only trips with available seats >= min_seats
        - Date filtering: departure_date >= date_from (defaults to today)
        - Optional date_to: departure_date <= date_to
        - Results sorted by departure_date ASC (soonest first)
        - Pagination via offset/limit

        Performance Optimizations:
        - Uses composite indexes: idx_search_composite
        - Filters applied in optimal order (indexed columns first)
        - Single query with JOIN-free filtering
        """
        # Base query
        query = select(TripModel)

        # Build filters list
        filters = [
            TripModel.status == "active",
            TripModel.is_active == True,
            TripModel.available_seats >= min_seats
        ]

        # Origin filter: case-insensitive partial match
        if origin:
            # ILIKE for SQLite case-insensitive search
            # Wraps search term with % for partial matching
            filters.append(TripModel.origin.ilike(f"%{origin}%"))

        # Destination filter: case-insensitive partial match
        if destination:
            filters.append(TripModel.destination.ilike(f"%{destination}%"))

        # Date range filtering
        if date_from:
            filters.append(TripModel.departure_date >= date_from)
        else:
            # Default: only future trips from today
            filters.append(TripModel.departure_date >= date.today())

        if date_to:
            filters.append(TripModel.departure_date <= date_to)

        # Apply all filters using AND
        query = query.where(and_(*filters))

        # Sort by departure date (soonest first)
        query = query.order_by(TripModel.departure_date.asc())

        # Pagination
        query = query.offset(skip).limit(limit)

        # Execute query
        result = await self._session.execute(query)
        trip_models = result.scalars().all()

        # Convert ORM models to domain entities
        trips = [self._to_domain(model) for model in trip_models]

        return trips

    def _to_domain(self, model: TripModel) -> Trip:
        """Convert SQLAlchemy model to domain entity"""
        import json

        # Parse roadmap JSON if present
        roadmap = []
        if model.roadmap:
            try:
                roadmap = json.loads(model.roadmap)
            except json.JSONDecodeError:
                roadmap = []

        return Trip(
            id=model.id,
            origin=model.origin,
            destination=model.destination,
            departure_date=model.departure_date,
            departure_time=model.departure_time,
            origin_lat=model.origin_lat,
            origin_lng=model.origin_lng,
            destination_lat=model.destination_lat,
            destination_lng=model.destination_lng,
            available_seats=model.available_seats,
            total_seats=model.total_seats,
            estimated_arrival_time=model.estimated_arrival_time,
            max_detour_minutes=model.max_detour_minutes,
            current_detour_minutes=model.current_detour_minutes,
            roadmap=roadmap,
            driver_id=model.driver_id,
            status=model.status,
            price_per_seat=model.price_per_seat,
            description=model.description,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at
        )
```

**SQLAlchemy Query Patterns Used:**
- `select(TripModel)`: Base query
- `.ilike(f"%{term}%")`: Case-insensitive partial matching (SQLite compatible)
- `and_(*filters)`: Combine multiple filters with AND logic
- `.order_by(column.asc())`: Sort results
- `.offset(skip).limit(limit)`: Pagination
- `await session.execute(query)`: Async execution
- `result.scalars().all()`: Extract ORM objects

---

## API Request Schema

### File: `apps/trips/api/versioning/v1/schemas/requests.py`

Add query parameter validation schema (optional but recommended for documentation).

```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date


class SearchTripsQueryParams(BaseModel):
    """
    Query parameters for trip search endpoint.

    Note: FastAPI automatically parses these from URL query params.
    This schema is primarily for OpenAPI documentation.
    """
    origin: Optional[str] = Field(
        None,
        description="City of origin (partial, case-insensitive match)",
        example="Cádiz"
    )
    destination: Optional[str] = Field(
        None,
        description="City of destination (partial, case-insensitive match)",
        example="Sevilla"
    )
    date_from: Optional[date] = Field(
        None,
        description="Minimum departure date (YYYY-MM-DD). Defaults to today.",
        example="2025-12-15"
    )
    date_to: Optional[date] = Field(
        None,
        description="Maximum departure date (YYYY-MM-DD). Optional.",
        example="2025-12-31"
    )
    min_seats: int = Field(
        1,
        ge=1,
        le=10,
        description="Minimum available seats required"
    )
    skip: int = Field(
        0,
        ge=0,
        description="Number of results to skip (pagination offset)"
    )
    limit: int = Field(
        100,
        ge=1,
        le=500,
        description="Maximum number of results to return"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "origin": "Cádiz",
                "destination": "Sevilla",
                "date_from": "2025-12-15",
                "date_to": "2025-12-31",
                "min_seats": 2,
                "skip": 0,
                "limit": 20
            }
        }
```

---

## Search Endpoint

### File: `apps/trips/api/versioning/v1/views.py`

Add the search endpoint after existing trip endpoints.

```python
from typing import Annotated, Optional
from datetime import date
from fastapi import APIRouter, Depends, Query, status

from apps.trips.domain.repositories.trip_repository import ITripRepository
from apps.trips.infrastructure.dependencies import get_trip_repository
from apps.trips.api.versioning.v1.schemas.responses import TripResponse, TripListResponse

router = APIRouter()


@router.get("/search", response_model=TripListResponse)
async def search_trips(
    repo: Annotated[ITripRepository, Depends(get_trip_repository)],
    origin: Optional[str] = Query(
        None,
        description="Ciudad de origen (búsqueda aproximada, case-insensitive)",
        example="Cádiz"
    ),
    destination: Optional[str] = Query(
        None,
        description="Ciudad de destino (búsqueda aproximada, case-insensitive)",
        example="Sevilla"
    ),
    date_from: Optional[date] = Query(
        None,
        description="Fecha mínima de salida (YYYY-MM-DD). Por defecto: hoy",
        example="2025-12-15"
    ),
    date_to: Optional[date] = Query(
        None,
        description="Fecha máxima de salida (YYYY-MM-DD). Opcional",
        example="2025-12-31"
    ),
    min_seats: int = Query(
        1,
        ge=1,
        le=10,
        description="Número mínimo de plazas disponibles requeridas"
    ),
    skip: int = Query(0, ge=0, description="Número de resultados a omitir (paginación)"),
    limit: int = Query(100, ge=1, le=500, description="Número máximo de resultados")
):
    """
    **Buscar trayectos disponibles con filtros**

    Permite a los pasajeros buscar trayectos que cumplan criterios específicos.

    ## Características

    - ✅ Búsqueda **aproximada** por ciudad (case-insensitive, parcial)
    - ✅ Filtro por rango de fechas (solo trayectos futuros por defecto)
    - ✅ Filtro por número mínimo de plazas disponibles
    - ✅ Solo retorna trayectos activos con plazas disponibles
    - ✅ Ordenados por fecha de salida (más cercanos primero)
    - ✅ Paginación con skip/limit
    - ✅ **No requiere autenticación** (endpoint público)

    ## Ejemplos de Uso

    **Búsqueda por origen y destino:**
    ```
    GET /api/v1/trips/v1/search?origin=Cádiz&destination=Sevilla
    ```

    **Búsqueda aproximada (case-insensitive, parcial):**
    ```
    GET /api/v1/trips/v1/search?origin=cadiz&destination=sev
    ```
    Retorna trayectos donde origen contiene "cadiz" y destino contiene "sev"

    **Filtro por rango de fechas:**
    ```
    GET /api/v1/trips/v1/search?date_from=2025-12-15&date_to=2025-12-31
    ```

    **Buscar con mínimo de plazas:**
    ```
    GET /api/v1/trips/v1/search?origin=Cádiz&min_seats=3
    ```

    **Solo por origen:**
    ```
    GET /api/v1/trips/v1/search?origin=Cádiz
    ```

    **Con paginación:**
    ```
    GET /api/v1/trips/v1/search?origin=Cádiz&skip=0&limit=10
    ```

    ## Reglas de Negocio

    - Solo trayectos con `status = "active"`
    - Solo trayectos con `is_active = True`
    - Solo trayectos con `available_seats >= min_seats`
    - Por defecto, solo trayectos con `departure_date >= hoy`
    - Búsqueda de texto: case-insensitive, coincidencia parcial

    ## Respuesta

    Retorna lista de trayectos ordenados por fecha de salida ascendente (más próximos primero).
    """
    # Execute search via repository
    trips = await repo.search(
        origin=origin,
        destination=destination,
        date_from=date_from,
        date_to=date_to,
        min_seats=min_seats,
        skip=skip,
        limit=limit
    )

    # Convert domain entities to response DTOs
    trip_responses = [TripResponse(**trip.model_dump()) for trip in trips]

    return TripListResponse(
        trips=trip_responses,
        total=len(trip_responses),  # Note: This is page size, not total count
        skip=skip,
        limit=limit
    )
```

**Key Implementation Notes:**
- Uses FastAPI's `Query()` for explicit parameter documentation
- No authentication required (public endpoint)
- Query parameters are optional except skip/limit with defaults
- Repository handles all filtering logic
- Response uses existing TripListResponse schema from RF-001

---

## Dependency Injection Update

### File: `apps/trips/infrastructure/dependencies.py`

Ensure the repository dependency uses async session correctly.

```python
from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_async_session
from apps.trips.domain.repositories.trip_repository import ITripRepository
from apps.trips.infrastructure.repositories.trip_repository import TripRepository


async def get_trip_repository(
    session: Annotated[AsyncSession, Depends(get_async_session)]
) -> ITripRepository:
    """
    FastAPI dependency that provides ITripRepository implementation.

    Injects async SQLAlchemy session into repository.
    Session lifecycle managed by get_async_session dependency.
    """
    return TripRepository(session)
```

---

## Database Indexes

### File: `migrations/versions/{timestamp}_add_trip_search_indexes.py`

Create Alembic migration for search indexes (if not already in initial migration).

```python
"""Add indexes for trip search optimization

Revision ID: {generated_id}
Revises: {previous_revision}
Create Date: 2025-11-13
"""
from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    """Add indexes for trip search performance"""

    # Individual column indexes
    op.create_index('idx_trips_origin', 'trips', ['origin'])
    op.create_index('idx_trips_destination', 'trips', ['destination'])
    op.create_index('idx_trips_departure_date', 'trips', ['departure_date'])
    op.create_index('idx_trips_available_seats', 'trips', ['available_seats'])
    op.create_index('idx_trips_status', 'trips', ['status'])
    op.create_index('idx_trips_is_active', 'trips', ['is_active'])
    op.create_index('idx_trips_driver_id', 'trips', ['driver_id'])

    # Composite indexes for common query patterns
    op.create_index(
        'idx_origin_destination',
        'trips',
        ['origin', 'destination']
    )

    op.create_index(
        'idx_departure_date_status',
        'trips',
        ['departure_date', 'status', 'is_active']
    )

    op.create_index(
        'idx_available_seats_active',
        'trips',
        ['available_seats', 'is_active', 'status']
    )

    # Composite index covering full search query
    op.create_index(
        'idx_search_composite',
        'trips',
        ['origin', 'destination', 'departure_date', 'status', 'is_active', 'available_seats']
    )


def downgrade() -> None:
    """Remove search indexes"""
    op.drop_index('idx_search_composite', table_name='trips')
    op.drop_index('idx_available_seats_active', table_name='trips')
    op.drop_index('idx_departure_date_status', table_name='trips')
    op.drop_index('idx_origin_destination', table_name='trips')
    op.drop_index('idx_trips_driver_id', table_name='trips')
    op.drop_index('idx_trips_is_active', table_name='trips')
    op.drop_index('idx_trips_status', table_name='trips')
    op.drop_index('idx_trips_available_seats', table_name='trips')
    op.drop_index('idx_trips_departure_date', table_name='trips')
    op.drop_index('idx_trips_destination', table_name='trips')
    op.drop_index('idx_trips_origin', table_name='trips')
```

**Index Strategy:**
- **Individual indexes**: For single-column filters (origin, destination, date, status)
- **Composite indexes**: For common multi-column queries
- **idx_search_composite**: Covers the full search query pattern
- SQLite will choose the most efficient index based on query

**Performance Notes:**
- SQLite's query planner will automatically select optimal index
- ILIKE queries benefit from text indexes
- Composite indexes reduce query time for filtered searches
- Trade-off: Slightly slower writes, much faster reads

---

## Testing Strategy

### File: `tests/test_trips/test_search_trips.py`

Comprehensive integration tests for search functionality.

```python
import pytest
from httpx import AsyncClient
from datetime import date, time, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from main import app
from apps.trips.infrastructure.database.models import TripModel


@pytest.fixture
async def sample_trips(async_session: AsyncSession):
    """Create sample trips for testing"""
    trips = [
        TripModel(
            id="trip-1",
            origin="Cádiz",
            destination="Sevilla",
            departure_date=date.today() + timedelta(days=1),
            departure_time=time(9, 0),
            available_seats=3,
            total_seats=3,
            driver_id="driver-1",
            status="active",
            is_active=True,
            price_per_seat=5.0
        ),
        TripModel(
            id="trip-2",
            origin="Cádiz",
            destination="Madrid",
            departure_date=date.today() + timedelta(days=2),
            departure_time=time(10, 0),
            available_seats=2,
            total_seats=4,
            driver_id="driver-2",
            status="active",
            is_active=True,
            price_per_seat=15.0
        ),
        TripModel(
            id="trip-3",
            origin="Sevilla",
            destination="Madrid",
            departure_date=date.today() + timedelta(days=3),
            departure_time=time(11, 0),
            available_seats=0,  # No available seats
            total_seats=3,
            driver_id="driver-3",
            status="active",
            is_active=True,
            price_per_seat=12.0
        ),
        TripModel(
            id="trip-4",
            origin="Cádiz",
            destination="Sevilla",
            departure_date=date.today() - timedelta(days=1),  # Past trip
            departure_time=time(8, 0),
            available_seats=2,
            total_seats=2,
            driver_id="driver-1",
            status="completed",
            is_active=False
        ),
        TripModel(
            id="trip-5",
            origin="Málaga",
            destination="Granada",
            departure_date=date.today() + timedelta(days=5),
            departure_time=time(14, 0),
            available_seats=4,
            total_seats=4,
            driver_id="driver-4",
            status="active",
            is_active=True,
            price_per_seat=8.0
        ),
    ]

    async_session.add_all(trips)
    await async_session.commit()

    yield trips

    # Cleanup
    for trip in trips:
        await async_session.delete(trip)
    await async_session.commit()


@pytest.mark.asyncio
async def test_search_trips_by_origin(sample_trips):
    """Test search by origin city"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/v1/trips/v1/search?origin=Cádiz")

    assert response.status_code == 200
    data = response.json()
    assert "trips" in data

    # Should return only active future trips from Cádiz with available seats
    assert len(data["trips"]) == 2  # trip-1 and trip-2
    for trip in data["trips"]:
        assert "cádiz" in trip["origin"].lower()
        assert trip["available_seats"] > 0
        assert trip["status"] == "active"


@pytest.mark.asyncio
async def test_search_trips_by_origin_and_destination(sample_trips):
    """Test search by origin and destination"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/v1/trips/v1/search?origin=Cádiz&destination=Sevilla")

    assert response.status_code == 200
    data = response.json()

    # Should return only trip-1 (future, active, available seats)
    assert len(data["trips"]) == 1
    assert data["trips"][0]["origin"] == "Cádiz"
    assert data["trips"][0]["destination"] == "Sevilla"
    assert data["trips"][0]["available_seats"] > 0


@pytest.mark.asyncio
async def test_search_trips_case_insensitive(sample_trips):
    """Test case-insensitive partial matching"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Search with lowercase and partial match
        response = await ac.get("/api/v1/trips/v1/search?origin=cadiz&destination=sev")

    assert response.status_code == 200
    data = response.json()

    # Should match "Cádiz" and "Sevilla"
    assert len(data["trips"]) >= 1
    for trip in data["trips"]:
        assert "cádiz" in trip["origin"].lower()
        assert "sev" in trip["destination"].lower()


@pytest.mark.asyncio
async def test_search_trips_by_date_range(sample_trips):
    """Test search with date range filter"""
    date_from = date.today() + timedelta(days=2)
    date_to = date.today() + timedelta(days=5)

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get(
            f"/api/v1/trips/v1/search?date_from={date_from.isoformat()}&date_to={date_to.isoformat()}"
        )

    assert response.status_code == 200
    data = response.json()

    # Should return trips within date range with available seats
    for trip in data["trips"]:
        trip_date = date.fromisoformat(trip["departure_date"])
        assert date_from <= trip_date <= date_to
        assert trip["available_seats"] > 0


@pytest.mark.asyncio
async def test_search_trips_only_future_by_default(sample_trips):
    """Test that search returns only future trips by default"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/v1/trips/v1/search")

    assert response.status_code == 200
    data = response.json()

    # Should not include trip-4 (past trip)
    today = date.today()
    for trip in data["trips"]:
        trip_date = date.fromisoformat(trip["departure_date"])
        assert trip_date >= today


@pytest.mark.asyncio
async def test_search_trips_only_available_seats(sample_trips):
    """Test that search only returns trips with available seats"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/v1/trips/v1/search?origin=Sevilla")

    assert response.status_code == 200
    data = response.json()

    # Should not include trip-3 (no available seats)
    for trip in data["trips"]:
        assert trip["available_seats"] > 0


@pytest.mark.asyncio
async def test_search_trips_min_seats_filter(sample_trips):
    """Test search with minimum seats requirement"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/v1/trips/v1/search?min_seats=3")

    assert response.status_code == 200
    data = response.json()

    # Should return trips with at least 3 available seats
    for trip in data["trips"]:
        assert trip["available_seats"] >= 3


@pytest.mark.asyncio
async def test_search_trips_no_results(sample_trips):
    """Test search with no matching results"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/v1/trips/v1/search?origin=CiudadInexistente")

    assert response.status_code == 200
    data = response.json()
    assert len(data["trips"]) == 0
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_search_trips_pagination(sample_trips):
    """Test pagination with skip and limit"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # First page
        response1 = await ac.get("/api/v1/trips/v1/search?skip=0&limit=2")

        # Second page
        response2 = await ac.get("/api/v1/trips/v1/search?skip=2&limit=2")

    assert response1.status_code == 200
    assert response2.status_code == 200

    data1 = response1.json()
    data2 = response2.json()

    # Check pagination parameters
    assert data1["skip"] == 0
    assert data1["limit"] == 2
    assert len(data1["trips"]) <= 2

    assert data2["skip"] == 2
    assert data2["limit"] == 2

    # Ensure different results
    if len(data1["trips"]) > 0 and len(data2["trips"]) > 0:
        assert data1["trips"][0]["id"] != data2["trips"][0]["id"]


@pytest.mark.asyncio
async def test_search_trips_sorted_by_date(sample_trips):
    """Test that results are sorted by departure date ascending"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/v1/trips/v1/search")

    assert response.status_code == 200
    data = response.json()

    # Verify ascending order
    if len(data["trips"]) > 1:
        dates = [date.fromisoformat(t["departure_date"]) for t in data["trips"]]
        assert dates == sorted(dates)


@pytest.mark.asyncio
async def test_search_trips_no_authentication_required(sample_trips):
    """Test that search endpoint is public (no auth required)"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # No Authorization header
        response = await ac.get("/api/v1/trips/v1/search?origin=Cádiz")

    # Should succeed without authentication
    assert response.status_code == 200
```

### Test Coverage Requirements

- **Filter Tests**: Each filter type (origin, destination, date, seats)
- **Combination Tests**: Multiple filters applied simultaneously
- **Edge Cases**: No results, past dates, zero seats
- **Pagination**: Skip/limit functionality
- **Sorting**: Verify date ascending order
- **Case Sensitivity**: Verify case-insensitive matching
- **Authentication**: Verify public access
- **Data Integrity**: Only active trips with available seats

---

## Performance Optimization

### Query Performance Analysis

**Expected Query Plan (with indexes):**
```sql
EXPLAIN QUERY PLAN
SELECT * FROM trips
WHERE origin LIKE '%Cádiz%'
  AND destination LIKE '%Sevilla%'
  AND departure_date >= '2025-12-15'
  AND status = 'active'
  AND is_active = 1
  AND available_seats >= 1
ORDER BY departure_date ASC
LIMIT 100 OFFSET 0;
```

**SQLite will use:**
1. `idx_search_composite` if all columns are filtered
2. Individual indexes for partial filters
3. Index on `departure_date` for date filtering
4. Index on `status` + `is_active` for active filtering

### Performance Tips

1. **Use Composite Index**: The `idx_search_composite` index covers most search queries
2. **Limit Result Set**: Always use pagination (limit) to avoid large result sets
3. **Index Maintenance**: SQLite automatically maintains indexes
4. **Query Analysis**: Use `EXPLAIN QUERY PLAN` to verify index usage
5. **Text Search Optimization**: Consider FTS5 for full-text search if needed

### Monitoring Queries

```python
# Enable SQL echo in development
# config/database.py
async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True,  # Logs all SQL queries
    future=True,
)
```

---

## Error Handling

### Expected Errors

| Error Scenario | HTTP Status | Error Response |
|---------------|-------------|----------------|
| Invalid date format | 422 | Validation error from Pydantic |
| Invalid skip/limit | 422 | Validation error (out of range) |
| Database connection error | 500 | Internal server error |
| No results found | 200 | Empty trips array (not an error) |

### Error Handler Example

```python
from fastapi import HTTPException, status

# In views.py
@router.get("/search", response_model=TripListResponse)
async def search_trips(...):
    try:
        trips = await repo.search(...)
        # ... return response
    except Exception as e:
        # Log error
        logger.error(f"Search error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al buscar trayectos"
        )
```

---

## API Documentation (OpenAPI/Swagger)

### Swagger UI Example

When visiting `/docs`, the search endpoint will display:

**Request Parameters:**
- `origin` (string, optional): City of origin
- `destination` (string, optional): City of destination
- `date_from` (date, optional): Minimum departure date
- `date_to` (date, optional): Maximum departure date
- `min_seats` (integer): Minimum available seats (default: 1)
- `skip` (integer): Pagination offset (default: 0)
- `limit` (integer): Page size (default: 100, max: 500)

**Response Schema:**
```json
{
  "trips": [
    {
      "id": "string",
      "origin": "string",
      "destination": "string",
      "departure_date": "2025-12-15",
      "departure_time": "09:00:00",
      "available_seats": 3,
      "total_seats": 3,
      "driver_id": "string",
      "status": "active",
      "price_per_seat": 5.0,
      "description": "string",
      "created_at": "2025-11-13T12:00:00",
      ...
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 100
}
```

---

## Dependencies

### Required Python Packages

```toml
[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.104.0"
pydantic = "^2.5.0"
sqlalchemy = "^2.0.23"
aiosqlite = "^0.19.0"  # Async SQLite driver
alembic = "^1.12.0"

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.0"
pytest-asyncio = "^0.21.0"
httpx = "^0.25.0"
```

### Installation Command

```bash
poetry add aiosqlite  # If not already installed
```

---

## Implementation Checklist

### Phase 1: Database Layer
- [ ] Update `TripModel` in `apps/trips/infrastructure/database/models.py` with indexes
- [ ] Create Alembic migration for indexes: `alembic revision --autogenerate -m "add_trip_search_indexes"`
- [ ] Run migration: `alembic upgrade head`
- [ ] Verify indexes created: Check SQLite schema

### Phase 2: Repository Layer
- [ ] Update `search()` method in `apps/trips/infrastructure/repositories/trip_repository.py`
- [ ] Implement SQLAlchemy query with filters (origin, destination, dates, seats)
- [ ] Add ILIKE for case-insensitive matching
- [ ] Implement sorting by departure_date
- [ ] Add pagination with offset/limit
- [ ] Test repository method with unit tests

### Phase 3: API Layer
- [ ] Create `SearchTripsQueryParams` schema in `apps/trips/api/versioning/v1/schemas/requests.py`
- [ ] Add search endpoint in `apps/trips/api/versioning/v1/views.py`
- [ ] Add comprehensive docstring with examples
- [ ] Use Query() parameters with descriptions
- [ ] Map query params to repository search() method
- [ ] Return TripListResponse

### Phase 4: Testing
- [ ] Create `tests/test_trips/test_search_trips.py`
- [ ] Test: search by origin
- [ ] Test: search by destination
- [ ] Test: search by origin + destination
- [ ] Test: case-insensitive partial matching
- [ ] Test: date range filtering (date_from, date_to)
- [ ] Test: only future trips by default
- [ ] Test: only trips with available seats
- [ ] Test: min_seats filter
- [ ] Test: no results scenario
- [ ] Test: pagination (skip/limit)
- [ ] Test: results sorted by date
- [ ] Test: no authentication required (public endpoint)
- [ ] Run tests: `pytest tests/test_trips/test_search_trips.py -v`

### Phase 5: Documentation & Validation
- [ ] Verify OpenAPI documentation at `/docs`
- [ ] Test in Swagger UI with example queries
- [ ] Verify response schemas match expectations
- [ ] Check SQL query performance with `echo=True`
- [ ] Analyze query plans for index usage
- [ ] Document any performance findings

### Phase 6: Integration Verification
- [ ] Test with curl/Postman:
  - [ ] Search by origin: `curl "http://localhost:8000/api/v1/trips/v1/search?origin=Cádiz"`
  - [ ] Search by origin + destination: `curl "http://localhost:8000/api/v1/trips/v1/search?origin=Cádiz&destination=Sevilla"`
  - [ ] Case-insensitive: `curl "http://localhost:8000/api/v1/trips/v1/search?origin=cadiz"`
  - [ ] Date filter: `curl "http://localhost:8000/api/v1/trips/v1/search?date_from=2025-12-15"`
  - [ ] Pagination: `curl "http://localhost:8000/api/v1/trips/v1/search?skip=0&limit=10"`
- [ ] Verify empty results handled gracefully
- [ ] Check response times for large result sets

### Phase 7: Code Review
- [ ] Review code for Clean Architecture compliance
- [ ] Verify domain layer has no SQLAlchemy dependencies
- [ ] Check repository implements interface correctly
- [ ] Ensure proper async/await usage
- [ ] Validate error handling
- [ ] Review test coverage (aim for >90%)

---

## Open Questions

1. **Total Count**: Should `TripListResponse.total` return the page size or the total count across all pages?
   - **Current**: Returns page size (len(trips))
   - **Alternative**: Add `count()` query to repository for total results
   - **Decision needed**: Performance vs. UX trade-off

2. **Full-Text Search**: Should we implement SQLite FTS5 for more advanced text search?
   - **Current**: Simple ILIKE pattern matching
   - **Alternative**: FTS5 virtual table for full-text search with ranking
   - **Recommendation**: Start with ILIKE, add FTS5 if needed

3. **Caching**: Should search results be cached for common queries?
   - **Consideration**: Redis cache for frequent searches (e.g., popular routes)
   - **Trade-off**: Complexity vs. performance gains
   - **Recommendation**: Profile first, then add caching if needed

4. **Geographic Search**: Should we add radius-based search using coordinates?
   - **Context**: Trip model has lat/lng fields
   - **Future**: RF-006 matching may require geographic queries
   - **Decision**: Keep for future enhancement

5. **Search Analytics**: Should we log search queries for analytics?
   - **Use case**: Understanding popular routes, improving search
   - **Privacy**: Ensure no PII logged
   - **Decision needed**: Business requirement

---

## Next Steps

After completing RF-002, the following features depend on search functionality:

1. **RF-INF-002: Validación de Disponibilidad**
   - Uses search to check trip availability before booking

2. **RF-003: Reserva de Trayectos**
   - Passengers search trips, then book selected trip

3. **RF-006: Motor de Matching**
   - Advanced search with geographic radius and route matching
   - May require geographic indexes and distance calculations

---

## Summary

This implementation plan provides:

✅ **Complete SQLAlchemy async implementation** for trip search with SQLite
✅ **Optimized database indexes** for search performance
✅ **Clean Architecture compliance** with proper layer separation
✅ **Comprehensive testing strategy** covering all scenarios
✅ **Public API endpoint** with detailed OpenAPI documentation
✅ **Pagination and sorting** for scalable result sets
✅ **Case-insensitive partial matching** using ILIKE
✅ **Date range filtering** with sensible defaults (future trips only)
✅ **Production-ready error handling** and validation

**Key Technical Decisions:**
- ILIKE for case-insensitive partial matching (SQLite compatible)
- Composite indexes for optimal query performance
- Async SQLAlchemy with proper session management
- Repository pattern for testability and maintainability
- Public endpoint (no authentication) as per requirements

**Estimated Implementation Time:** 2-3 hours
- Database layer + indexes: 30 mins
- Repository search method: 45 mins
- API endpoint: 30 mins
- Testing: 60 mins
- Documentation & validation: 15 mins
