# FastAPI Implementation Plan: RF-003 - Booking/Reservation System

**Status**: READY
**Version**: 1.0.0
**Last Updated**: 2025-11-13
**Related Docs**:
- `.claude/plans/04-RF-003-reserva-trayectos.md` (Functional requirements)
- `.claude/docs/RF-001-publicacion-trayectos/` (Trip dependency)
- `.claude/docs/RF-INF-001-gestion-usuarios/` (User authentication dependency)

---

## Summary

This implementation plan provides comprehensive guidance for building a trip booking/reservation system with strong transaction guarantees and race condition prevention. The feature allows authenticated passengers to reserve seats on published trips with automatic seat availability management, duplicate booking prevention, and proper authorization controls.

**Key Design Decisions:**
- **Database**: SQLite3 with SQLAlchemy async for persistence
- **Concurrency Control**: Row-level locking with `SELECT FOR UPDATE` to prevent race conditions
- **Transactional Integrity**: Database transactions ensure seat consistency across booking and trip updates
- **Business Rules**: Prevent duplicate bookings, validate seat availability, check trip hasn't started
- **Status Management**: Booking lifecycle (pending → confirmed → cancelled)
- **Soft Delete**: Cancelled bookings remain in database for audit trail

**Critical Challenge**: Multiple users booking the last available seat simultaneously must be handled safely with proper locking mechanisms.

**Technology Stack:**
- FastAPI 0.104+ for HTTP layer
- SQLAlchemy 2.0+ async with row-level locking
- SQLite3 with WAL mode for concurrent writes
- Alembic for database migrations
- pytest + httpx for testing concurrent scenarios

---

## Architecture Mapping

### Domain → FastAPI Mapping

| Domain Concept | FastAPI Construct | Location | Notes |
|----------------|-------------------|----------|-------|
| Booking (Entity) | Pure Python dataclass | `apps/trips/domain/models.py` | No framework dependencies |
| BookingStatus (Value Object) | Python Enum | `apps/trips/domain/models.py` | Lifecycle states |
| Create Booking (Command) | POST endpoint | `apps/trips/api/v1/views.py` | Maps to `book_trip()` |
| Cancel Booking (Command) | DELETE endpoint | `apps/trips/api/v1/views.py` | Maps to `cancel_booking()` |
| Get Booking (Query) | GET endpoint | `apps/trips/api/v1/views.py` | Maps to `get_booking()` |
| List Bookings (Query) | GET endpoint | `apps/trips/api/v1/views.py` | User bookings or trip bookings |
| IBookingRepository | Abstract base class | `apps/trips/domain/repositories/booking_repository.py` | Domain interface |
| BookingRepository | SQLAlchemy implementation | `apps/trips/infrastructure/repositories/booking_repository.py` | With locking |
| BookingORM | SQLAlchemy model | `apps/trips/infrastructure/models.py` | Database mapping with FKs |
| BookTripRequest | Pydantic model | `apps/trips/api/v1/schemas/requests.py` | HTTP → Application |
| BookingResponse | Pydantic model | `apps/trips/api/v1/schemas/responses.py` | Application → HTTP |
| BookingService | Application Service | `apps/trips/application/services/booking_service.py` | Orchestrates booking logic |

### Layer Responsibilities

**Domain Layer** (`apps/trips/domain/`)
- Define Booking entity with business rules
- Define BookingStatus enum (pending, confirmed, cancelled)
- Define IBookingRepository interface
- Business logic: `can_be_cancelled()`, `is_active()`
- **Zero dependencies** on FastAPI, SQLAlchemy

**Application Layer** (`apps/trips/application/`)
- `BookingService`: Orchestrates booking creation/cancellation
- Validates business rules (seat availability, no duplicates, driver ≠ passenger)
- Manages transactions across booking + trip updates
- Coordinates repository operations

**Adapters/Infrastructure Layer** (`apps/trips/infrastructure/`)
- Implement BookingRepository with SQLAlchemy
- Define BookingORM model with foreign keys
- Handle row-level locking (`SELECT FOR UPDATE`)
- Manage database transactions
- Provide dependency injection

**HTTP Entrypoints Layer** (`apps/trips/api/`)
- Define FastAPI routers for booking endpoints
- Handle HTTP request/response with Pydantic
- Enforce authentication (JWT required)
- Enforce authorization (only passenger can book, only owner can cancel)
- Translate between HTTP and application layer

### Clean Architecture Dependency Rules

```
HTTP (FastAPI) → Application (BookingService) → Domain
         ↓                    ↓
   Infrastructure (Repositories, ORM)
```

**Enforced Rules:**
- Domain layer: **ONLY** standard library
- Application layer: Can import from Domain
- Infrastructure: Implements Domain interfaces
- HTTP layer: Uses Application services
- **NEVER**: Domain importing FastAPI or SQLAlchemy

---

## File Actions

### Create New Files

**Domain Layer:**
```
apps/trips/domain/
├── models.py                          # ADD: Booking entity, BookingStatus enum
└── repositories/
    └── booking_repository.py          # NEW: IBookingRepository interface
```

**Application Layer:**
```
apps/trips/application/
├── __init__.py                        # NEW: Package marker
└── services/
    ├── __init__.py                    # NEW: Package marker
    └── booking_service.py             # NEW: BookingService with business logic
```

**Infrastructure Layer:**
```
apps/trips/infrastructure/
├── models.py                          # MODIFY: Add BookingORM model
├── dependencies.py                    # MODIFY: Add booking DI
└── repositories/
    └── booking_repository.py          # NEW: BookingRepository with locking
```

**HTTP Layer:**
```
apps/trips/api/v1/
├── schemas/
│   ├── requests.py                    # MODIFY: Add BookTripRequest
│   └── responses.py                   # MODIFY: Add BookingResponse
└── views.py                           # MODIFY: Add booking endpoints
```

**Database Migrations:**
```
alembic/versions/
└── {timestamp}_create_bookings_table.py   # NEW: Alembic migration
```

**Tests:**
```
tests/trips/
├── test_domain/
│   └── test_booking_model.py          # NEW: Domain logic tests
├── test_application/
│   └── test_booking_service.py        # NEW: Service logic tests
├── test_repositories/
│   └── test_booking_repository.py     # NEW: Repository + locking tests
└── test_api/
    ├── test_book_trip.py              # NEW: Booking endpoint tests
    ├── test_cancel_booking.py         # NEW: Cancellation tests
    └── test_concurrent_booking.py     # NEW: Race condition tests
```

### Modify Existing Files

- **`apps/trips/domain/models.py`**: Add `Booking` dataclass and `BookingStatus` enum
- **`apps/trips/infrastructure/models.py`**: Add `BookingORM` SQLAlchemy model
- **`apps/trips/infrastructure/dependencies.py`**: Add `get_booking_repository()`, `get_booking_service()`
- **`apps/trips/api/v1/views.py`**: Add booking endpoints
- **`apps/trips/api/v1/schemas/requests.py`**: Add `BookTripRequest`
- **`apps/trips/api/v1/schemas/responses.py`**: Add `BookingResponse`, `BookingWithTripResponse`
- **`alembic/env.py`**: Import BookingORM for migrations

---

## API Endpoints

| Method | Path | Request Model | Response Model | Use Case | Auth | Authorization |
|--------|------|---------------|----------------|----------|------|---------------|
| POST | `/api/v1/trips/{trip_id}/book` | `BookTripRequest` | `BookingResponse` | Book seats | Yes | Passenger only |
| GET | `/api/v1/bookings/{booking_id}` | None | `BookingWithTripResponse` | Get booking details | Yes | Owner or driver |
| GET | `/api/v1/bookings/my-bookings` | Query params | `BookingListResponse` | List user's bookings | Yes | Authenticated |
| GET | `/api/v1/trips/{trip_id}/bookings` | Query params | `BookingListResponse` | List trip bookings | Yes | Driver only |
| DELETE | `/api/v1/bookings/{booking_id}` | None | `204 No Content` | Cancel booking | Yes | Booking owner |

### Endpoint Details

#### POST /api/v1/trips/{trip_id}/book
**Purpose**: Reserve seat(s) on a trip with transactional safety

**Business Rules:**
1. Trip must exist and be active
2. Trip must not have started (departure_date/time in future)
3. Sufficient seats available (`available_seats >= seats_requested`)
4. User cannot be the trip driver
5. No duplicate active booking for same user+trip
6. Atomic transaction: booking creation + seat decrement

