# FastAPI Implementation Plan: RF-001 - Trip Publication

**Status**: READY
**Version**: 1.0.0
**Last Updated**: 2025-11-13
**Related Docs**:
- `.claude/plans/02-RF-001-publicacion-trayectos.md` (Functional requirements)
- `.claude/docs/RF-INF-001-gestion-usuarios/` (User authentication dependency)

---

## Summary

This implementation plan translates the Trip Publication feature (RF-001) into a production-ready FastAPI service using SQLite3 + SQLAlchemy async with Clean Architecture principles. The feature allows authenticated drivers to publish trips with origin, destination, date/time, and available seats. The architecture maintains strict layer separation: pure Python domain models, application services, SQLAlchemy-based repositories, and FastAPI HTTP entrypoints.

**Key Design Decisions:**
- **Database**: SQLite3 with SQLAlchemy async for persistence
- **Primary Key**: Integer auto-increment ID (SQLite-optimized)
- **Authentication**: Dependency on Users module (RF-INF-001) for JWT validation
- **Authorization**: Only users with `driver` or `both` roles can publish trips
- **Date Validation**: Business rule enforces future departure dates
- **Soft Delete**: Trips are marked inactive rather than physically deleted

**Technology Stack:**
- FastAPI 0.104+ for HTTP layer
- SQLAlchemy 2.0+ async for ORM and database access
- Alembic for database migrations
- Pydantic 2.5+ for request/response validation
- pytest + httpx for integration testing

---

## Architecture Mapping

### Domain → FastAPI Mapping

| Domain Concept | FastAPI Construct | Location | Notes |
|----------------|-------------------|----------|-------|
| Trip (Entity) | Pure Python dataclass | `apps/trips/domain/models.py` | No framework dependencies |
| TripStatus (Value Object) | Python Enum | `apps/trips/domain/models.py` | Used in both domain and API |
| Create Trip (Command) | POST endpoint | `apps/trips/api/v1/views.py` | Maps to `create_trip()` |
| Get Trip (Query) | GET endpoint | `apps/trips/api/v1/views.py` | Maps to `get_trip()` |
| List Trips (Query) | GET endpoint | `apps/trips/api/v1/views.py` | Maps to `list_trips()` |
| ITripRepository | Abstract base class | `apps/trips/domain/repositories/trip_repository.py` | Domain interface |
| TripRepository | SQLAlchemy implementation | `apps/trips/infrastructure/repositories/trip_repository.py` | Adapter layer |
| TripORM | SQLAlchemy model | `apps/trips/infrastructure/models.py` | Database mapping |
| CreateTripRequest | Pydantic model | `apps/trips/api/v1/schemas/requests.py` | HTTP → Application boundary |
| TripResponse | Pydantic model | `apps/trips/api/v1/schemas/responses.py` | Application → HTTP boundary |

### Layer Responsibilities

**Domain Layer** (`apps/trips/domain/`)
- Define pure business entities (`Trip`, `TripStatus`)
- Define repository interfaces (`ITripRepository`)
- Contain business logic methods (`has_available_seats()`, `can_accommodate()`)
- **Zero dependencies** on FastAPI, SQLAlchemy, or any framework

**Application Layer** (`apps/trips/application/`)
- [Future] Orchestrate complex use cases involving multiple aggregates
- [Future] Handle application-level transactions
- [Future] Emit domain events
- **Note**: For this MVP, logic stays in HTTP layer; complex use cases move here later

**Adapters/Infrastructure Layer** (`apps/trips/infrastructure/`)
- Implement repository interfaces with SQLAlchemy
- Define SQLAlchemy ORM models (`TripORM`)
- Handle database sessions and transactions
- Provide dependency injection factories

**HTTP Entrypoints Layer** (`apps/trips/api/`)
- Define FastAPI routers and endpoints
- Handle HTTP request/response serialization with Pydantic
- Enforce authentication/authorization
- Translate between HTTP and domain layer
- Handle HTTP-specific errors (404, 403, 400)

### Clean Architecture Dependency Rules

```
HTTP (FastAPI) → Application → Domain
         ↓
   Infrastructure (SQLAlchemy)
```

**Enforced Rules:**
- Domain layer imports: **ONLY** standard library + Python dataclasses
- Application layer: Can import from Domain
- Infrastructure: Can import from Domain (implements interfaces)
- HTTP layer: Can import from Domain, Application, Infrastructure (for DI)
- **NEVER**: Domain/Application importing FastAPI or SQLAlchemy

---

## File Actions

### Create New Files

**Domain Layer:**
```
apps/trips/domain/
├── __init__.py
├── models.py                          # Trip entity, TripStatus enum
└── repositories/
    ├── __init__.py
    └── trip_repository.py             # ITripRepository interface
```

**Infrastructure Layer:**
```
apps/trips/infrastructure/
├── __init__.py
├── models.py                          # TripORM SQLAlchemy model
├── dependencies.py                    # Dependency injection factories
└── repositories/
    ├── __init__.py
    └── trip_repository.py             # TripRepository implementation
```

**HTTP Layer:**
```
apps/trips/api/
├── __init__.py
├── urls.py                            # Router aggregation
└── v1/
    ├── __init__.py
    ├── views.py                       # FastAPI endpoints
    └── schemas/
        ├── __init__.py
        ├── requests.py                # CreateTripRequest, UpdateTripRequest
        └── responses.py               # TripResponse, TripListResponse
```

**Database Migrations:**
```
alembic/versions/
└── XXXX_create_trips_table.py         # Alembic migration
```

**Tests:**
```
tests/trips/
├── __init__.py
├── test_domain/
│   ├── __init__.py
│   └── test_trip_model.py             # Pure domain logic tests
├── test_repositories/
│   ├── __init__.py
│   └── test_trip_repository.py        # Repository integration tests
└── test_api/
    ├── __init__.py
    ├── test_create_trip.py            # POST /trips endpoint tests
    ├── test_get_trip.py               # GET /trips/{id} tests
    └── test_list_trips.py             # GET /trips tests
```

### Modify Existing Files

- **`main.py`**: Register trips router with `app.include_router(trips_router, prefix="/api/v1/trips")`
- **`config/database.py`**: Ensure async session factory is configured for SQLAlchemy
- **`alembic/env.py`**: Import TripORM model for migration auto-generation

---

## API Endpoints

| Method | Path | Request Model | Response Model | Use Case | Auth Required | Authorization |
|--------|------|---------------|----------------|----------|---------------|---------------|
| POST | `/api/v1/trips` | `CreateTripRequest` | `TripResponse` | Create new trip | Yes (JWT) | Driver or Both role |
| GET | `/api/v1/trips/{trip_id}` | None | `TripResponse` | Get trip by ID | No | Public |
| GET | `/api/v1/trips` | Query params | `TripListResponse` | List all trips | No | Public |
| GET | `/api/v1/trips/driver/{driver_id}` | Query params | `TripListResponse` | List trips by driver | No | Public |
| PUT | `/api/v1/trips/{trip_id}` | `UpdateTripRequest` | `TripResponse` | Update trip | Yes (JWT) | Owner only |
| DELETE | `/api/v1/trips/{trip_id}` | None | `204 No Content` | Cancel trip | Yes (JWT) | Owner only |

**Query Parameters for List Endpoints:**
- `skip: int = 0` - Pagination offset
- `limit: int = 100` - Pagination limit (max 500)
- `status: Optional[str] = None` - Filter by trip status (active, completed, cancelled)

**Authentication Flow:**
1. Client sends JWT token in `Authorization: Bearer <token>` header
2. FastAPI dependency `get_current_user()` validates token (from users module)
3. Returns `User` object with role information
4. Endpoint checks if user has required role for operation

---

## Dependencies

### Required Packages

```toml
[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.104.0"
uvicorn = {extras = ["standard"], version = "^0.24.0"}
pydantic = {extras = ["email"], version = "^2.5.0"}
pydantic-settings = "^2.1.0"
sqlalchemy = {extras = ["asyncio"], version = "^2.0.23"}
aiosqlite = "^0.19.0"                    # SQLite async driver
alembic = "^1.12.0"                      # Database migrations
python-jose = {extras = ["cryptography"], version = "^3.3.0"}  # JWT (from users module)
passlib = {extras = ["bcrypt"], version = "^1.7.4"}            # Password hashing (from users module)

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.0"
pytest-asyncio = "^0.21.0"
httpx = "^0.25.0"                        # Async HTTP client for testing
faker = "^20.0.0"                        # Test data generation
```

### Dependency Injection Hierarchy

```
FastAPI Request
    ↓
get_db_session() → AsyncSession (SQLAlchemy)
    ↓
get_trip_repository(session) → ITripRepository (TripRepository instance)
    ↓
Endpoint Handler (create_trip, get_trip, etc.)
```

**Authentication Dependencies:**
```
get_current_user() → User
    ↓
Check user.role in [UserRole.DRIVER, UserRole.BOTH]
    ↓
Allow trip creation
```

**File**: `apps/trips/infrastructure/dependencies.py`
```python
from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_db_session
from apps.trips.domain.repositories.trip_repository import ITripRepository
from apps.trips.infrastructure.repositories.trip_repository import TripRepository

async def get_trip_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)]
) -> ITripRepository:
    """Inject trip repository with database session"""
    return TripRepository(session)
```

---

## Data Persistence

### Domain Model (Pure Python)

**File**: `apps/trips/domain/models.py`

```python
from dataclasses import dataclass, field
from datetime import datetime, date, time
from typing import Optional
from enum import Enum

class TripStatus(str, Enum):
    """Trip status value object"""
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

@dataclass
class Trip:
    """
    Trip aggregate root - pure domain entity
    Represents a trip published by a driver

    Business Rules:
    - departure_date must be in the future
    - available_seats must be >= 0 and <= total_seats
    - only ACTIVE trips can accept bookings
    """
    # Identity
    id: Optional[int] = None

    # Trip details
    origin: str = ""
    destination: str = ""
    departure_date: date = field(default_factory=date.today)
    departure_time: time = field(default_factory=lambda: time(0, 0))

    # Geolocation (optional, for future matching engine)
    origin_lat: Optional[float] = None
    origin_lng: Optional[float] = None
    destination_lat: Optional[float] = None
    destination_lng: Optional[float] = None

    # Capacity management
    available_seats: int = 0
    total_seats: int = 0

    # Matching engine fields (RF-006 preparation)
    estimated_arrival_time: Optional[time] = None
    max_detour_minutes: int = 30
    current_detour_minutes: int = 0
    roadmap: list[dict] = field(default_factory=list)

    # Driver relationship
    driver_id: int = 0

    # Status and metadata
    status: TripStatus = TripStatus.ACTIVE
    price_per_seat: Optional[float] = None
    description: Optional[str] = None
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    def has_available_seats(self) -> bool:
        """Check if trip has available seats"""
        return self.available_seats > 0

    def can_accommodate(self, seats_requested: int) -> bool:
        """Check if trip can accommodate N seats"""
        return self.available_seats >= seats_requested

    def reserve_seats(self, seats: int) -> bool:
        """
        Reserve seats (business logic)
        Returns True if successful, False if insufficient seats
        """
        if not self.can_accommodate(seats):
            return False
        self.available_seats -= seats
        return True

    def release_seats(self, seats: int) -> None:
        """Release reserved seats back to available pool"""
        self.available_seats = min(self.available_seats + seats, self.total_seats)
```

**Design Notes:**
- Uses `@dataclass` for simplicity (no Pydantic in domain layer)
- All business logic methods are pure functions (no side effects)
- No framework dependencies - can be tested in isolation
- `id` is Optional[int] to work before persistence

### SQLAlchemy ORM Model

**File**: `apps/trips/infrastructure/models.py`

```python
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Date, Time, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from config.database import Base  # SQLAlchemy declarative base

class TripStatusEnum(str, enum.Enum):
    """SQLAlchemy-compatible enum"""
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class TripORM(Base):
    """
    SQLAlchemy ORM model for trips table
    Maps to Trip domain entity
    """
    __tablename__ = "trips"

    # Primary key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Trip details
    origin = Column(String(200), nullable=False)
    destination = Column(String(200), nullable=False)
    departure_date = Column(Date, nullable=False, index=True)
    departure_time = Column(Time, nullable=False)

    # Geolocation (for future matching)
    origin_lat = Column(Float, nullable=True)
    origin_lng = Column(Float, nullable=True)
    destination_lat = Column(Float, nullable=True)
    destination_lng = Column(Float, nullable=True)

    # Capacity
    available_seats = Column(Integer, nullable=False)
    total_seats = Column(Integer, nullable=False)

    # Matching engine fields
    estimated_arrival_time = Column(Time, nullable=True)
    max_detour_minutes = Column(Integer, default=30, nullable=False)
    current_detour_minutes = Column(Integer, default=0, nullable=False)
    roadmap = Column(Text, default="[]", nullable=False)  # JSON stored as text

    # Driver relationship (Foreign Key to users table)
    driver_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Status and metadata
    status = Column(SQLEnum(TripStatusEnum), default=TripStatusEnum.ACTIVE, nullable=False, index=True)
    price_per_seat = Column(Float, nullable=True)
    description = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)

    # Relationships
    driver = relationship("UserORM", back_populates="trips")  # Requires UserORM.trips relationship

    def __repr__(self):
        return f"<TripORM(id={self.id}, origin={self.origin}, destination={self.destination})>"
```

**Design Notes:**
- Integer primary key (SQLite-optimized)
- Indexes on: `id`, `departure_date`, `driver_id`, `status`, `is_active` (query optimization)
- Foreign key constraint to `users.id` with CASCADE delete
- `roadmap` stored as JSON text (parsed in repository layer)
- Timestamps use `datetime.utcnow` (consistent with requirements)