**Concurrency Safety:**
- Uses `SELECT FOR UPDATE` on trip record before checking availability
- Prevents race condition when multiple users book simultaneously
- Transaction rollback if any validation fails

**Request Body**:
```json
{
  "seats_requested": 1,
  "passenger_notes": "Will arrive 5 minutes early",
  "pickup_location": "Plaza de España",
  "dropoff_location": "Universidad de Sevilla"
}
```

**Response (201 Created)**:
```json
{
  "id": 1,
  "trip_id": 42,
  "passenger_id": 5,
  "seats_booked": 1,
  "status": "confirmed",
  "pickup_location": "Plaza de España",
  "dropoff_location": "Universidad de Sevilla",
  "passenger_notes": "Will arrive 5 minutes early",
  "booking_date": "2025-11-13T10:00:00Z",
  "is_active": true,
  "created_at": "2025-11-13T10:00:00Z"
}
```

**Errors**:
- 400: Insufficient seats, duplicate booking, driver cannot book own trip
- 401: Not authenticated
- 403: User is not a passenger
- 404: Trip not found
- 409: Concurrent booking conflict (retry mechanism needed)

#### DELETE /api/v1/bookings/{booking_id}
**Purpose**: Cancel booking and release seats

**Business Rules:**
1. Booking must exist and be active
2. Only booking owner can cancel
3. Booking status must be `confirmed` or `pending`
4. Atomic transaction: booking cancellation + seat increment

**Concurrency Safety:**
- Uses `SELECT FOR UPDATE` on both booking and trip
- Ensures consistent seat release

**Response**: 204 No Content

**Errors**:
- 401: Not authenticated
- 403: Not booking owner
- 404: Booking not found
- 400: Booking already cancelled or cannot be cancelled

---

## Dependencies

### Required Packages

Already available in project (verified in config):
```toml
[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.104.0"
sqlalchemy = {extras = ["asyncio"], version = "^2.0.23"}
aiosqlite = "^0.19.0"
alembic = "^1.12.0"
pydantic = {extras = ["email"], version = "^2.5.0"}

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.0"
pytest-asyncio = "^0.21.0"
httpx = "^0.25.0"
```

### SQLite Concurrent Write Configuration

**CRITICAL**: Enable WAL mode for concurrent writes

**File**: `config/database.py` (add to engine creation)

```python
from sqlalchemy import event

# Enable WAL mode for SQLite (allows concurrent reads + single writer)
@event.listens_for(async_engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
    cursor.execute("PRAGMA busy_timeout=5000")  # Wait 5s for locks
    cursor.close()
```

### Dependency Injection Hierarchy

```
FastAPI Request
    ↓
get_async_session() → AsyncSession (with transaction)
    ↓
get_booking_repository(session) → IBookingRepository
get_trip_repository(session) → ITripRepository
    ↓
get_booking_service(booking_repo, trip_repo) → BookingService
    ↓
Endpoint Handler (book_trip, cancel_booking)
    ↓
get_current_user() → User (authentication)
```

---

## Domain Layer Implementation

### 1. Booking Entity

**File**: `apps/trips/domain/models.py` (append to existing file)

```python
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class BookingStatus(str, Enum):
    """Booking lifecycle states"""
    PENDING = "pending"      # Initial state (payment pending if applicable)
    CONFIRMED = "confirmed"  # Active booking
    CANCELLED = "cancelled"  # User cancelled
    COMPLETED = "completed"  # Trip completed
    NO_SHOW = "no_show"      # Passenger didn't show up


@dataclass
class Booking:
    """
    Booking aggregate root - represents a passenger's reservation on a trip

    Business Rules:
    - passenger_id cannot equal trip's driver_id
    - seats_booked must be <= trip's available_seats
    - only CONFIRMED/PENDING bookings can be cancelled
    - cancellation releases seats back to trip
    """
    # Identity
    id: Optional[int] = None

    # Relationships
    trip_id: int = 0
    passenger_id: int = 0

    # Booking details
    seats_booked: int = 1
    status: BookingStatus = BookingStatus.CONFIRMED

    # Optional fields
    pickup_location: Optional[str] = None
    dropoff_location: Optional[str] = None
    passenger_notes: Optional[str] = None

    # Metadata
    booking_date: datetime = field(default_factory=datetime.utcnow)
    cancellation_date: Optional[datetime] = None
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    def can_be_cancelled(self) -> bool:
        """Check if booking can be cancelled"""
        return (
            self.is_active and
            self.status in (BookingStatus.CONFIRMED, BookingStatus.PENDING)
        )

    def cancel(self) -> None:
        """Cancel booking (business logic)"""
        if not self.can_be_cancelled():
            raise ValueError("Booking cannot be cancelled")

        self.status = BookingStatus.CANCELLED
        self.is_active = False
        self.cancellation_date = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def complete(self) -> None:
        """Mark booking as completed after trip ends"""
        if self.status != BookingStatus.CONFIRMED:
            raise ValueError("Only confirmed bookings can be completed")

        self.status = BookingStatus.COMPLETED
        self.updated_at = datetime.utcnow()
```

**Design Notes**:
- Pure Python dataclass with zero framework dependencies
- Business logic methods (`can_be_cancelled()`, `cancel()`, `complete()`)
- Separate `is_active` flag for soft delete vs `status` for lifecycle
- `cancellation_date` for audit trail

### 2. Repository Interface

**File**: `apps/trips/domain/repositories/booking_repository.py` (NEW)

```python
from abc import ABC, abstractmethod
from typing import Optional, List
from datetime import datetime

from apps.trips.domain.models import Booking


class IBookingRepository(ABC):
    """
    Repository contract for Booking persistence

    Implementations must handle concurrency safely for create/update operations.
    """

    @abstractmethod
    async def create(self, booking: Booking) -> Booking:
        """
        Create new booking

        Returns:
            Booking with assigned id

        Raises:
            Exception if constraint violation (duplicate booking, etc.)
        """
        pass

    @abstractmethod
    async def get_by_id(self, booking_id: int) -> Optional[Booking]:
        """Get booking by ID"""
        pass

    @abstractmethod
    async def get_by_id_for_update(self, booking_id: int) -> Optional[Booking]:
        """
        Get booking by ID with row-level lock (SELECT FOR UPDATE)

        Use when modifying booking to prevent concurrent updates.
        Must be called within a transaction.
        """
        pass

    @abstractmethod
    async def get_by_passenger(
        self,
        passenger_id: int,
        skip: int = 0,
        limit: int = 100,
        include_inactive: bool = False
    ) -> List[Booking]:
        """Get all bookings for a passenger"""
        pass

    @abstractmethod
    async def get_by_trip(
        self,
        trip_id: int,
        skip: int = 0,
        limit: int = 100,
        include_inactive: bool = False
    ) -> List[Booking]:
        """Get all bookings for a trip"""
        pass

    @abstractmethod
    async def exists_active_booking(
        self,
        trip_id: int,
        passenger_id: int
    ) -> bool:
        """
        Check if passenger has active booking on trip

        Used to prevent duplicate bookings.
        """
        pass

    @abstractmethod
    async def update(self, booking_id: int, booking: Booking) -> bool:
        """
        Update existing booking

        Returns:
            True if updated, False if not found
        """
        pass

    @abstractmethod
    async def count_active_bookings_by_trip(self, trip_id: int) -> int:
        """Count active bookings for a trip"""
        pass
```

---

## Infrastructure Layer Implementation

### 1. SQLAlchemy ORM Model

**File**: `apps/trips/infrastructure/models.py` (append to existing file)