### Repository Interface

**File**: `apps/trips/domain/repositories/trip_repository.py`

```python
from abc import ABC, abstractmethod
from typing import Optional, List
from datetime import date

from apps.trips.domain.models import Trip

class ITripRepository(ABC):
    """
    Trip repository interface (domain contract)
    Defines persistence operations without implementation details
    """

    @abstractmethod
    async def create(self, trip: Trip) -> Trip:
        """
        Create new trip
        Returns trip with assigned ID
        """
        pass

    @abstractmethod
    async def get_by_id(self, trip_id: int) -> Optional[Trip]:
        """Get trip by ID, returns None if not found"""
        pass

    @abstractmethod
    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None
    ) -> List[Trip]:
        """List trips with pagination and optional status filter"""
        pass

    @abstractmethod
    async def get_by_driver(
        self,
        driver_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[Trip]:
        """Get all trips by specific driver"""
        pass

    @abstractmethod
    async def search(
        self,
        origin: Optional[str] = None,
        destination: Optional[str] = None,
        date_from: Optional[date] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Trip]:
        """
        Search trips by criteria (for RF-002)
        Uses LIKE for origin/destination, >= for date
        """
        pass

    @abstractmethod
    async def update(self, trip_id: int, trip: Trip) -> bool:
        """
        Update existing trip
        Returns True if updated, False if not found
        """
        pass

    @abstractmethod
    async def delete(self, trip_id: int) -> bool:
        """
        Soft delete trip (set is_active=False, status=CANCELLED)
        Returns True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def exists(self, trip_id: int) -> bool:
        """Check if trip exists"""
        pass
```

### Repository Implementation

**File**: `apps/trips/infrastructure/repositories/trip_repository.py`

```python
from typing import Optional, List
from datetime import datetime, date
import json

from sqlalchemy import select, update, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from apps.trips.domain.models import Trip, TripStatus
from apps.trips.domain.repositories.trip_repository import ITripRepository
from apps.trips.infrastructure.models import TripORM, TripStatusEnum

class TripRepository(ITripRepository):
    """SQLAlchemy async implementation of trip repository"""

    def __init__(self, session: AsyncSession):
        self._session = session

    def _to_domain(self, orm: TripORM) -> Trip:
        """Convert ORM model to domain entity"""
        return Trip(
            id=orm.id,
            origin=orm.origin,
            destination=orm.destination,
            departure_date=orm.departure_date,
            departure_time=orm.departure_time,
            origin_lat=orm.origin_lat,
            origin_lng=orm.origin_lng,
            destination_lat=orm.destination_lat,
            destination_lng=orm.destination_lng,
            available_seats=orm.available_seats,
            total_seats=orm.total_seats,
            estimated_arrival_time=orm.estimated_arrival_time,
            max_detour_minutes=orm.max_detour_minutes,
            current_detour_minutes=orm.current_detour_minutes,
            roadmap=json.loads(orm.roadmap) if orm.roadmap else [],
            driver_id=orm.driver_id,
            status=TripStatus(orm.status.value),
            price_per_seat=orm.price_per_seat,
            description=orm.description,
            is_active=orm.is_active,
            created_at=orm.created_at,
            updated_at=orm.updated_at
        )

    def _to_orm(self, trip: Trip) -> TripORM:
        """Convert domain entity to ORM model"""
        return TripORM(
            id=trip.id,
            origin=trip.origin,
            destination=trip.destination,
            departure_date=trip.departure_date,
            departure_time=trip.departure_time,
            origin_lat=trip.origin_lat,
            origin_lng=trip.origin_lng,
            destination_lat=trip.destination_lat,
            destination_lng=trip.destination_lng,
            available_seats=trip.available_seats,
            total_seats=trip.total_seats,
            estimated_arrival_time=trip.estimated_arrival_time,
            max_detour_minutes=trip.max_detour_minutes,
            current_detour_minutes=trip.current_detour_minutes,
            roadmap=json.dumps(trip.roadmap),
            driver_id=trip.driver_id,
            status=TripStatusEnum(trip.status.value),
            price_per_seat=trip.price_per_seat,
            description=trip.description,
            is_active=trip.is_active,
            created_at=trip.created_at,
            updated_at=trip.updated_at
        )

    async def create(self, trip: Trip) -> Trip:
        """Create new trip"""
        orm = self._to_orm(trip)
        self._session.add(orm)
        await self._session.commit()
        await self._session.refresh(orm)
        return self._to_domain(orm)

    async def get_by_id(self, trip_id: int) -> Optional[Trip]:
        """Get trip by ID"""
        stmt = select(TripORM).where(TripORM.id == trip_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None
    ) -> List[Trip]:
        """List trips with pagination"""
        stmt = select(TripORM).offset(skip).limit(limit)
        if status:
            stmt = stmt.where(TripORM.status == TripStatusEnum(status))

        result = await self._session.execute(stmt)
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def get_by_driver(
        self,
        driver_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[Trip]:
        """Get trips by driver"""
        stmt = select(TripORM).where(
            TripORM.driver_id == driver_id
        ).offset(skip).limit(limit)

        result = await self._session.execute(stmt)
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def search(
        self,
        origin: Optional[str] = None,
        destination: Optional[str] = None,
        date_from: Optional[date] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Trip]:
        """Search trips by criteria"""
        stmt = select(TripORM).where(
            and_(
                TripORM.status == TripStatusEnum.ACTIVE,
                TripORM.is_active == True
            )
        )

        if origin:
            stmt = stmt.where(TripORM.origin.ilike(f"%{origin}%"))
        if destination:
            stmt = stmt.where(TripORM.destination.ilike(f"%{destination}%"))
        if date_from:
            stmt = stmt.where(TripORM.departure_date >= date_from)

        stmt = stmt.offset(skip).limit(limit)
        result = await self._session.execute(stmt)
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def update(self, trip_id: int, trip: Trip) -> bool:
        """Update trip"""
        trip.updated_at = datetime.utcnow()
        stmt = update(TripORM).where(TripORM.id == trip_id).values(
            available_seats=trip.available_seats,
            price_per_seat=trip.price_per_seat,
            description=trip.description,
            status=TripStatusEnum(trip.status.value),
            updated_at=trip.updated_at
        )
        result = await self._session.execute(stmt)
        await self._session.commit()
        return result.rowcount > 0

    async def delete(self, trip_id: int) -> bool:
        """Soft delete trip"""
        stmt = update(TripORM).where(TripORM.id == trip_id).values(
            is_active=False,
            status=TripStatusEnum.CANCELLED,
            updated_at=datetime.utcnow()
        )
        result = await self._session.execute(stmt)
        await self._session.commit()
        return result.rowcount > 0

    async def exists(self, trip_id: int) -> bool:
        """Check if trip exists"""
        stmt = select(TripORM.id).where(TripORM.id == trip_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None
```

**Design Notes:**
- Uses `_to_domain()` and `_to_orm()` mappers to maintain Clean Architecture boundary
- All queries use SQLAlchemy 2.0 style (`select()`, not legacy query API)
- JSON roadmap serialization handled in repository (infrastructure concern)
- Async session management via dependency injection (no session creation in repository)

### Alembic Migration

**File**: `alembic/versions/XXXX_create_trips_table.py` (generated via `alembic revision --autogenerate -m "create trips table"`)

```python
"""create trips table

Revision ID: XXXX
Revises: YYYY  # Previous migration (users table)
Create Date: 2025-11-13

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import Enum

# revision identifiers, used by Alembic.
revision = 'XXXX'
down_revision = 'YYYY'  # ID of users table migration
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'trips',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('origin', sa.String(length=200), nullable=False),
        sa.Column('destination', sa.String(length=200), nullable=False),
        sa.Column('departure_date', sa.Date(), nullable=False),
        sa.Column('departure_time', sa.Time(), nullable=False),
        sa.Column('origin_lat', sa.Float(), nullable=True),
        sa.Column('origin_lng', sa.Float(), nullable=True),
        sa.Column('destination_lat', sa.Float(), nullable=True),
        sa.Column('destination_lng', sa.Float(), nullable=True),
        sa.Column('available_seats', sa.Integer(), nullable=False),
        sa.Column('total_seats', sa.Integer(), nullable=False),
        sa.Column('estimated_arrival_time', sa.Time(), nullable=True),
        sa.Column('max_detour_minutes', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('current_detour_minutes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('roadmap', sa.Text(), nullable=False, server_default='[]'),
        sa.Column('driver_id', sa.Integer(), nullable=False),
        sa.Column('status', Enum('active', 'completed', 'cancelled', name='tripstatusenum'), nullable=False, server_default='active'),
        sa.Column('price_per_seat', sa.Float(), nullable=True),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['driver_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for query optimization
    op.create_index('ix_trips_id', 'trips', ['id'])
    op.create_index('ix_trips_departure_date', 'trips', ['departure_date'])
    op.create_index('ix_trips_driver_id', 'trips', ['driver_id'])
    op.create_index('ix_trips_status', 'trips', ['status'])
    op.create_index('ix_trips_is_active', 'trips', ['is_active'])

    # Composite index for common query patterns
    op.create_index('ix_trips_status_active', 'trips', ['status', 'is_active'])

def downgrade() -> None:
    op.drop_index('ix_trips_status_active', table_name='trips')
    op.drop_index('ix_trips_is_active', table_name='trips')
    op.drop_index('ix_trips_status', table_name='trips')
    op.drop_index('ix_trips_driver_id', table_name='trips')
    op.drop_index('ix_trips_departure_date', table_name='trips')
    op.drop_index('ix_trips_id', table_name='trips')
    op.drop_table('trips')
```

**Migration Commands:**
```bash
# Generate migration
alembic revision --autogenerate -m "create trips table"

# Apply migration
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

---

## HTTP Layer

### Request Schemas

**File**: `apps/trips/api/v1/schemas/requests.py`

```python
from pydantic import BaseModel, Field, validator
from datetime import date, time
from typing import Optional

class CreateTripRequest(BaseModel):
    """Request schema for creating a trip"""

    origin: str = Field(..., min_length=3, max_length=200, description="Trip origin city/location")
    destination: str = Field(..., min_length=3, max_length=200, description="Trip destination city/location")
    departure_date: date = Field(..., description="Departure date (YYYY-MM-DD)")
    departure_time: time = Field(..., description="Departure time (HH:MM:SS)")
    available_seats: int = Field(..., ge=1, le=10, description="Number of available seats (1-10)")

    # Optional fields
    price_per_seat: Optional[float] = Field(None, ge=0, description="Price per seat (optional)")
    description: Optional[str] = Field(None, max_length=500, description="Trip description")
    max_detour_minutes: int = Field(default=30, ge=0, le=120, description="Maximum allowed detour in minutes")
    estimated_arrival_time: Optional[time] = Field(None, description="Estimated arrival time")

    @validator('departure_date')
    def validate_future_date(cls, v):
        """Ensure departure date is not in the past"""
        if v < date.today():
            raise ValueError('Departure date must be today or in the future')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "origin": "Cádiz",
                "destination": "Sevilla",
                "departure_date": "2025-12-15",
                "departure_time": "09:00:00",
                "available_seats": 3,
                "price_per_seat": 5.0,
                "description": "Comfortable trip, pets allowed",
                "max_detour_minutes": 30
            }
        }

class UpdateTripRequest(BaseModel):
    """Request schema for updating a trip"""

    available_seats: Optional[int] = Field(None, ge=0, le=10)
    price_per_seat: Optional[float] = Field(None, ge=0)
    description: Optional[str] = Field(None, max_length=500)
    status: Optional[str] = Field(None, description="Trip status: active, completed, cancelled")

    class Config:
        json_schema_extra = {
            "example": {
                "available_seats": 2,
                "price_per_seat": 6.0,
                "description": "Updated description"
            }
        }
```

### Response Schemas

**File**: `apps/trips/api/v1/schemas/responses.py`

```python
from pydantic import BaseModel, Field
from datetime import datetime, date, time
from typing import Optional, List

class TripResponse(BaseModel):
    """Response schema for a single trip"""

    id: int
    origin: str
    destination: str
    departure_date: date
    departure_time: time
    available_seats: int
    total_seats: int
    driver_id: int
    status: str

    # Optional fields
    origin_lat: Optional[float] = None
    origin_lng: Optional[float] = None
    destination_lat: Optional[float] = None
    destination_lng: Optional[float] = None
    estimated_arrival_time: Optional[time] = None
    max_detour_minutes: int
    current_detour_minutes: int
    price_per_seat: Optional[float] = None
    description: Optional[str] = None

    # Timestamps
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "origin": "Cádiz",
                "destination": "Sevilla",
                "departure_date": "2025-12-15",
                "departure_time": "09:00:00",
                "available_seats": 3,
                "total_seats": 3,
                "driver_id": 42,
                "status": "active",
                "max_detour_minutes": 30,
                "current_detour_minutes": 0,
                "price_per_seat": 5.0,
                "description": "Comfortable trip",
                "created_at": "2025-11-13T10:00:00",
                "updated_at": None
            }
        }

class TripListResponse(BaseModel):
    """Response schema for list of trips"""

    trips: List[TripResponse]
    total: int = Field(..., description="Total number of trips returned")
    skip: int = Field(..., description="Pagination offset")
    limit: int = Field(..., description="Pagination limit")

    class Config:
        json_schema_extra = {
            "example": {
                "trips": [],
                "total": 0,
                "skip": 0,
                "limit": 100
            }
        }
```

### FastAPI Endpoints

**File**: `apps/trips/api/v1/views.py`

```python
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from datetime import date