```python
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum as SQLEnum, Text
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime
import enum

# Import base and existing models
from config.database import Base
from apps.trips.domain.models import BookingStatus


class BookingStatusEnum(str, enum.Enum):
    """SQLAlchemy-compatible enum"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    NO_SHOW = "no_show"


class BookingORM(Base):
    """
    SQLAlchemy ORM model for bookings table
    Maps to Booking domain entity
    """
    __tablename__ = "bookings"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)

    # Foreign keys
    trip_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("trips.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    passenger_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Booking details
    seats_booked: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        SQLEnum(BookingStatusEnum, native_enum=False, length=20),
        default=BookingStatusEnum.CONFIRMED,
        nullable=False,
        index=True
    )

    # Optional fields
    pickup_location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    dropoff_location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    passenger_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Metadata
    booking_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    cancellation_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, onupdate=datetime.utcnow, nullable=True)

    # Relationships
    trip = relationship("TripORM", back_populates="bookings")
    passenger = relationship("UserORM", foreign_keys=[passenger_id])

    def to_domain(self) -> "Booking":
        """Convert ORM model to domain entity"""
        from apps.trips.domain.models import Booking, BookingStatus

        return Booking(
            id=self.id,
            trip_id=self.trip_id,
            passenger_id=self.passenger_id,
            seats_booked=self.seats_booked,
            status=BookingStatus(self.status.value),
            pickup_location=self.pickup_location,
            dropoff_location=self.dropoff_location,
            passenger_notes=self.passenger_notes,
            booking_date=self.booking_date,
            cancellation_date=self.cancellation_date,
            is_active=self.is_active,
            created_at=self.created_at,
            updated_at=self.updated_at
        )

    @staticmethod
    def from_domain(booking: "Booking") -> "BookingORM":
        """Convert domain entity to ORM model"""
        return BookingORM(
            id=booking.id,
            trip_id=booking.trip_id,
            passenger_id=booking.passenger_id,
            seats_booked=booking.seats_booked,
            status=BookingStatusEnum(booking.status.value),
            pickup_location=booking.pickup_location,
            dropoff_location=booking.dropoff_location,
            passenger_notes=booking.passenger_notes,
            booking_date=booking.booking_date,
            cancellation_date=booking.cancellation_date,
            is_active=booking.is_active,
            created_at=booking.created_at,
            updated_at=booking.updated_at
        )

    def __repr__(self):
        return f"<BookingORM(id={self.id}, trip_id={self.trip_id}, passenger_id={self.passenger_id}, status={self.status})>"
```

**IMPORTANT**: Update `TripORM` to add relationship:

```python
class TripORM(Base):
    # ... existing fields ...

    # Add this relationship
    bookings = relationship("BookingORM", back_populates="trip", cascade="all, delete-orphan")
```

**Design Notes**:
- Foreign keys with CASCADE delete (if trip deleted, bookings deleted)
- Composite index on `(trip_id, passenger_id, is_active)` for duplicate detection
- Indexes on foreign keys for join performance
- `to_domain()` and `from_domain()` for Clean Architecture boundary

### 2. Repository Implementation with Locking

**File**: `apps/trips/infrastructure/repositories/booking_repository.py` (NEW)

```python
from typing import List, Optional
from datetime import datetime

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from apps.trips.domain.models import Booking, BookingStatus
from apps.trips.domain.repositories.booking_repository import IBookingRepository
from apps.trips.infrastructure.models import BookingORM, BookingStatusEnum


class BookingRepository(IBookingRepository):
    """
    SQLAlchemy async implementation of IBookingRepository

    Includes row-level locking for concurrent booking safety.
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, booking: Booking) -> Booking:
        """Create new booking"""
        booking_orm = BookingORM.from_domain(booking)

        self._session.add(booking_orm)
        await self._session.flush()  # Get ID without committing
        await self._session.refresh(booking_orm)

        return booking_orm.to_domain()

    async def get_by_id(self, booking_id: int) -> Optional[Booking]:
        """Get booking by ID without locking"""
        stmt = select(BookingORM).where(BookingORM.id == booking_id)
        result = await self._session.execute(stmt)
        booking_orm = result.scalar_one_or_none()

        return booking_orm.to_domain() if booking_orm else None

    async def get_by_id_for_update(self, booking_id: int) -> Optional[Booking]:
        """
        Get booking by ID with row-level lock

        CRITICAL: Prevents concurrent modifications to same booking.
        Must be called within active transaction.
        """
        stmt = (
            select(BookingORM)
            .where(BookingORM.id == booking_id)
            .with_for_update()  # Row-level lock
        )
        result = await self._session.execute(stmt)
        booking_orm = result.scalar_one_or_none()

        return booking_orm.to_domain() if booking_orm else None

    async def get_by_passenger(
        self,
        passenger_id: int,
        skip: int = 0,
        limit: int = 100,
        include_inactive: bool = False
    ) -> List[Booking]:
        """Get all bookings for a passenger"""
        stmt = select(BookingORM).where(BookingORM.passenger_id == passenger_id)

        if not include_inactive:
            stmt = stmt.where(BookingORM.is_active == True)

        stmt = stmt.order_by(BookingORM.booking_date.desc()).offset(skip).limit(limit)

        result = await self._session.execute(stmt)
        booking_orms = result.scalars().all()

        return [b.to_domain() for b in booking_orms]

    async def get_by_trip(
        self,
        trip_id: int,
        skip: int = 0,
        limit: int = 100,
        include_inactive: bool = False
    ) -> List[Booking]:
        """Get all bookings for a trip"""
        stmt = select(BookingORM).where(BookingORM.trip_id == trip_id)

        if not include_inactive:
            stmt = stmt.where(BookingORM.is_active == True)

        stmt = stmt.order_by(BookingORM.booking_date.asc()).offset(skip).limit(limit)

        result = await self._session.execute(stmt)
        booking_orms = result.scalars().all()

        return [b.to_domain() for b in booking_orms]

    async def exists_active_booking(
        self,
        trip_id: int,
        passenger_id: int
    ) -> bool:
        """Check if passenger has active booking on trip"""
        stmt = select(func.count(BookingORM.id)).where(
            and_(
                BookingORM.trip_id == trip_id,
                BookingORM.passenger_id == passenger_id,
                BookingORM.is_active == True,
                BookingORM.status.in_([
                    BookingStatusEnum.CONFIRMED,
                    BookingStatusEnum.PENDING
                ])
            )
        )

        result = await self._session.execute(stmt)
        count = result.scalar()

        return count > 0

    async def update(self, booking_id: int, booking: Booking) -> bool:
        """Update existing booking"""
        stmt = select(BookingORM).where(BookingORM.id == booking_id)
        result = await self._session.execute(stmt)
        booking_orm = result.scalar_one_or_none()

        if not booking_orm:
            return False

        # Update fields
        booking_orm.seats_booked = booking.seats_booked
        booking_orm.status = BookingStatusEnum(booking.status.value)
        booking_orm.pickup_location = booking.pickup_location
        booking_orm.dropoff_location = booking.dropoff_location
        booking_orm.passenger_notes = booking.passenger_notes
        booking_orm.is_active = booking.is_active
        booking_orm.cancellation_date = booking.cancellation_date
        booking_orm.updated_at = datetime.utcnow()

        await self._session.flush()
        return True

    async def count_active_bookings_by_trip(self, trip_id: int) -> int:
        """Count active bookings for a trip"""
        stmt = select(func.count(BookingORM.id)).where(
            and_(
                BookingORM.trip_id == trip_id,
                BookingORM.is_active == True,
                BookingORM.status.in_([
                    BookingStatusEnum.CONFIRMED,
                    BookingStatusEnum.PENDING
                ])
            )
        )

        result = await self._session.execute(stmt)
        return result.scalar()
```

**Design Notes**:
- `get_by_id_for_update()` uses `.with_for_update()` for row-level lock
- Lock prevents concurrent modifications during booking/cancellation
- `flush()` instead of `commit()` in repository (service manages transactions)
- Efficient queries with indexed columns

---

## Application Layer Implementation

### BookingService with Transaction Management

**File**: `apps/trips/application/services/booking_service.py` (NEW)