from apps.trips.domain.models import Trip, TripStatus
from apps.trips.domain.repositories.trip_repository import ITripRepository
from apps.trips.infrastructure.dependencies import get_trip_repository
from apps.trips.api.v1.schemas.requests import CreateTripRequest, UpdateTripRequest
from apps.trips.api.v1.schemas.responses import TripResponse, TripListResponse

# Import authentication from users module
from apps.users.infrastructure.dependencies import get_current_user
from apps.users.domain.models import User, UserRole

router = APIRouter()

@router.post("/", response_model=TripResponse, status_code=status.HTTP_201_CREATED)
async def create_trip(
    payload: CreateTripRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    repo: Annotated[ITripRepository, Depends(get_trip_repository)]
):
    """
    Create a new trip.

    **Requirements:**
    - User must be authenticated (JWT token required)
    - User must have driver or both role
    - All required fields must be provided
    - Departure date must be in the future (validated in request schema)

    **Business Rules:**
    - available_seats must be > 0
    - total_seats initialized to available_seats
    - Status defaults to ACTIVE
    """
    # Authorization: only drivers can publish trips
    if current_user.role not in [UserRole.DRIVER, UserRole.BOTH]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only drivers can publish trips"
        )

    # Create domain entity
    trip = Trip(
        origin=payload.origin,
        destination=payload.destination,
        departure_date=payload.departure_date,
        departure_time=payload.departure_time,
        available_seats=payload.available_seats,
        total_seats=payload.available_seats,  # Initially equal
        driver_id=current_user.id,
        price_per_seat=payload.price_per_seat,
        description=payload.description,
        max_detour_minutes=payload.max_detour_minutes,
        estimated_arrival_time=payload.estimated_arrival_time,
        status=TripStatus.ACTIVE
    )

    # Persist to database
    created_trip = await repo.create(trip)

    return TripResponse.model_validate(created_trip)

@router.get("/{trip_id}", response_model=TripResponse)
async def get_trip(
    trip_id: int,
    repo: Annotated[ITripRepository, Depends(get_trip_repository)]
):
    """
    Get trip by ID.

    **Authentication:** Not required (public endpoint)
    """
    trip = await repo.get_by_id(trip_id)
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trip with ID {trip_id} not found"
        )

    return TripResponse.model_validate(trip)

@router.get("/", response_model=TripListResponse)
async def list_trips(
    repo: Annotated[ITripRepository, Depends(get_trip_repository)],
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(100, ge=1, le=500, description="Pagination limit"),
    status: Optional[str] = Query(None, description="Filter by status (active, completed, cancelled)")
):
    """
    List all trips with pagination.

    **Authentication:** Not required (public endpoint)
    **Filters:** Optional status filter
    """
    trips = await repo.get_all(skip=skip, limit=limit, status=status)

    return TripListResponse(
        trips=[TripResponse.model_validate(t) for t in trips],
        total=len(trips),  # TODO: Add count query for accurate total
        skip=skip,
        limit=limit
    )

@router.get("/driver/{driver_id}", response_model=TripListResponse)
async def list_trips_by_driver(
    driver_id: int,
    repo: Annotated[ITripRepository, Depends(get_trip_repository)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500)
):
    """
    List trips by specific driver.

    **Authentication:** Not required (public endpoint)
    """
    trips = await repo.get_by_driver(driver_id, skip=skip, limit=limit)

    return TripListResponse(
        trips=[TripResponse.model_validate(t) for t in trips],
        total=len(trips),
        skip=skip,
        limit=limit
    )

@router.put("/{trip_id}", response_model=TripResponse)
async def update_trip(
    trip_id: int,
    payload: UpdateTripRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    repo: Annotated[ITripRepository, Depends(get_trip_repository)]
):
    """
    Update existing trip.

    **Requirements:**
    - User must be authenticated
    - Only the trip owner (driver) can update

    **Allowed Updates:**
    - available_seats
    - price_per_seat
    - description
    - status
    """
    # Fetch existing trip
    trip = await repo.get_by_id(trip_id)
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trip with ID {trip_id} not found"
        )

    # Authorization: only owner can update
    if trip.driver_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the trip owner can update this trip"
        )

    # Apply updates (only provided fields)
    if payload.available_seats is not None:
        # Business rule: can't exceed total_seats
        if payload.available_seats > trip.total_seats:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Available seats cannot exceed total seats ({trip.total_seats})"
            )
        trip.available_seats = payload.available_seats

    if payload.price_per_seat is not None:
        trip.price_per_seat = payload.price_per_seat

    if payload.description is not None:
        trip.description = payload.description

    if payload.status is not None:
        try:
            trip.status = TripStatus(payload.status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {payload.status}. Must be active, completed, or cancelled"
            )

    # Persist update
    success = await repo.update(trip_id, trip)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update trip"
        )

    # Return updated trip
    updated_trip = await repo.get_by_id(trip_id)
    return TripResponse.model_validate(updated_trip)

@router.delete("/{trip_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trip(
    trip_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    repo: Annotated[ITripRepository, Depends(get_trip_repository)]
):
    """
    Cancel trip (soft delete).

    **Requirements:**
    - User must be authenticated
    - Only the trip owner can cancel

    **Effect:**
    - Sets is_active = False
    - Sets status = CANCELLED
    - Does not physically delete the record
    """
    # Fetch existing trip
    trip = await repo.get_by_id(trip_id)
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trip with ID {trip_id} not found"
        )

    # Authorization: only owner can delete
    if trip.driver_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the trip owner can delete this trip"
        )

    # Soft delete
    success = await repo.delete(trip_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete trip"
        )

    return None  # 204 No Content
```

### Router Registration

**File**: `apps/trips/api/urls.py`

```python
from fastapi import APIRouter
from apps.trips.api.v1.views import router as v1_router

router = APIRouter()
router.include_router(v1_router, tags=["Trips"])
```

**File**: `main.py` (modify)

```python
from fastapi import FastAPI
from apps.trips.api.urls import router as trips_router

app = FastAPI(title="Carpool API")

# Register routers
app.include_router(trips_router, prefix="/api/v1/trips", tags=["Trips"])
```

---

## Error Handling

### Domain Error Mapping

| Domain Error | HTTP Status | Response Format |
|--------------|-------------|-----------------|
| Trip not found | 404 NOT_FOUND | `{"detail": "Trip with ID {id} not found"}` |
| Unauthorized access | 401 UNAUTHORIZED | `{"detail": "Not authenticated"}` |
| Insufficient permissions | 403 FORBIDDEN | `{"detail": "Only drivers can publish trips"}` |
| Ownership violation | 403 FORBIDDEN | `{"detail": "Only the trip owner can update this trip"}` |
| Invalid date (past) | 400 BAD_REQUEST | `{"detail": "Departure date must be in the future"}` |
| Invalid seats | 400 BAD_REQUEST | `{"detail": "Available seats cannot exceed total seats"}` |
| Invalid status | 400 BAD_REQUEST | `{"detail": "Invalid status: {status}"}` |
| Validation error (Pydantic) | 422 UNPROCESSABLE_ENTITY | Pydantic validation error format |
| Database error | 500 INTERNAL_SERVER_ERROR | `{"detail": "Internal server error"}` |

### Exception Handlers

FastAPI automatically handles:
- `HTTPException` - Returns specified status code and detail
- Pydantic validation errors - Returns 422 with validation details
- Uncaught exceptions - Returns 500 (logged internally)

**Custom Error Handler** (optional, add to `main.py`):

```python
from fastapi import Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    """Handle database errors gracefully"""
    # Log the error for debugging
    print(f"Database error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Database error occurred"}
    )
```

---

## Background Tasks

**[Not required for RF-001, reserved for future features]**

When implementing domain events (e.g., `TripCreatedEvent`, `TripCancelledEvent`):

1. Use FastAPI's `BackgroundTasks` for lightweight async tasks
2. For complex workflows, integrate Celery or similar task queue
3. Event handlers should be in `apps/trips/application/event_handlers.py`

**Example** (future):

```python
from fastapi import BackgroundTasks

@router.post("/", response_model=TripResponse)
async def create_trip(
    payload: CreateTripRequest,
    background_tasks: BackgroundTasks,
    ...
):
    created_trip = await repo.create(trip)

    # Emit event in background
    background_tasks.add_task(emit_trip_created_event, created_trip.id)

    return TripResponse.model_validate(created_trip)
```

---

## Testing Strategy

### Unit Tests (Domain Layer)

**File**: `tests/trips/test_domain/test_trip_model.py`

```python
import pytest
from datetime import date, time

from apps.trips.domain.models import Trip, TripStatus

def test_trip_creation():
    """Test trip entity creation"""
    trip = Trip(
        origin="Cádiz",
        destination="Sevilla",
        departure_date=date(2025, 12, 15),
        departure_time=time(9, 0),
        available_seats=3,
        total_seats=3,
        driver_id=42
    )

    assert trip.origin == "Cádiz"
    assert trip.status == TripStatus.ACTIVE
    assert trip.has_available_seats() is True

def test_reserve_seats_success():
    """Test successful seat reservation"""
    trip = Trip(
        available_seats=3,
        total_seats=3,
        driver_id=42
    )

    success = trip.reserve_seats(2)

    assert success is True
    assert trip.available_seats == 1

def test_reserve_seats_insufficient():
    """Test seat reservation with insufficient seats"""
    trip = Trip(
        available_seats=1,
        total_seats=3,
        driver_id=42
    )

    success = trip.reserve_seats(2)

    assert success is False
    assert trip.available_seats == 1  # Unchanged

def test_release_seats():
    """Test releasing reserved seats"""
    trip = Trip(
        available_seats=1,
        total_seats=3,
        driver_id=42
    )

    trip.release_seats(2)

    assert trip.available_seats == 3  # Capped at total_seats
```

### Integration Tests (Repository Layer)

**File**: `tests/trips/test_repositories/test_trip_repository.py`

```python
import pytest
from datetime import date, time

from apps.trips.domain.models import Trip, TripStatus
from apps.trips.infrastructure.repositories.trip_repository import TripRepository

@pytest.mark.asyncio
async def test_create_trip(db_session):
    """Test repository create operation"""
    repo = TripRepository(db_session)

    trip = Trip(
        origin="Cádiz",
        destination="Sevilla",
        departure_date=date(2025, 12, 15),
        departure_time=time(9, 0),
        available_seats=3,
        total_seats=3,
        driver_id=1
    )

    created = await repo.create(trip)

    assert created.id is not None
    assert created.origin == "Cádiz"

@pytest.mark.asyncio
async def test_get_by_id(db_session, sample_trip):
    """Test repository get_by_id operation"""
    repo = TripRepository(db_session)

    trip = await repo.get_by_id(sample_trip.id)

    assert trip is not None
    assert trip.id == sample_trip.id

@pytest.mark.asyncio
async def test_get_by_driver(db_session, sample_trips):
    """Test repository get_by_driver operation"""
    repo = TripRepository(db_session)

    trips = await repo.get_by_driver(driver_id=1)

    assert len(trips) > 0
    assert all(t.driver_id == 1 for t in trips)

@pytest.mark.asyncio
async def test_soft_delete(db_session, sample_trip):
    """Test soft delete operation"""
    repo = TripRepository(db_session)

    success = await repo.delete(sample_trip.id)

    assert success is True

    # Verify trip still exists but is inactive
    trip = await repo.get_by_id(sample_trip.id)
    assert trip.is_active is False
    assert trip.status == TripStatus.CANCELLED
```

**Fixture** (`tests/conftest.py`):

```python
import pytest
from datetime import date, time
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from config.database import Base
from apps.trips.domain.models import Trip
from apps.trips.infrastructure.repositories.trip_repository import TripRepository

@pytest.fixture
async def db_session():
    """Create test database session"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session

    await engine.dispose()

@pytest.fixture
async def sample_trip(db_session):
    """Create sample trip for testing"""
    repo = TripRepository(db_session)
    trip = Trip(
        origin="Cádiz",
        destination="Sevilla",
        departure_date=date(2025, 12, 15),
        departure_time=time(9, 0),
        available_seats=3,
        total_seats=3,
        driver_id=1
    )
    return await repo.create(trip)
```

### API Tests (HTTP Layer)

**File**: `tests/trips/test_api/test_create_trip.py`

```python
import pytest
from httpx import AsyncClient
from datetime import date

from main import app

@pytest.mark.asyncio
async def test_create_trip_success(auth_token_driver):
    """Test successful trip creation"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/trips/",
            headers={"Authorization": f"Bearer {auth_token_driver}"},
            json={
                "origin": "Cádiz",
                "destination": "Sevilla",
                "departure_date": "2025-12-15",
                "departure_time": "09:00:00",
                "available_seats": 3,
                "price_per_seat": 5.0
            }
        )

    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["origin"] == "Cádiz"
    assert data["available_seats"] == 3

@pytest.mark.asyncio
async def test_create_trip_unauthorized():
    """Test trip creation without authentication"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/trips/",
            json={
                "origin": "Cádiz",
                "destination": "Sevilla",
                "departure_date": "2025-12-15",
                "departure_time": "09:00:00",
                "available_seats": 3
            }
        )

    assert response.status_code == 401

@pytest.mark.asyncio
async def test_create_trip_forbidden_passenger(auth_token_passenger):
    """Test trip creation by passenger (should fail)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/trips/",
            headers={"Authorization": f"Bearer {auth_token_passenger}"},
            json={
                "origin": "Cádiz",
                "destination": "Sevilla",
                "departure_date": "2025-12-15",
                "departure_time": "09:00:00",
                "available_seats": 3
            }
        )

    assert response.status_code == 403
    assert "drivers" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_create_trip_past_date(auth_token_driver):
    """Test trip creation with past date"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/trips/",
            headers={"Authorization": f"Bearer {auth_token_driver}"},
            json={
                "origin": "Cádiz",
                "destination": "Sevilla",
                "departure_date": "2020-01-01",
                "departure_time": "09:00:00",
                "available_seats": 3
            }
        )

    assert response.status_code == 422  # Pydantic validation error
    assert "future" in response.text.lower()

@pytest.mark.asyncio
async def test_create_trip_invalid_seats(auth_token_driver):
    """Test trip creation with invalid seat count"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/trips/",
            headers={"Authorization": f"Bearer {auth_token_driver}"},
            json={
                "origin": "Cádiz",
                "destination": "Sevilla",
                "departure_date": "2025-12-15",
                "departure_time": "09:00:00",
                "available_seats": 0  # Invalid: must be >= 1
            }
        )

    assert response.status_code == 422