```python
from typing import Optional
from datetime import datetime

from fastapi import HTTPException, status

from apps.trips.domain.models import Booking, BookingStatus, Trip
from apps.trips.domain.repositories.booking_repository import IBookingRepository
from apps.trips.domain.repositories.trip_repository import ITripRepository


class BookingService:
    """
    Application service for booking operations

    Orchestrates multi-entity transactions with proper locking.
    Enforces business rules across aggregates.
    """

    def __init__(
        self,
        booking_repo: IBookingRepository,
        trip_repo: ITripRepository
    ):
        self.booking_repo = booking_repo
        self.trip_repo = trip_repo

    async def create_booking(
        self,
        trip_id: int,
        passenger_id: int,
        seats_requested: int = 1,
        pickup_location: Optional[str] = None,
        dropoff_location: Optional[str] = None,
        passenger_notes: Optional[str] = None
    ) -> Booking:
        """
        Create booking with transactional safety and validation

        CRITICAL: Uses row-level locking to prevent race conditions
        when multiple users book simultaneously.

        Business Rules:
        1. Trip exists and is active
        2. Trip hasn't started yet
        3. Sufficient seats available
        4. Passenger is not the driver
        5. No duplicate booking
        6. Atomic: booking creation + seat decrement

        Transaction flow:
        1. Lock trip row (SELECT FOR UPDATE)
        2. Validate all rules
        3. Create booking
        4. Decrement available_seats
        5. Commit (handled by session)

        Raises:
            HTTPException 404: Trip not found
            HTTPException 400: Validation failed
            HTTPException 409: Race condition (should retry)
        """
        # Step 1: Get trip with row-level lock
        trip = await self.trip_repo.get_by_id_for_update(trip_id)

        if not trip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trip not found"
            )

        # Step 2: Validate trip is active
        if not trip.is_active or trip.status != "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Trip is not available for booking"
            )

        # Step 3: Validate trip hasn't started
        now = datetime.now()
        trip_datetime = datetime.combine(trip.departure_date, trip.departure_time)
        if trip_datetime <= now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot book trip that has already started"
            )

        # Step 4: Validate seat availability
        if not trip.can_accommodate(seats_requested):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient seats. Available: {trip.available_seats}, Requested: {seats_requested}"
            )

        # Step 5: Validate passenger is not driver
        if trip.driver_id == passenger_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Driver cannot book their own trip"
            )

        # Step 6: Check for duplicate booking
        has_existing = await self.booking_repo.exists_active_booking(trip_id, passenger_id)
        if has_existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You already have an active booking on this trip"
            )

        # Step 7: Validate seats requested range
        if seats_requested < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Must request at least 1 seat"
            )

        if seats_requested > 10:  # Reasonable limit
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot book more than 10 seats at once"
            )

        # Step 8: Create booking entity
        booking = Booking(
            trip_id=trip_id,
            passenger_id=passenger_id,
            seats_booked=seats_requested,
            status=BookingStatus.CONFIRMED,
            pickup_location=pickup_location,
            dropoff_location=dropoff_location,
            passenger_notes=passenger_notes
        )

        # Step 9: Persist booking
        created_booking = await self.booking_repo.create(booking)

        # Step 10: Decrement available seats
        if not trip.reserve_seats(seats_requested):
            # Should never happen due to validation, but safety check
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to reserve seats"
            )

        await self.trip_repo.update(trip_id, trip)

        # Transaction commits in session dependency
        return created_booking

    async def cancel_booking(
        self,
        booking_id: int,
        user_id: int
    ) -> bool:
        """
        Cancel booking and release seats

        Transaction flow:
        1. Lock booking row (SELECT FOR UPDATE)
        2. Validate ownership and cancellable
        3. Lock trip row
        4. Cancel booking
        5. Increment available_seats
        6. Commit

        Raises:
            HTTPException 404: Booking not found
            HTTPException 403: Not booking owner
            HTTPException 400: Cannot be cancelled
        """
        # Step 1: Get booking with lock
        booking = await self.booking_repo.get_by_id_for_update(booking_id)

        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking not found"
            )

        # Step 2: Validate ownership
        if booking.passenger_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only cancel your own bookings"
            )

        # Step 3: Validate cancellable
        if not booking.can_be_cancelled():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Booking cannot be cancelled (already cancelled or completed)"
            )

        # Step 4: Get trip with lock
        trip = await self.trip_repo.get_by_id_for_update(booking.trip_id)

        if not trip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Associated trip not found"
            )

        # Step 5: Cancel booking
        booking.cancel()
        await self.booking_repo.update(booking_id, booking)

        # Step 6: Release seats
        trip.release_seats(booking.seats_booked)
        await self.trip_repo.update(trip.id, trip)

        # Transaction commits in session dependency
        return True

    async def get_booking_with_authorization(
        self,
        booking_id: int,
        user_id: int
    ) -> Booking:
        """
        Get booking if user is authorized (passenger or driver)

        Raises:
            HTTPException 404: Not found
            HTTPException 403: Unauthorized
        """
        booking = await self.booking_repo.get_by_id(booking_id)

        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking not found"
            )

        # Get trip to check if user is driver
        trip = await self.trip_repo.get_by_id(booking.trip_id)

        if not trip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Associated trip not found"
            )

        # Authorize: passenger or driver
        if booking.passenger_id != user_id and trip.driver_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to view this booking"
            )

        return booking
```

**Design Notes**:
- Orchestrates multi-entity transactions (Booking + Trip)
- Uses repository locking methods (`get_by_id_for_update`)
- Comprehensive validation with descriptive errors
- Transaction managed by SQLAlchemy session (auto-commit/rollback)

---

## HTTP Layer Implementation

### 1. Request Schemas

**File**: `apps/trips/api/v1/schemas/requests.py` (append)

```python
from pydantic import BaseModel, Field
from typing import Optional


class BookTripRequest(BaseModel):
    """Schema for booking a trip"""

    seats_requested: int = Field(
        default=1,
        ge=1,
        le=10,
        description="Number of seats to book (1-10)"
    )
    pickup_location: Optional[str] = Field(
        None,
        max_length=200,
        description="Specific pickup location (optional)"
    )
    dropoff_location: Optional[str] = Field(
        None,
        max_length=200,
        description="Specific dropoff location (optional)"
    )
    passenger_notes: Optional[str] = Field(
        None,
        max_length=500,
        description="Notes for driver (optional)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "seats_requested": 1,
                "pickup_location": "Plaza de España",
                "dropoff_location": "Universidad de Sevilla",
                "passenger_notes": "Will arrive 5 minutes early"
            }
        }
    }
```

### 2. Response Schemas

**File**: `apps/trips/api/v1/schemas/responses.py` (append)

```python
from datetime import datetime
from pydantic import BaseModel
from typing import Optional, List


class BookingResponse(BaseModel):
    """Schema for booking data in API responses"""

    id: int
    trip_id: int
    passenger_id: int
    seats_booked: int
    status: str
    pickup_location: Optional[str] = None
    dropoff_location: Optional[str] = None
    passenger_notes: Optional[str] = None
    booking_date: datetime
    cancellation_date: Optional[datetime] = None
    is_active: bool
    created_at: datetime

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "trip_id": 42,
                "passenger_id": 5,
                "seats_booked": 1,
                "status": "confirmed",
                "pickup_location": "Plaza de España",
                "dropoff_location": None,
                "passenger_notes": "Will arrive early",
                "booking_date": "2025-11-13T10:00:00Z",
                "cancellation_date": None,
                "is_active": True,
                "created_at": "2025-11-13T10:00:00Z"
            }
        }
    }


class BookingWithTripResponse(BaseModel):
    """Schema for booking with trip details"""

    booking: BookingResponse
    trip: TripResponse  # Use existing TripResponse

    model_config = {
        "json_schema_extra": {
            "example": {
                "booking": {
                    "id": 1,
                    "trip_id": 42,
                    "passenger_id": 5,
                    "seats_booked": 1,
                    "status": "confirmed"
                },
                "trip": {
                    "id": 42,
                    "origin": "Cádiz",
                    "destination": "Sevilla",
                    "departure_date": "2025-12-15",
                    "available_seats": 2
                }
            }
        }
    }


class BookingListResponse(BaseModel):
    """Schema for list of bookings"""

    bookings: List[BookingResponse]
    total: int
    skip: int
    limit: int

    model_config = {
        "json_schema_extra": {
            "example": {
                "bookings": [],
                "total": 0,
                "skip": 0,
                "limit": 100
            }
        }
    }
```

### 3. FastAPI Endpoints

**File**: `apps/trips/api/v1/views.py` (append to existing router)

```python
# Add imports at top of file
from apps.trips.application.services.booking_service import BookingService
from apps.trips.infrastructure.dependencies import get_booking_service
from apps.trips.api.v1.schemas.responses import (
    BookingResponse,
    BookingWithTripResponse,
    BookingListResponse
)


# ============= BOOKING ENDPOINTS =============


@router.post(
    "/{trip_id}/book",
    response_model=BookingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Book a trip",
    description="""
    Reserve seat(s) on a trip with transactional safety.

    **Business Rules:**
    - Trip must exist and be active
    - Trip must not have started
    - Sufficient seats available
    - User cannot be the trip driver
    - No duplicate bookings allowed

    **Concurrency Safety:**
    Uses row-level locking to prevent race conditions when multiple
    users book the last available seat simultaneously.
    """
)
async def book_trip(
    trip_id: int,
    payload: BookTripRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    booking_service: Annotated[BookingService, Depends(get_booking_service)]
):
    """Book seats on a trip"""

    # Authorization: only passengers can book
    if not current_user.is_passenger():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only passengers can book trips"
        )

    # Create booking with service (handles all validation)
    created_booking = await booking_service.create_booking(
        trip_id=trip_id,
        passenger_id=current_user.id,
        seats_requested=payload.seats_requested,
        pickup_location=payload.pickup_location,
        dropoff_location=payload.dropoff_location,
        passenger_notes=payload.passenger_notes
    )

    return BookingResponse.model_validate(created_booking)


@router.get(
    "/bookings/{booking_id}",
    response_model=BookingWithTripResponse,
    summary="Get booking details",
    description="Get booking with trip information. Only passenger or driver can access."
)
async def get_booking(
    booking_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    booking_service: Annotated[BookingService, Depends(get_booking_service)],
    trip_repo: Annotated[ITripRepository, Depends(get_trip_repository)]
):
    """Get booking details with authorization"""

    # Service handles authorization check
    booking = await booking_service.get_booking_with_authorization(
        booking_id=booking_id,
        user_id=current_user.id
    )

    # Get associated trip
    trip = await trip_repo.get_by_id(booking.trip_id)
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated trip not found"
        )

    return BookingWithTripResponse(
        booking=BookingResponse.model_validate(booking),
        trip=TripResponse.model_validate(trip)
    )


@router.get(
    "/bookings/my-bookings",
    response_model=BookingListResponse,
    summary="List my bookings",
    description="Get all bookings for the authenticated user"
)
async def list_my_bookings(
    current_user: Annotated[User, Depends(get_current_user)],
    booking_repo: Annotated[IBookingRepository, Depends(get_booking_repository)],
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(100, ge=1, le=500, description="Pagination limit"),
    include_inactive: bool = Query(False, description="Include cancelled bookings")
):
    """List user's bookings"""

    bookings = await booking_repo.get_by_passenger(
        passenger_id=current_user.id,
        skip=skip,
        limit=limit,
        include_inactive=include_inactive
    )

    return BookingListResponse(
        bookings=[BookingResponse.model_validate(b) for b in bookings],
        total=len(bookings),
        skip=skip,
        limit=limit
    )


@router.get(
    "/{trip_id}/bookings",
    response_model=BookingListResponse,
    summary="List trip bookings",
    description="Get all bookings for a trip. Only trip driver can access."
)
async def list_trip_bookings(
    trip_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    trip_repo: Annotated[ITripRepository, Depends(get_trip_repository)],
    booking_repo: Annotated[IBookingRepository, Depends(get_booking_repository)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    include_inactive: bool = Query(False, description="Include cancelled bookings")
):
    """List bookings for a trip (driver only)"""

    # Get trip and verify ownership
    trip = await trip_repo.get_by_id(trip_id)
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found"
        )

    # Authorization: only driver can see bookings
    if trip.driver_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the trip driver can view bookings"
        )

    bookings = await booking_repo.get_by_trip(
        trip_id=trip_id,
        skip=skip,
        limit=limit,
        include_inactive=include_inactive
    )

    return BookingListResponse(
        bookings=[BookingResponse.model_validate(b) for b in bookings],
        total=len(bookings),
        skip=skip,
        limit=limit
    )


@router.delete(
    "/bookings/{booking_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel booking",
    description="Cancel booking and release seats. Only booking owner can cancel."
)
async def cancel_booking(
    booking_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    booking_service: Annotated[BookingService, Depends(get_booking_service)]
):
    """Cancel booking"""

    # Service handles authorization and transaction
    await booking_service.cancel_booking(
        booking_id=booking_id,
        user_id=current_user.id
    )

    return None  # 204 No Content
```

### 4. Dependency Injection

**File**: `apps/trips/infrastructure/dependencies.py` (append)

```python
from apps.trips.domain.repositories.booking_repository import IBookingRepository
from apps.trips.infrastructure.repositories.booking_repository import BookingRepository
from apps.trips.application.services.booking_service import BookingService


async def get_booking_repository(
    session: Annotated[AsyncSession, Depends(get_async_session)]
) -> IBookingRepository:
    """Inject booking repository"""
    return BookingRepository(session)


async def get_booking_service(
    booking_repo: Annotated[IBookingRepository, Depends(get_booking_repository)],
    trip_repo: Annotated[ITripRepository, Depends(get_trip_repository)]
) -> BookingService:
    """Inject booking service with dependencies"""
    return BookingService(booking_repo, trip_repo)
```

---

## Data Persistence

### Alembic Migration

**File**: `alembic/versions/{timestamp}_create_bookings_table.py`

Generate with:
```bash
alembic revision --autogenerate -m "Create bookings table"
```

**Migration content**:

```python
"""Create bookings table

Revision ID: {revision_id}
Revises: {previous_revision}
Create Date: 2025-11-13
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import Enum


# revision identifiers
revision = '{revision_id}'
down_revision = '{previous_revision}'  # trips table migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create bookings table with foreign keys and indexes"""

    op.create_table(
        'bookings',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('trip_id', sa.Integer(), nullable=False),
        sa.Column('passenger_id', sa.Integer(), nullable=False),
        sa.Column('seats_booked', sa.Integer(), nullable=False),
        sa.Column(
            'status',
            Enum('pending', 'confirmed', 'cancelled', 'completed', 'no_show', name='bookingstatusenum'),
            nullable=False,
            server_default='confirmed'
        ),
        sa.Column('pickup_location', sa.String(length=200), nullable=True),
        sa.Column('dropoff_location', sa.String(length=200), nullable=True),
        sa.Column('passenger_notes', sa.Text(), nullable=True),
        sa.Column('booking_date', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('cancellation_date', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True),

        sa.ForeignKeyConstraint(['trip_id'], ['trips.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['passenger_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Indexes for performance
    op.create_index('ix_bookings_id', 'bookings', ['id'])
    op.create_index('ix_bookings_trip_id', 'bookings', ['trip_id'])
    op.create_index('ix_bookings_passenger_id', 'bookings', ['passenger_id'])
    op.create_index('ix_bookings_status', 'bookings', ['status'])
    op.create_index('ix_bookings_is_active', 'bookings', ['is_active'])

    # Composite index for duplicate booking detection
    op.create_index(
        'ix_bookings_trip_passenger_active',
        'bookings',
        ['trip_id', 'passenger_id', 'is_active']
    )


def downgrade() -> None:
    """Drop bookings table"""
    op.drop_index('ix_bookings_trip_passenger_active', table_name='bookings')
    op.drop_index('ix_bookings_is_active', table_name='bookings')
    op.drop_index('ix_bookings_status', table_name='bookings')
    op.drop_index('ix_bookings_passenger_id', table_name='bookings')
    op.drop_index('ix_bookings_trip_id', table_name='bookings')
    op.drop_index('ix_bookings_id', table_name='bookings')
    op.drop_table('bookings')
```

**Run migration**:
```bash
alembic upgrade head
```

---

## Error Handling

### Domain Error Mapping

| Domain Error | HTTP Status | Response Format | Scenario |
|--------------|-------------|-----------------|----------|
| Trip not found | 404 NOT_FOUND | `{"detail": "Trip not found"}` | Invalid trip_id |
| Booking not found | 404 NOT_FOUND | `{"detail": "Booking not found"}` | Invalid booking_id |
| Insufficient seats | 400 BAD_REQUEST | `{"detail": "Insufficient seats. Available: X, Requested: Y"}` | Race condition |
| Duplicate booking | 400 BAD_REQUEST | `{"detail": "You already have an active booking on this trip"}` | User books twice |
| Driver cannot book | 400 BAD_REQUEST | `{"detail": "Driver cannot book their own trip"}` | Driver tries to book |
| Trip started | 400 BAD_REQUEST | `{"detail": "Cannot book trip that has already started"}` | Past departure time |
| Cannot cancel | 400 BAD_REQUEST | `{"detail": "Booking cannot be cancelled"}` | Already cancelled/completed |
| Not booking owner | 403 FORBIDDEN | `{"detail": "You can only cancel your own bookings"}` | Unauthorized cancellation |
| Not passenger role | 403 FORBIDDEN | `{"detail": "Only passengers can book trips"}` | Driver-only user booking |
| Not authorized | 403 FORBIDDEN | `{"detail": "You are not authorized to view this booking"}` | Viewing other's booking |
| Unauthenticated | 401 UNAUTHORIZED | `{"detail": "Not authenticated"}` | Missing JWT token |
| Lock timeout | 409 CONFLICT | `{"detail": "Booking conflict, please retry"}` | Row lock timeout |