```

**Fixture** (`tests/conftest.py`):

```python
@pytest.fixture
def auth_token_driver():
    """Generate JWT token for driver user"""
    from apps.users.infrastructure.security import create_access_token
    from apps.users.domain.models import UserRole

    return create_access_token({"sub": "1", "role": UserRole.DRIVER.value})

@pytest.fixture
def auth_token_passenger():
    """Generate JWT token for passenger user"""
    from apps.users.infrastructure.security import create_access_token
    from apps.users.domain.models import UserRole

    return create_access_token({"sub": "2", "role": UserRole.PASSENGER.value})
```

### Contract Tests

**File**: `tests/trips/test_api/test_trip_contracts.py`

```python
import pytest
from httpx import AsyncClient

from main import app

@pytest.mark.asyncio
async def test_trip_response_contract(auth_token_driver, sample_trip_id):
    """Verify TripResponse matches API contract"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(f"/api/v1/trips/{sample_trip_id}")

    assert response.status_code == 200
    data = response.json()

    # Required fields
    assert "id" in data
    assert "origin" in data
    assert "destination" in data
    assert "departure_date" in data
    assert "departure_time" in data
    assert "available_seats" in data
    assert "total_seats" in data
    assert "driver_id" in data
    assert "status" in data
    assert "created_at" in data

    # Field types
    assert isinstance(data["id"], int)
    assert isinstance(data["available_seats"], int)
    assert data["status"] in ["active", "completed", "cancelled"]
```

### Test Coverage Requirements

- **Domain Layer**: 100% coverage (pure logic, easy to test)
- **Repository Layer**: 90%+ coverage (integration tests with test database)
- **HTTP Layer**: 80%+ coverage (focus on authorization, validation, error handling)

**Run Tests:**

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=apps/trips --cov-report=html

# Run specific test file
pytest tests/trips/test_api/test_create_trip.py

# Run with verbose output
pytest -v -s
```

---

## Observability

### Logging

**Strategy**: Use Python's `logging` module with structured logging

**File**: `apps/trips/api/v1/views.py` (add logging)

```python
import logging

logger = logging.getLogger(__name__)

@router.post("/", response_model=TripResponse)
async def create_trip(...):
    logger.info(
        "Creating trip",
        extra={
            "user_id": current_user.id,
            "origin": payload.origin,
            "destination": payload.destination
        }
    )

    created_trip = await repo.create(trip)

    logger.info(
        "Trip created successfully",
        extra={"trip_id": created_trip.id, "driver_id": current_user.id}
    )

    return TripResponse.model_validate(created_trip)
```

**Configuration** (`config/logging.py`):

```python
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        },
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "stream": "ext://sys.stdout"
        }
    },
    "root": {
        "level": "INFO",
        "handlers": ["console"]
    }
}
```

### Metrics

**[Optional for MVP, recommended for production]**

Integrate Prometheus for metrics:

```python
from prometheus_client import Counter, Histogram

trip_created_counter = Counter('trips_created_total', 'Total trips created')
trip_creation_duration = Histogram('trip_creation_duration_seconds', 'Trip creation duration')

@router.post("/", response_model=TripResponse)
async def create_trip(...):
    with trip_creation_duration.time():
        created_trip = await repo.create(trip)
        trip_created_counter.inc()
        return TripResponse.model_validate(created_trip)
```

### Tracing

**[Optional for MVP]**

For distributed tracing with OpenTelemetry:

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

@router.post("/", response_model=TripResponse)
async def create_trip(...):
    with tracer.start_as_current_span("create_trip"):
        created_trip = await repo.create(trip)
        return TripResponse.model_validate(created_trip)
```

---

## Open Questions

1. **User Relationship in TripORM**: Should we add a `back_populates` relationship in `UserORM.trips`?
   - **Recommendation**: Yes, add `trips = relationship("TripORM", back_populates="driver")` to `UserORM` for bidirectional access

2. **Geolocation**: Should trip creation automatically geocode origin/destination addresses?
   - **Recommendation**: Not for MVP. Add manual lat/lng input fields, implement geocoding in RF-006 (matching engine)

3. **Pagination Total Count**: Should we implement a separate count query for accurate pagination totals?
   - **Recommendation**: Yes, add `async def count(...)` method to repository interface and implementation

4. **Trip Search Optimization**: Should we add full-text search indexes for origin/destination?
   - **Recommendation**: SQLite FTS (Full-Text Search) can be added later if performance degrades

5. **Concurrency**: How should we handle concurrent seat reservations (booking race conditions)?
   - **Recommendation**: Implement optimistic locking with version field in RF-003 (reservations)

6. **Time Zone Handling**: Should departure times be stored in UTC or local time?
   - **Recommendation**: Store in UTC, add `timezone` field to Trip model for display purposes

---

## Implementation Checklist

### Phase 1: Domain Layer (Day 1 - 1 hour)
- [ ] Create `apps/trips/domain/` directory structure
- [ ] Define `TripStatus` enum in `domain/models.py`
- [ ] Define `Trip` dataclass in `domain/models.py`
- [ ] Add business logic methods (`has_available_seats()`, `can_accommodate()`)
- [ ] Create `ITripRepository` interface in `domain/repositories/trip_repository.py`
- [ ] Write unit tests for `Trip` entity (`tests/trips/test_domain/test_trip_model.py`)
- [ ] Verify 100% test coverage for domain layer

### Phase 2: Infrastructure Layer (Day 1 - 2 hours)
- [ ] Create `apps/trips/infrastructure/` directory structure
- [ ] Define `TripORM` SQLAlchemy model in `infrastructure/models.py`
- [ ] Add foreign key to `users.id`
- [ ] Implement `TripRepository` in `infrastructure/repositories/trip_repository.py`
- [ ] Add `_to_domain()` and `_to_orm()` mappers
- [ ] Implement all repository methods (create, get_by_id, get_all, etc.)
- [ ] Create dependency injection in `infrastructure/dependencies.py`
- [ ] Generate Alembic migration: `alembic revision --autogenerate -m "create trips table"`
- [ ] Review migration file, apply: `alembic upgrade head`
- [ ] Write repository integration tests (`tests/trips/test_repositories/test_trip_repository.py`)
- [ ] Verify tests pass with in-memory SQLite database

### Phase 3: HTTP Layer (Day 2 - 2 hours)
- [ ] Create `apps/trips/api/v1/` directory structure
- [ ] Define `CreateTripRequest` schema in `api/v1/schemas/requests.py`
- [ ] Define `UpdateTripRequest` schema in `api/v1/schemas/requests.py`
- [ ] Add Pydantic validator for future date
- [ ] Define `TripResponse` schema in `api/v1/schemas/responses.py`
- [ ] Define `TripListResponse` schema in `api/v1/schemas/responses.py`
- [ ] Implement `create_trip` endpoint in `api/v1/views.py`
- [ ] Add authorization check for driver role
- [ ] Implement `get_trip` endpoint
- [ ] Implement `list_trips` endpoint
- [ ] Implement `list_trips_by_driver` endpoint
- [ ] Implement `update_trip` endpoint with ownership check
- [ ] Implement `delete_trip` endpoint (soft delete)
- [ ] Create router in `api/urls.py`
- [ ] Register router in `main.py`

### Phase 4: Testing (Day 2 - 1 hour)
- [ ] Write API tests for `create_trip` (`tests/trips/test_api/test_create_trip.py`)
  - [ ] Test successful creation
  - [ ] Test unauthorized (no token)
  - [ ] Test forbidden (passenger role)
  - [ ] Test past date validation
  - [ ] Test invalid seats
- [ ] Write API tests for `get_trip`
  - [ ] Test successful retrieval
  - [ ] Test 404 not found
- [ ] Write API tests for `list_trips`
  - [ ] Test pagination
  - [ ] Test status filter
- [ ] Write API tests for `update_trip`
  - [ ] Test successful update
  - [ ] Test ownership check
  - [ ] Test seat validation
- [ ] Write API tests for `delete_trip`
  - [ ] Test successful deletion
  - [ ] Test ownership check
- [ ] Write contract tests (`tests/trips/test_api/test_trip_contracts.py`)
- [ ] Run full test suite: `pytest --cov=apps/trips`
- [ ] Verify coverage meets requirements (80%+)

### Phase 5: Integration & Documentation (Day 2-3 - 30 min)
- [ ] Start FastAPI server: `uvicorn main:app --reload`
- [ ] Open Swagger docs: `http://localhost:8000/docs`
- [ ] Test all endpoints in Swagger UI
- [ ] Verify authentication with JWT token from users module
- [ ] Test authorization (driver vs passenger)
- [ ] Verify database persistence (check SQLite file)
- [ ] Manual curl tests (see Verification section below)
- [ ] Update API documentation if needed
- [ ] Mark RF-001 as complete

---

## Verification

### Manual Testing with curl

**Step 1: Authenticate as driver**

```bash
# Login or register driver user (from users module)
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "driver@example.com", "password": "password123"}'

# Save the returned token
export TOKEN="<access_token>"
```

**Step 2: Create trip**

```bash
curl -X POST http://localhost:8000/api/v1/trips/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "origin": "Cádiz",
    "destination": "Sevilla",
    "departure_date": "2025-12-15",
    "departure_time": "09:00:00",
    "available_seats": 3,
    "price_per_seat": 5.0,
    "description": "Comfortable trip, pets allowed"
  }'
```

**Expected Response:**

```json
{
  "id": 1,
  "origin": "Cádiz",
  "destination": "Sevilla",
  "departure_date": "2025-12-15",
  "departure_time": "09:00:00",
  "available_seats": 3,
  "total_seats": 3,
  "driver_id": 1,
  "status": "active",
  "max_detour_minutes": 30,
  "current_detour_minutes": 0,
  "price_per_seat": 5.0,
  "description": "Comfortable trip, pets allowed",
  "created_at": "2025-11-13T10:00:00",
  "updated_at": null
}
```

**Step 3: Get trip**

```bash
curl http://localhost:8000/api/v1/trips/1
```

**Step 4: List trips (public)**

```bash
curl http://localhost:8000/api/v1/trips/

# With pagination
curl "http://localhost:8000/api/v1/trips/?skip=0&limit=10"

# With status filter
curl "http://localhost:8000/api/v1/trips/?status=active"
```

**Step 5: Update trip**

```bash
curl -X PUT http://localhost:8000/api/v1/trips/1 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "available_seats": 2,
    "price_per_seat": 6.0
  }'
```

**Step 6: Delete trip**

```bash
curl -X DELETE http://localhost:8000/api/v1/trips/1 \
  -H "Authorization: Bearer $TOKEN"
```

**Step 7: Verify soft delete**

```bash
# Trip should still be retrievable but with status=cancelled
curl http://localhost:8000/api/v1/trips/1
```

### Swagger UI Testing

1. Navigate to `http://localhost:8000/docs`
2. Click "Authorize" button
3. Enter JWT token in format: `Bearer <token>`
4. Test each endpoint:
   - POST /api/v1/trips/ (requires auth)
   - GET /api/v1/trips/{trip_id} (public)
   - GET /api/v1/trips/ (public)
   - GET /api/v1/trips/driver/{driver_id} (public)
   - PUT /api/v1/trips/{trip_id} (requires auth + ownership)
   - DELETE /api/v1/trips/{trip_id} (requires auth + ownership)

### Database Verification

```bash
# Connect to SQLite database
sqlite3 database.db

# Check trips table structure
.schema trips

# List all trips
SELECT * FROM trips;

# Verify foreign key
SELECT t.id, t.origin, t.destination, u.email
FROM trips t
JOIN users u ON t.driver_id = u.id;

# Verify soft delete
SELECT id, origin, destination, status, is_active FROM trips WHERE id = 1;
```

---

## Next Steps

After completing RF-001, proceed with:

1. **RF-002: Trip Search** - Implement advanced search with geolocation, date ranges, and available seats filter
2. **RF-003: Trip Reservations** - Allow passengers to reserve seats on trips
3. **RF-006: Matching Engine** - Implement route optimization and passenger matching

**Dependencies for Future Features:**
- RF-002 uses `ITripRepository.search()` method (already implemented)
- RF-003 requires adding `Reservation` entity with foreign key to `trips.id`
- RF-006 will enhance Trip model with geolocation and route optimization

---

## Summary

This implementation plan provides a complete roadmap for building the Trip Publication feature (RF-001) using FastAPI + SQLAlchemy async with SQLite3. The architecture maintains Clean Architecture principles with clear layer separation, making the codebase maintainable and testable.

**Key Highlights:**
- Pure domain models with zero framework dependencies
- SQLAlchemy async repository with proper ORM mapping
- FastAPI endpoints with authentication and authorization
- Comprehensive testing strategy (unit, integration, API, contract tests)
- Alembic migration for database schema
- Soft delete pattern for data retention

**Total Estimated Time**: 6-8 hours (2-3 days for full implementation and testing)