---

## Testing Strategy

### 1. Domain Layer Tests

**File**: `tests/trips/test_domain/test_booking_model.py` (NEW)

```python
import pytest
from datetime import datetime

from apps.trips.domain.models import Booking, BookingStatus


def test_booking_creation():
    """Test booking entity creation"""
    booking = Booking(
        trip_id=42,
        passenger_id=5,
        seats_booked=2,
        status=BookingStatus.CONFIRMED
    )

    assert booking.trip_id == 42
    assert booking.passenger_id == 5
    assert booking.seats_booked == 2
    assert booking.is_active is True
    assert booking.can_be_cancelled() is True


def test_booking_can_be_cancelled_confirmed():
    """Test confirmed booking can be cancelled"""
    booking = Booking(
        trip_id=1,
        passenger_id=1,
        status=BookingStatus.CONFIRMED,
        is_active=True
    )

    assert booking.can_be_cancelled() is True


def test_booking_cannot_be_cancelled_already_cancelled():
    """Test cancelled booking cannot be cancelled again"""
    booking = Booking(
        trip_id=1,
        passenger_id=1,
        status=BookingStatus.CANCELLED,
        is_active=False
    )

    assert booking.can_be_cancelled() is False


def test_booking_cancel():
    """Test booking cancellation business logic"""
    booking = Booking(
        trip_id=1,
        passenger_id=1,
        status=BookingStatus.CONFIRMED,
        is_active=True
    )

    booking.cancel()

    assert booking.status == BookingStatus.CANCELLED
    assert booking.is_active is False
    assert booking.cancellation_date is not None


def test_booking_complete():
    """Test booking completion"""
    booking = Booking(
        trip_id=1,
        passenger_id=1,
        status=BookingStatus.CONFIRMED
    )

    booking.complete()

    assert booking.status == BookingStatus.COMPLETED
```

### 2. Repository Tests with Locking

**File**: `tests/trips/test_repositories/test_booking_repository.py` (NEW)

```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from apps.trips.domain.models import Booking, BookingStatus
from apps.trips.infrastructure.repositories.booking_repository import BookingRepository


@pytest.mark.asyncio
async def test_create_booking(db_session: AsyncSession):
    """Test creating a booking"""
    repo = BookingRepository(db_session)

    booking = Booking(
        trip_id=1,
        passenger_id=2,
        seats_booked=1,
        status=BookingStatus.CONFIRMED
    )

    created = await repo.create(booking)
    await db_session.commit()

    assert created.id is not None
    assert created.trip_id == 1
    assert created.passenger_id == 2


@pytest.mark.asyncio
async def test_get_by_id_for_update_locks_row(db_session: AsyncSession):
    """Test row-level locking"""
    repo = BookingRepository(db_session)

    # Create booking
    booking = Booking(trip_id=1, passenger_id=2, seats_booked=1)
    created = await repo.create(booking)
    await db_session.commit()

    # Get with lock (in transaction)
    locked_booking = await repo.get_by_id_for_update(created.id)

    assert locked_booking is not None
    assert locked_booking.id == created.id
    # Row is now locked until transaction commits


@pytest.mark.asyncio
async def test_exists_active_booking(db_session: AsyncSession):
    """Test duplicate booking detection"""
    repo = BookingRepository(db_session)

    # Create booking
    booking = Booking(trip_id=1, passenger_id=2, seats_booked=1)
    await repo.create(booking)
    await db_session.commit()

    # Check exists
    exists = await repo.exists_active_booking(trip_id=1, passenger_id=2)
    assert exists is True

    # Check non-existent
    not_exists = await repo.exists_active_booking(trip_id=1, passenger_id=999)
    assert not_exists is False
```

### 3. Application Service Tests

**File**: `tests/trips/test_application/test_booking_service.py` (NEW)

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta
from fastapi import HTTPException

from apps.trips.application.services.booking_service import BookingService
from apps.trips.domain.models import Booking, Trip, TripStatus, BookingStatus


@pytest.mark.asyncio
async def test_create_booking_success():
    """Test successful booking creation"""
    # Mock repositories
    booking_repo = AsyncMock()
    trip_repo = AsyncMock()

    # Setup trip data
    future_date = datetime.now() + timedelta(days=1)
    trip = Trip(
        id=1,
        driver_id=10,
        available_seats=3,
        total_seats=3,
        departure_date=future_date.date(),
        departure_time=future_date.time(),
        status=TripStatus.ACTIVE,
        is_active=True
    )

    trip_repo.get_by_id_for_update.return_value = trip
    booking_repo.exists_active_booking.return_value = False
    booking_repo.create.return_value = Booking(
        id=1,
        trip_id=1,
        passenger_id=5,
        seats_booked=1
    )

    # Create service
    service = BookingService(booking_repo, trip_repo)

    # Execute
    booking = await service.create_booking(
        trip_id=1,
        passenger_id=5,
        seats_requested=1
    )

    # Assertions
    assert booking.id == 1
    assert booking.seats_booked == 1
    booking_repo.create.assert_called_once()
    trip_repo.update.assert_called_once()


@pytest.mark.asyncio
async def test_create_booking_insufficient_seats():
    """Test booking fails with insufficient seats"""
    booking_repo = AsyncMock()
    trip_repo = AsyncMock()

    future_date = datetime.now() + timedelta(days=1)
    trip = Trip(
        id=1,
        driver_id=10,
        available_seats=1,  # Only 1 seat
        total_seats=3,
        departure_date=future_date.date(),
        departure_time=future_date.time(),
        status=TripStatus.ACTIVE,
        is_active=True
    )

    trip_repo.get_by_id_for_update.return_value = trip

    service = BookingService(booking_repo, trip_repo)

    # Should raise 400 error
    with pytest.raises(HTTPException) as exc_info:
        await service.create_booking(
            trip_id=1,
            passenger_id=5,
            seats_requested=2  # Requesting more than available
        )

    assert exc_info.value.status_code == 400
    assert "Insufficient seats" in exc_info.value.detail


@pytest.mark.asyncio
async def test_create_booking_driver_cannot_book():
    """Test driver cannot book their own trip"""
    booking_repo = AsyncMock()
    trip_repo = AsyncMock()

    future_date = datetime.now() + timedelta(days=1)
    trip = Trip(
        id=1,
        driver_id=5,  # Same as passenger_id below
        available_seats=3,
        total_seats=3,
        departure_date=future_date.date(),
        departure_time=future_date.time(),
        status=TripStatus.ACTIVE,
        is_active=True
    )

    trip_repo.get_by_id_for_update.return_value = trip

    service = BookingService(booking_repo, trip_repo)

    with pytest.raises(HTTPException) as exc_info:
        await service.create_booking(
            trip_id=1,
            passenger_id=5,  # Same as driver
            seats_requested=1
        )

    assert exc_info.value.status_code == 400
    assert "driver cannot book" in exc_info.value.detail.lower()
```

### 4. API Endpoint Tests

**File**: `tests/trips/test_api/test_book_trip.py` (NEW)

```python
import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta

from main import app


@pytest.mark.asyncio
async def test_book_trip_success(client: AsyncClient, auth_token_passenger, sample_trip):
    """Test successful trip booking"""
    response = await client.post(
        f"/api/v1/trips/{sample_trip.id}/book",
        headers={"Authorization": f"Bearer {auth_token_passenger}"},
        json={
            "seats_requested": 1,
            "passenger_notes": "Looking forward to the trip"
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["trip_id"] == sample_trip.id
    assert data["seats_booked"] == 1
    assert data["status"] == "confirmed"


@pytest.mark.asyncio
async def test_book_trip_unauthorized(client: AsyncClient, sample_trip):
    """Test booking without authentication"""
    response = await client.post(
        f"/api/v1/trips/{sample_trip.id}/book",
        json={"seats_requested": 1}
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_book_trip_duplicate_booking(
    client: AsyncClient,
    auth_token_passenger,
    sample_trip
):
    """Test duplicate booking prevention"""
    # First booking
    response1 = await client.post(
        f"/api/v1/trips/{sample_trip.id}/book",
        headers={"Authorization": f"Bearer {auth_token_passenger}"},
        json={"seats_requested": 1}
    )
    assert response1.status_code == 201

    # Second booking (should fail)
    response2 = await client.post(
        f"/api/v1/trips/{sample_trip.id}/book",
        headers={"Authorization": f"Bearer {auth_token_passenger}"},
        json={"seats_requested": 1}
    )
    assert response2.status_code == 400
    assert "already have" in response2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_book_trip_insufficient_seats(
    client: AsyncClient,
    auth_token_passenger,
    sample_trip_one_seat
):
    """Test booking with insufficient seats"""
    response = await client.post(
        f"/api/v1/trips/{sample_trip_one_seat.id}/book",
        headers={"Authorization": f"Bearer {auth_token_passenger}"},
        json={"seats_requested": 2}  # Trip only has 1 seat
    )

    assert response.status_code == 400
    assert "insufficient" in response.json()["detail"].lower()
```

### 5. Concurrent Booking Tests (CRITICAL)

**File**: `tests/trips/test_api/test_concurrent_booking.py` (NEW)

```python
import pytest
import asyncio
from httpx import AsyncClient

from main import app


@pytest.mark.asyncio
async def test_concurrent_booking_last_seat(
    client: AsyncClient,
    auth_tokens_multiple_passengers,
    sample_trip_one_seat
):
    """
    Test race condition: multiple users booking last seat simultaneously

    CRITICAL: Only ONE booking should succeed, others should fail gracefully.
    """
    trip_id = sample_trip_one_seat.id

    # Create 5 concurrent booking requests
    async def book_trip(token):
        try:
            response = await client.post(
                f"/api/v1/trips/{trip_id}/book",
                headers={"Authorization": f"Bearer {token}"},
                json={"seats_requested": 1}
            )
            return response.status_code, response.json()
        except Exception as e:
            return 500, {"error": str(e)}

    # Execute concurrently
    results = await asyncio.gather(
        *[book_trip(token) for token in auth_tokens_multiple_passengers]
    )

    # Verify only one success
    success_count = sum(1 for status, _ in results if status == 201)
    fail_count = sum(1 for status, _ in results if status == 400)

    assert success_count == 1, "Exactly one booking should succeed"
    assert fail_count == 4, "Four bookings should fail gracefully"

    # Verify failed responses have proper error message
    for status, body in results:
        if status == 400:
            assert "insufficient" in body["detail"].lower() or \
                   "already have" in body["detail"].lower()


@pytest.mark.asyncio
async def test_concurrent_cancellation(
    client: AsyncClient,
    auth_token_passenger,
    sample_booking
):
    """
    Test race condition: double cancellation attempt

    Only first cancellation should succeed.
    """
    booking_id = sample_booking.id

    async def cancel_booking():
        try:
            response = await client.delete(
                f"/api/v1/bookings/{booking_id}",
                headers={"Authorization": f"Bearer {auth_token_passenger}"}
            )
            return response.status_code
        except Exception:
            return 500

    # Execute two cancellations concurrently
    results = await asyncio.gather(
        cancel_booking(),
        cancel_booking()
    )

    # One should succeed (204), one should fail (400 or 409)
    success_count = sum(1 for status in results if status == 204)
    assert success_count == 1


@pytest.mark.asyncio
async def test_booking_seat_consistency(
    client: AsyncClient,
    auth_tokens_multiple_passengers,
    sample_trip_three_seats
):
    """
    Test seat count consistency after concurrent bookings

    Trip has 3 seats, 3 users book 1 seat each concurrently.
    After bookings complete, available_seats should be 0.
    """
    trip_id = sample_trip_three_seats.id

    # Book concurrently
    async def book_trip(token):
        return await client.post(
            f"/api/v1/trips/{trip_id}/book",
            headers={"Authorization": f"Bearer {token}"},
            json={"seats_requested": 1}
        )

    await asyncio.gather(*[
        book_trip(token)
        for token in auth_tokens_multiple_passengers[:3]
    ])

    # Check trip has 0 available seats
    trip_response = await client.get(f"/api/v1/trips/{trip_id}")
    trip_data = trip_response.json()

    assert trip_data["available_seats"] == 0

    # Fourth booking should fail
    response = await client.post(
        f"/api/v1/trips/{trip_id}/book",
        headers={"Authorization": f"Bearer {auth_tokens_multiple_passengers[3]}"},
        json={"seats_requested": 1}
    )

    assert response.status_code == 400
```

**Fixtures** (`tests/conftest.py` - append):

```python
@pytest.fixture
async def sample_trip_one_seat(db_session, sample_driver):
    """Create trip with only 1 available seat"""
    from apps.trips.infrastructure.repositories.trip_repository import TripRepository
    from apps.trips.domain.models import Trip
    from datetime import datetime, timedelta

    repo = TripRepository(db_session)
    future_date = datetime.now() + timedelta(days=1)

    trip = Trip(
        origin="Cádiz",
        destination="Sevilla",
        departure_date=future_date.date(),
        departure_time=future_date.time(),
        available_seats=1,  # Only 1 seat
        total_seats=1,
        driver_id=sample_driver.id
    )

    created = await repo.create(trip)
    await db_session.commit()
    return created


@pytest.fixture
def auth_tokens_multiple_passengers():
    """Generate JWT tokens for 5 different passengers"""
    from apps.users.infrastructure.auth.jwt import create_access_token

    return [
        create_access_token({"sub": str(i), "role": "passenger"})
        for i in range(100, 105)  # User IDs 100-104
    ]
```

### Test Coverage Requirements

- **Domain Layer**: 95%+ (pure logic, critical business rules)
- **Application Layer**: 90%+ (service orchestration, validation)
- **Repository Layer**: 85%+ (database operations, locking)
- **HTTP Layer**: 80%+ (endpoints, authorization)
- **Concurrent Scenarios**: 100% (race conditions MUST be tested)

**Run tests**:
```bash
# All tests
pytest

# With coverage
pytest --cov=apps/trips --cov-report=html

# Only booking tests
pytest tests/trips/test_api/test_book_trip.py -v

# Only concurrent tests (CRITICAL)
pytest tests/trips/test_api/test_concurrent_booking.py -v -s

# Load test with pytest-xdist (parallel execution)
pytest tests/trips/test_api/test_concurrent_booking.py -n 10
```

---

## Observability

### Logging

Add structured logging to booking operations:

**File**: `apps/trips/application/services/booking_service.py` (add logging)

```python
import logging

logger = logging.getLogger(__name__)


class BookingService:
    async def create_booking(self, ...):
        logger.info(
            "Creating booking",
            extra={
                "trip_id": trip_id,
                "passenger_id": passenger_id,
                "seats_requested": seats_requested
            }
        )

        # ... booking logic ...

        logger.info(
            "Booking created successfully",
            extra={
                "booking_id": created_booking.id,
                "trip_id": trip_id,
                "seats_remaining": trip.available_seats
            }
        )

        return created_booking
```

### Metrics (Optional - Production)

Track booking metrics with Prometheus:

```python
from prometheus_client import Counter, Histogram

booking_created_counter = Counter(
    'bookings_created_total',
    'Total bookings created',
    ['trip_id', 'status']
)

booking_duration = Histogram(
    'booking_creation_duration_seconds',
    'Booking creation duration'
)

@router.post("/{trip_id}/book")
async def book_trip(...):
    with booking_duration.time():
        booking = await booking_service.create_booking(...)
        booking_created_counter.labels(
            trip_id=trip_id,
            status='success'
        ).inc()
        return BookingResponse.model_validate(booking)
```

---

## Open Questions

1. **Payment Integration**: Should bookings require payment before confirmation?
   - **Recommendation**: MVP uses `status=confirmed` immediately. Add payment in Phase 2 with `status=pending`.

2. **Cancellation Deadline**: Should there be a deadline (e.g., 24h before departure)?
   - **Recommendation**: Add `cancellation_deadline_hours` field to Trip model in future iteration.

3. **Overbooking**: Should we allow overbooking with waitlist?
   - **Recommendation**: Not for MVP. Strict seat limit enforcement.

4. **Notification System**: Should users receive email/push notifications?
   - **Recommendation**: Add background task integration in Phase 2.

5. **Booking Modification**: Should passengers be able to change seat count?
   - **Recommendation**: Not for MVP. Cancel and rebook instead.

6. **Driver Approval**: Should bookings require driver approval?
   - **Recommendation**: MVP auto-confirms. Add approval workflow in Phase 2.

---

## Implementation Checklist

### Phase 1: Domain Layer (2 hours)
- [ ] Add `BookingStatus` enum to `domain/models.py`
- [ ] Add `Booking` dataclass to `domain/models.py`
- [ ] Implement business logic methods (`can_be_cancelled()`, `cancel()`)
- [ ] Create `IBookingRepository` interface
- [ ] Write domain unit tests (`test_booking_model.py`)
- [ ] Verify 95%+ test coverage for domain

### Phase 2: Infrastructure Layer (3 hours)
- [ ] Add `BookingORM` model to `infrastructure/models.py`
- [ ] Add `bookings` relationship to `TripORM`
- [ ] Create `BookingRepository` implementation with locking
- [ ] Implement `get_by_id_for_update()` with `SELECT FOR UPDATE`
- [ ] Add SQLite WAL mode configuration to `config/database.py`
- [ ] Generate Alembic migration: `alembic revision --autogenerate -m "Create bookings table"`
- [ ] Review migration, add composite indexes
- [ ] Run migration: `alembic upgrade head`
- [ ] Write repository tests with locking scenarios
- [ ] Verify database schema in SQLite browser

### Phase 3: Application Layer (2 hours)
- [ ] Create `apps/trips/application/services/` directory
- [ ] Implement `BookingService` class
- [ ] Implement `create_booking()` with validation and locking
- [ ] Implement `cancel_booking()` with transaction management
- [ ] Implement `get_booking_with_authorization()`
- [ ] Add comprehensive error handling with HTTPExceptions
- [ ] Write service unit tests with mocks
- [ ] Test all business rule validations

### Phase 4: HTTP Layer (2 hours)
- [ ] Add `BookTripRequest` to `api/v1/schemas/requests.py`
- [ ] Add `BookingResponse`, `BookingWithTripResponse`, `BookingListResponse` to responses
- [ ] Implement `POST /{trip_id}/book` endpoint
- [ ] Implement `GET /bookings/{booking_id}` endpoint
- [ ] Implement `GET /bookings/my-bookings` endpoint
- [ ] Implement `GET /{trip_id}/bookings` endpoint (driver only)
- [ ] Implement `DELETE /bookings/{booking_id}` endpoint
- [ ] Add dependency injection for booking service
- [ ] Add authorization checks (passenger role, ownership)

### Phase 5: Testing (4 hours - CRITICAL)
- [ ] Write domain tests (5+ test cases)
- [ ] Write repository tests with locking (8+ test cases)
- [ ] Write application service tests with mocks (10+ test cases)
- [ ] Write API endpoint tests:
  - [ ] Successful booking (201)
  - [ ] Unauthorized (401)
  - [ ] Forbidden (403)
  - [ ] Not found (404)
  - [ ] Insufficient seats (400)
  - [ ] Duplicate booking (400)
  - [ ] Driver cannot book (400)
  - [ ] Trip started (400)
  - [ ] Successful cancellation (204)
  - [ ] Cannot cancel (400)
- [ ] **CRITICAL**: Write concurrent booking tests:
  - [ ] Multiple users booking last seat
  - [ ] Double cancellation attempt
  - [ ] Seat consistency after concurrent bookings
- [ ] Run full test suite: `pytest --cov=apps/trips -v`
- [ ] Verify 80%+ overall coverage
- [ ] Load test with `pytest -n 10` (parallel execution)

### Phase 6: Integration & Verification (1 hour)
- [ ] Start server: `uvicorn main:app --reload`
- [ ] Open Swagger docs: `http://localhost:8000/docs`
- [ ] Manual testing in Swagger:
  - [ ] Book trip as passenger
  - [ ] Try booking same trip twice
  - [ ] Try booking trip with insufficient seats
  - [ ] Try booking as driver (own trip)
  - [ ] Cancel booking
  - [ ] Try cancelling already cancelled booking
  - [ ] List my bookings
  - [ ] List trip bookings as driver
- [ ] Verify database state after operations
- [ ] Test with multiple concurrent curl requests
- [ ] Check logs for proper error messages

### Phase 7: Documentation (30 min)
- [ ] Update OpenAPI/Swagger descriptions
- [ ] Add code comments for complex logic
- [ ] Document race condition prevention strategy
- [ ] Create deployment notes (SQLite WAL mode requirement)
- [ ] Update README with booking endpoints

---

## Quick Start Commands

```bash
# Create application services directory
mkdir -p apps/trips/application/services

# Generate migration
alembic revision --autogenerate -m "Create bookings table"

# Apply migration
alembic upgrade head

# Verify schema
sqlite3 carpooling.db ".schema bookings"

# Run tests
pytest tests/trips/test_domain/test_booking_model.py -v
pytest tests/trips/test_repositories/test_booking_repository.py -v
pytest tests/trips/test_api/test_book_trip.py -v

# CRITICAL: Test concurrent scenarios
pytest tests/trips/test_api/test_concurrent_booking.py -v -s

# Run with coverage
pytest --cov=apps/trips --cov-report=html --cov-report=term

# Start server
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Test concurrent bookings with curl (in parallel terminals)
for i in {1..5}; do
  curl -X POST http://localhost:8000/api/v1/trips/1/book \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"seats_requested": 1}' &
done
wait
```

---

## Manual Testing Scenarios

### Scenario 1: Happy Path
1. Create driver user, get token
2. Create trip with 3 seats
3. Create passenger user, get token
4. Book 1 seat → should succeed (201)
5. Check trip → should have 2 available seats
6. Check bookings → should show 1 booking

### Scenario 2: Race Condition (CRITICAL)
1. Create trip with 1 seat
2. Create 5 passenger users
3. Simultaneously execute 5 booking requests
4. Verify only 1 succeeds (201)
5. Verify 4 fail with proper error (400)
6. Verify trip has 0 available seats

### Scenario 3: Cancellation
1. Book trip
2. Cancel booking → should succeed (204)
3. Check trip → should have original seat count
4. Try cancelling again → should fail (400)
5. Check booking → should be inactive

### Scenario 4: Authorization
1. User A books trip
2. User B tries to cancel User A's booking → should fail (403)
3. User A cancels own booking → should succeed (204)

---

## Architecture Validation Checklist

- [ ] Domain layer has ZERO imports from FastAPI/SQLAlchemy?
- [ ] Application service manages transactions correctly?
- [ ] Repository uses row-level locking for updates?
- [ ] Concurrent booking tests pass consistently?
- [ ] Seat count remains consistent after concurrent operations?
- [ ] Authorization properly enforced (passenger/driver/owner)?
- [ ] All endpoints return proper status codes?
- [ ] Business rules validated before persistence?
- [ ] Soft delete implemented (is_active flag)?
- [ ] Foreign keys configured with CASCADE delete?
- [ ] Indexes created for query optimization?
- [ ] SQLite WAL mode enabled for concurrent writes?

---

## Production Considerations

**Database Migration**:
- SQLite: Sufficient for MVP with WAL mode
- PostgreSQL: Recommended for production (better locking, connection pooling)
- Migration path: Change `DATABASE_URL`, rerun migrations

**Concurrency Limits**:
- SQLite: Single writer at a time (readers can be concurrent)
- With WAL mode: Better concurrency, minimal blocking
- For high load: Migrate to PostgreSQL with connection pooling

**Monitoring**:
- Log all booking operations with trip_id, passenger_id
- Alert on high failure rates (may indicate race conditions)
- Track booking_duration_seconds metric

**Scalability**:
- Consider adding booking queue for high-traffic trips
- Implement optimistic locking as alternative to pessimistic
- Add Redis cache for seat availability checks

---

## Summary

This implementation plan provides complete guidance for building a production-ready booking system with:

✅ **Transactional Integrity**: Row-level locking prevents race conditions
✅ **Business Rule Enforcement**: Comprehensive validation at service layer
✅ **Clean Architecture**: Clear separation of domain, application, infrastructure
✅ **Authorization**: Proper role-based access control
✅ **Testing**: Extensive coverage including concurrent scenarios
✅ **Observability**: Structured logging for operations
✅ **Documentation**: API docs with Swagger/OpenAPI

**Critical Success Factors**:
1. Row-level locking (`SELECT FOR UPDATE`) for trip and booking records
2. Comprehensive concurrent booking tests
3. Transaction management at service layer
4. SQLite WAL mode enabled for better concurrency

**Total Estimated Time**: 14-16 hours for complete implementation and testing

---

**End of FastAPI Implementation Plan - RF-003 Booking System**
