# FastAPI Implementation Plan: RF-004 - Listado de Reservas

**Status**: READY
**Version**: 1.0.0
**Last Updated**: 2025-11-13
**Related Docs**:
- `.claude/plans/05-RF-004-listado-reservas.md`
- RF-003 (Booking entity and repository)

---

## Summary

This implementation plan covers two distinct booking list endpoints with proper authorization, efficient SQLAlchemy eager loading, and comprehensive filtering. The system allows passengers to view their bookings and drivers to view bookings on their trips, with different authorization rules for each role.

**Key Features:**
- **GET /bookings** - List authenticated user's bookings as passenger (with trip and driver details)
- **GET /trips/{trip_id}/bookings** - List bookings for a specific trip (driver authorization required)
- SQLAlchemy async with joinedload() to prevent N+1 query problems
- Filter by status (pending, confirmed, cancelled, completed)
- Date range filtering
- Pagination support
- Proper authorization (users see only their data, drivers see only their trips' bookings)

**Architecture Note**: The original functional requirement document was written for MongoDB. This plan adapts all repository methods, queries, and patterns to SQLAlchemy async with SQLite3.

---

## Architecture Mapping

### Domain → FastAPI Mapping

| Domain Concept | FastAPI Construct | Location | Notes |
|---------------|------------------|----------|-------|
| Booking Aggregate | Booking SQLAlchemy Model | `apps/trips/domain/models/booking.py` | Existing entity with relationships |
| Trip Aggregate | Trip SQLAlchemy Model | `apps/trips/domain/models/trip.py` | Related via `booking.trip` |
| User Entity | User SQLAlchemy Model | `apps/users/domain/models/user.py` | Related via `trip.driver` and `booking.passenger` |
| List Passenger Bookings | GET /bookings | `apps/trips/api/v1/bookings.py` | Query user's bookings as passenger |
| List Trip Bookings | GET /trips/{trip_id}/bookings | `apps/trips/api/v1/trips.py` | Query bookings for driver's trip |
| Booking Repository | IBookingRepository + Implementation | `apps/trips/infrastructure/repositories/` | SQLAlchemy async queries |

### Layer Responsibilities

**Domain Layer** (`apps/trips/domain/`):
- `models/booking.py` - Booking SQLAlchemy model with relationships to Trip and User
- `models/trip.py` - Trip model with relationship to Booking collection
- `repositories/booking_repository.py` - Abstract repository interface with query methods

**Application Layer** (not applicable for this feature):
- This is primarily a query/read feature, direct repository access from HTTP layer is acceptable

**Adapters Layer** (`apps/trips/infrastructure/`):
- `repositories/booking_repository.py` - SQLAlchemy implementation with joinedload eager loading
- `dependencies.py` - FastAPI dependency injection for repositories

**HTTP Entrypoints** (`apps/trips/api/v1/`):
- `bookings.py` - Router for GET /bookings endpoint
- `trips.py` - Add GET /trips/{trip_id}/bookings to existing trips router
- `schemas/responses.py` - Response schemas with nested data
- Authorization logic in endpoint handlers

---

## File Actions

### Modify Existing Files

**1. `apps/trips/domain/repositories/booking_repository.py`**
- Add `get_by_passenger_with_relations()` method signature with filters
- Add `get_by_trip_with_relations()` method signature
- Update method signatures to support date range filtering

**2. `apps/trips/infrastructure/repositories/booking_repository.py`**
- Implement `get_by_passenger_with_relations()` using SQLAlchemy async with joinedload
- Implement `get_by_trip_with_relations()` using joinedload
- Add private method `_apply_filters()` for status and date range filtering

**3. `apps/trips/api/v1/schemas/responses.py`**
- Create `BookingWithDetailsResponse` - includes nested trip and driver
- Create `BookingListResponse` - wrapper with pagination metadata
- Ensure UserResponse is imported from users module

**4. `apps/trips/api/v1/trips.py`**
- Add `GET /trips/{trip_id}/bookings` endpoint
- Implement driver authorization (trip must belong to current user)
- Use booking repository with eager loading

### Create New Files

**5. `apps/trips/api/v1/bookings.py`** (NEW)
- Create new router for booking-related endpoints
- Implement `GET /bookings` - list authenticated user's bookings
- Register router in main application

**6. `tests/test_bookings/test_list_bookings.py`** (NEW)
- Test passenger viewing their own bookings
- Test passenger cannot see other users' bookings
- Test driver viewing bookings for their trip
- Test driver cannot view bookings for other drivers' trips
- Test status filters
- Test date range filters
- Test pagination
- Test N+1 query prevention (count queries executed)

**7. `tests/test_bookings/test_list_trip_bookings.py`** (NEW)
- Test driver authorization
- Test non-driver cannot access trip bookings
- Test empty booking lists
- Test with multiple bookings on same trip

---

## SQLAlchemy Models & Relationships

### Expected Relationships

Ensure these relationships exist in your SQLAlchemy models:

**Booking Model** (`apps/trips/domain/models/booking.py`):
```python
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum

class BookingStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(String, primary_key=True)
    trip_id = Column(String, ForeignKey("trips.id"), nullable=False, index=True)
    passenger_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    seats_booked = Column(Integer, nullable=False)
    status = Column(Enum(BookingStatus), nullable=False, default=BookingStatus.CONFIRMED, index=True)
    booking_date = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True, index=True)

    # Relationships (for eager loading)
    trip = relationship("Trip", back_populates="bookings", lazy="select")
    passenger = relationship("User", foreign_keys=[passenger_id], lazy="select")
```

**Trip Model** (`apps/trips/domain/models/trip.py`):
```python
class Trip(Base):
    __tablename__ = "trips"

    id = Column(String, primary_key=True)
    driver_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    # ... other trip fields ...

    # Relationships
    driver = relationship("User", back_populates="trips_as_driver", lazy="select")
    bookings = relationship("Booking", back_populates="trip", lazy="select")
```

**User Model** (`apps/users/domain/models/user.py`):
```python
class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    # ... other user fields ...

    # Relationships
    trips_as_driver = relationship("Trip", back_populates="driver", lazy="select")
    bookings_as_passenger = relationship("Booking", foreign_keys="[Booking.passenger_id]", back_populates="passenger", lazy="select")
```

---

## Repository Interface Updates

### File: `apps/trips/domain/repositories/booking_repository.py`

Update the abstract interface:

```python
from abc import ABC, abstractmethod
from typing import Optional, List
from datetime import datetime
from apps.trips.domain.models.booking import Booking, BookingStatus

class IBookingRepository(ABC):

    @abstractmethod
    async def get_by_id(self, booking_id: str) -> Optional[Booking]:
        """Get booking by ID"""
        pass

    @abstractmethod
    async def get_by_passenger_with_relations(
        self,
        passenger_id: str,
        skip: int = 0,
        limit: int = 100,
        status: Optional[BookingStatus] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> List[Booking]:
        """
        Get all bookings for a passenger with trip and driver eagerly loaded.

        Args:
            passenger_id: The passenger's user ID
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return
            status: Filter by booking status
            from_date: Filter bookings from this date (inclusive)
            to_date: Filter bookings to this date (inclusive)

        Returns:
            List of Booking objects with trip and trip.driver relationships loaded
        """
        pass

    @abstractmethod
    async def get_by_trip_with_relations(
        self,
        trip_id: str,
        skip: int = 0,
        limit: int = 100,
        status: Optional[BookingStatus] = None
    ) -> List[Booking]:
        """
        Get all bookings for a trip with passenger eagerly loaded.

        Args:
            trip_id: The trip ID
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return
            status: Filter by booking status

        Returns:
            List of Booking objects with passenger relationship loaded
        """
        pass

    @abstractmethod
    async def count_by_passenger(
        self,
        passenger_id: str,
        status: Optional[BookingStatus] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> int:
        """Count total bookings for a passenger (for pagination metadata)"""
        pass

    @abstractmethod
    async def count_by_trip(
        self,
        trip_id: str,
        status: Optional[BookingStatus] = None
    ) -> int:
        """Count total bookings for a trip (for pagination metadata)"""
        pass
```

---

## Repository Implementation

### File: `apps/trips/infrastructure/repositories/booking_repository.py`

Implement with SQLAlchemy async and eager loading:

```python
from typing import Optional, List
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from apps.trips.domain.models.booking import Booking, BookingStatus
from apps.trips.domain.repositories.booking_repository import IBookingRepository

class BookingRepository(IBookingRepository):

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_passenger_with_relations(
        self,
        passenger_id: str,
        skip: int = 0,
        limit: int = 100,
        status: Optional[BookingStatus] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> List[Booking]:
        """
        Efficiently load bookings for a passenger with related trip and driver.

        Uses joinedload to prevent N+1 queries:
        - booking -> trip (joinedload)
        - trip -> driver (joinedload)

        This results in a single SQL query with LEFT OUTER JOINs.
        """
        # Build base query with eager loading
        stmt = (
            select(Booking)
            .options(
                joinedload(Booking.trip).joinedload(Trip.driver)  # Single query with joins
            )
            .where(Booking.passenger_id == passenger_id)
            .where(Booking.is_active == True)
        )

        # Apply filters
        stmt = self._apply_filters(stmt, status, from_date, to_date)

        # Order by most recent first
        stmt = stmt.order_by(Booking.booking_date.desc())

        # Apply pagination
        stmt = stmt.offset(skip).limit(limit)

        # Execute query
        result = await self.session.execute(stmt)
        bookings = result.unique().scalars().all()

        return list(bookings)

    async def get_by_trip_with_relations(
        self,
        trip_id: str,
        skip: int = 0,
        limit: int = 100,
        status: Optional[BookingStatus] = None
    ) -> List[Booking]:
        """
        Efficiently load bookings for a trip with passenger details.

        Uses joinedload to prevent N+1 queries:
        - booking -> passenger (joinedload)

        This results in a single SQL query with LEFT OUTER JOIN.
        """
        stmt = (
            select(Booking)
            .options(
                joinedload(Booking.passenger)  # Eager load passenger
            )
            .where(Booking.trip_id == trip_id)
            .where(Booking.is_active == True)
        )

        # Apply status filter
        if status:
            stmt = stmt.where(Booking.status == status)

        # Order by booking date (earliest bookings first)
        stmt = stmt.order_by(Booking.booking_date.asc())

        # Apply pagination
        stmt = stmt.offset(skip).limit(limit)

        # Execute query
        result = await self.session.execute(stmt)
        bookings = result.unique().scalars().all()

        return list(bookings)

    async def count_by_passenger(
        self,
        passenger_id: str,
        status: Optional[BookingStatus] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> int:
        """Count bookings for pagination metadata"""
        stmt = (
            select(func.count(Booking.id))
            .where(Booking.passenger_id == passenger_id)
            .where(Booking.is_active == True)
        )

        stmt = self._apply_filters(stmt, status, from_date, to_date)

        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def count_by_trip(
        self,
        trip_id: str,
        status: Optional[BookingStatus] = None
    ) -> int:
        """Count bookings for a trip"""
        stmt = (
            select(func.count(Booking.id))
            .where(Booking.trip_id == trip_id)
            .where(Booking.is_active == True)
        )

        if status:
            stmt = stmt.where(Booking.status == status)

        result = await self.session.execute(stmt)
        return result.scalar_one()

    def _apply_filters(self, stmt, status, from_date, to_date):
        """Apply common filters to a query statement"""
        if status:
            stmt = stmt.where(Booking.status == status)

        if from_date:
            stmt = stmt.where(Booking.booking_date >= from_date)

        if to_date:
            stmt = stmt.where(Booking.booking_date <= to_date)

        return stmt
```

**Key Points:**
- **`joinedload()`**: Creates a single SQL query with JOINs, avoiding N+1 queries
- **`unique()`**: Required when using joinedload to deduplicate rows
- **Filtering**: Status, date range applied in SQL for efficiency
- **Pagination**: Applied at database level with offset/limit
- **Ordering**: Passenger bookings = most recent first, trip bookings = earliest first

---

## API Schemas

### File: `apps/trips/api/v1/schemas/responses.py`

Define response schemas with nested data:

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from apps.trips.domain.models.booking import BookingStatus

# Import from users module
from apps.users.api.v1.schemas.responses import UserResponse

class TripSummaryResponse(BaseModel):
    """Minimal trip info for booking list responses"""
    id: str
    origin: str
    destination: str
    departure_date: str  # YYYY-MM-DD
    departure_time: str  # HH:MM:SS
    available_seats: int
    price: float

    class Config:
        from_attributes = True

class BookingResponse(BaseModel):
    """Basic booking information"""
    id: str
    trip_id: str
    passenger_id: str
    seats_booked: int
    status: BookingStatus
    booking_date: datetime
    created_at: datetime

    class Config:
        from_attributes = True

class BookingWithDetailsResponse(BaseModel):
    """
    Booking with nested trip and driver details.
    Used for GET /bookings (passenger view).
    """
    id: str
    seats_booked: int
    status: BookingStatus
    booking_date: datetime
    trip: TripSummaryResponse
    driver: UserResponse  # Nested driver information

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "bkg_123",
                "seats_booked": 2,
                "status": "confirmed",
                "booking_date": "2025-11-10T14:30:00Z",
                "trip": {
                    "id": "trip_456",
                    "origin": "Cádiz",
                    "destination": "Sevilla",
                    "departure_date": "2025-11-15",
                    "departure_time": "09:00:00",
                    "available_seats": 3,
                    "price": 12.50
                },
                "driver": {
                    "id": "user_789",
                    "name": "Juan Pérez",
                    "email": "juan@example.com",
                    "phone": "+34612345678"
                }
            }
        }

class BookingWithPassengerResponse(BaseModel):
    """
    Booking with passenger details.
    Used for GET /trips/{trip_id}/bookings (driver view).
    """
    id: str
    seats_booked: int
    status: BookingStatus
    booking_date: datetime
    passenger: UserResponse  # Nested passenger information

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "bkg_123",
                "seats_booked": 1,
                "status": "confirmed",
                "booking_date": "2025-11-10T14:30:00Z",
                "passenger": {
                    "id": "user_101",
                    "name": "María García",
                    "email": "maria@example.com",
                    "phone": "+34698765432"
                }
            }
        }

class PaginationMetadata(BaseModel):
    """Pagination information"""
    total: int = Field(..., description="Total number of items")
    skip: int = Field(..., description="Number of items skipped")
    limit: int = Field(..., description="Maximum items per page")
    count: int = Field(..., description="Number of items in this response")

class BookingListResponse(BaseModel):
    """Paginated list of bookings with metadata"""
    items: List[BookingWithDetailsResponse]
    pagination: PaginationMetadata

class TripBookingListResponse(BaseModel):
    """Paginated list of trip bookings with metadata"""
    items: List[BookingWithPassengerResponse]
    pagination: PaginationMetadata
```

---

## API Endpoints

### Endpoint 1: List User's Bookings (as Passenger)

**File**: `apps/trips/api/v1/bookings.py` (NEW FILE)

```python
from fastapi import APIRouter, Depends, Query, HTTPException, status
from typing import Annotated, Optional
from datetime import datetime

from apps.users.domain.models.user import User
from apps.trips.domain.models.booking import BookingStatus
from apps.trips.domain.repositories.booking_repository import IBookingRepository
from apps.trips.infrastructure.dependencies import get_booking_repository
from apps.users.infrastructure.dependencies import get_current_user
from apps.trips.api.v1.schemas.responses import (
    BookingListResponse,
    BookingWithDetailsResponse,
    PaginationMetadata
)

router = APIRouter(prefix="/bookings", tags=["bookings"])

@router.get("", response_model=BookingListResponse)
async def list_my_bookings(
    current_user: Annotated[User, Depends(get_current_user)],
    booking_repo: Annotated[IBookingRepository, Depends(get_booking_repository)],
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum records to return"),
    status: Optional[BookingStatus] = Query(None, description="Filter by booking status"),
    from_date: Optional[datetime] = Query(None, description="Filter bookings from date (ISO format)"),
    to_date: Optional[datetime] = Query(None, description="Filter bookings to date (ISO format)")
):
    """
    List all bookings for the authenticated user (as passenger).

    **Features:**
    - Includes complete trip information (origin, destination, date, time)
    - Includes driver details (name, email, phone)
    - Filter by booking status
    - Filter by date range
    - Pagination support
    - Ordered by booking date (most recent first)
    - Optimized with eager loading (no N+1 queries)

    **Authorization:**
    - User must be authenticated
    - User sees only their own bookings

    **Examples:**
    - All bookings: `GET /bookings`
    - Only confirmed: `GET /bookings?status=confirmed`
    - Date range: `GET /bookings?from_date=2025-11-01T00:00:00&to_date=2025-11-30T23:59:59`
    - With pagination: `GET /bookings?skip=10&limit=5`

    **Performance:**
    - Uses SQLAlchemy joinedload() for efficient queries
    - Single database query with JOINs (no N+1 problem)
    """

    # Query bookings with eager loading
    bookings = await booking_repo.get_by_passenger_with_relations(
        passenger_id=current_user.id,
        skip=skip,
        limit=limit,
        status=status,
        from_date=from_date,
        to_date=to_date
    )

    # Get total count for pagination metadata
    total = await booking_repo.count_by_passenger(
        passenger_id=current_user.id,
        status=status,
        from_date=from_date,
        to_date=to_date
    )

    # Build response items
    items = [
        BookingWithDetailsResponse(
            id=booking.id,
            seats_booked=booking.seats_booked,
            status=booking.status,
            booking_date=booking.booking_date,
            trip=booking.trip,  # Already loaded via joinedload
            driver=booking.trip.driver  # Already loaded via joinedload
        )
        for booking in bookings
    ]

    return BookingListResponse(
        items=items,
        pagination=PaginationMetadata(
            total=total,
            skip=skip,
            limit=limit,
            count=len(items)
        )
    )
```

### Endpoint 2: List Trip Bookings (for Driver)

**File**: `apps/trips/api/v1/trips.py` (ADD TO EXISTING ROUTER)

```python
from apps.trips.api.v1.schemas.responses import (
    TripBookingListResponse,
    BookingWithPassengerResponse,
    PaginationMetadata
)

# Add to existing trips router

@router.get("/{trip_id}/bookings", response_model=TripBookingListResponse)
async def list_trip_bookings(
    trip_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    trip_repo: Annotated[ITripRepository, Depends(get_trip_repository)],
    booking_repo: Annotated[IBookingRepository, Depends(get_booking_repository)],
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum records to return"),
    status: Optional[BookingStatus] = Query(None, description="Filter by booking status")
):
    """
    List all bookings for a specific trip (driver authorization required).

    **Features:**
    - Includes passenger details for each booking
    - Filter by booking status
    - Pagination support
    - Ordered by booking date (earliest bookings first)
    - Optimized with eager loading (no N+1 queries)

    **Authorization:**
    - User must be authenticated
    - User must be the driver of the trip (trip.driver_id == current_user.id)
    - Returns 403 Forbidden if user is not the driver
    - Returns 404 Not Found if trip doesn't exist

    **Use Cases:**
    - Driver wants to see who booked their trip
    - Driver wants to manage confirmed vs pending bookings
    - Driver wants to contact passengers

    **Examples:**
    - All bookings: `GET /trips/{trip_id}/bookings`
    - Only confirmed: `GET /trips/{trip_id}/bookings?status=confirmed`
    - With pagination: `GET /trips/{trip_id}/bookings?skip=0&limit=10`
    """

    # 1. Verify trip exists
    trip = await trip_repo.get_by_id(trip_id)
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trip with id {trip_id} not found"
        )

    # 2. Verify user is the driver (AUTHORIZATION)
    if trip.driver_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the trip driver can view bookings for this trip"
        )

    # 3. Query bookings with eager loading
    bookings = await booking_repo.get_by_trip_with_relations(
        trip_id=trip_id,
        skip=skip,
        limit=limit,
        status=status
    )

    # 4. Get total count for pagination
    total = await booking_repo.count_by_trip(
        trip_id=trip_id,
        status=status
    )

    # 5. Build response items
    items = [
        BookingWithPassengerResponse(
            id=booking.id,
            seats_booked=booking.seats_booked,
            status=booking.status,
            booking_date=booking.booking_date,
            passenger=booking.passenger  # Already loaded via joinedload
        )
        for booking in bookings
    ]

    return TripBookingListResponse(
        items=items,
        pagination=PaginationMetadata(
            total=total,
            skip=skip,
            limit=limit,
            count=len(items)
        )
    )
```

---

## Dependencies

### Required Packages

```toml
[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.104.0"
pydantic = "^2.5.0"
sqlalchemy = "^2.0.0"
aiosqlite = "^0.19.0"  # Async SQLite driver

[tool.poetry.dev-dependencies]
pytest = "^7.4.0"
pytest-asyncio = "^0.21.0"
httpx = "^0.25.0"
```

### Dependency Injection Setup

**File**: `apps/trips/infrastructure/dependencies.py`

Ensure this exists:

```python
from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from apps.core.database import get_db_session
from apps.trips.domain.repositories.booking_repository import IBookingRepository
from apps.trips.infrastructure.repositories.booking_repository import BookingRepository

async def get_booking_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)]
) -> IBookingRepository:
    """Dependency injection for booking repository"""
    return BookingRepository(session)
```

---

## Testing Strategy

### Integration Tests

#### File: `tests/test_bookings/test_list_bookings.py` (NEW)

```python
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from apps.users.domain.models.user import User
from apps.trips.domain.models.trip import Trip
from apps.trips.domain.models.booking import Booking, BookingStatus


@pytest.mark.asyncio
async def test_list_my_bookings_success(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_token: str,
    current_user: User,
    sample_trip: Trip,
    sample_booking: Booking
):
    """Test: User can list their own bookings"""
    response = await client.get(
        "/api/v1/bookings",
        headers={"Authorization": f"Bearer {auth_token}"}
    )

    assert response.status_code == 200
    data = response.json()

    # Check structure
    assert "items" in data
    assert "pagination" in data
    assert isinstance(data["items"], list)

    # Check pagination metadata
    assert data["pagination"]["total"] >= 1
    assert data["pagination"]["count"] == len(data["items"])

    # Check first item structure
    if len(data["items"]) > 0:
        item = data["items"][0]
        assert "id" in item
        assert "seats_booked" in item
        assert "status" in item
        assert "trip" in item
        assert "driver" in item

        # Check nested trip
        assert "origin" in item["trip"]
        assert "destination" in item["trip"]

        # Check nested driver
        assert "name" in item["driver"]
        assert "email" in item["driver"]


@pytest.mark.asyncio
async def test_list_bookings_filter_by_status(
    client: AsyncClient,
    auth_token: str,
    confirmed_booking: Booking,
    cancelled_booking: Booking
):
    """Test: Filter bookings by status"""
    response = await client.get(
        "/api/v1/bookings?status=confirmed",
        headers={"Authorization": f"Bearer {auth_token}"}
    )

    assert response.status_code == 200
    data = response.json()

    # All items should be confirmed
    for item in data["items"]:
        assert item["status"] == "confirmed"


@pytest.mark.asyncio
async def test_list_bookings_date_range_filter(
    client: AsyncClient,
    auth_token: str,
    old_booking: Booking,
    recent_booking: Booking
):
    """Test: Filter bookings by date range"""
    from_date = (datetime.utcnow() - timedelta(days=7)).isoformat()

    response = await client.get(
        f"/api/v1/bookings?from_date={from_date}",
        headers={"Authorization": f"Bearer {auth_token}"}
    )

    assert response.status_code == 200
    data = response.json()

    # Verify all bookings are within date range
    for item in data["items"]:
        booking_date = datetime.fromisoformat(item["booking_date"].replace("Z", "+00:00"))
        assert booking_date >= datetime.fromisoformat(from_date)


@pytest.mark.asyncio
async def test_list_bookings_pagination(
    client: AsyncClient,
    auth_token: str,
    multiple_bookings: list[Booking]  # Fixture creating 15 bookings
):
    """Test: Pagination works correctly"""
    # First page
    response = await client.get(
        "/api/v1/bookings?skip=0&limit=5",
        headers={"Authorization": f"Bearer {auth_token}"}
    )

    assert response.status_code == 200
    data = response.json()

    assert len(data["items"]) == 5
    assert data["pagination"]["skip"] == 0
    assert data["pagination"]["limit"] == 5
    assert data["pagination"]["total"] == 15

    # Second page
    response = await client.get(
        "/api/v1/bookings?skip=5&limit=5",
        headers={"Authorization": f"Bearer {auth_token}"}
    )

    assert response.status_code == 200
    data = response.json()

    assert len(data["items"]) == 5
    assert data["pagination"]["skip"] == 5


@pytest.mark.asyncio
async def test_list_bookings_empty(
    client: AsyncClient,
    auth_token: str,
    user_without_bookings: User
):
    """Test: User with no bookings gets empty list"""
    response = await client.get(
        "/api/v1/bookings",
        headers={"Authorization": f"Bearer {auth_token}"}
    )

    assert response.status_code == 200
    data = response.json()

    assert len(data["items"]) == 0
    assert data["pagination"]["total"] == 0


@pytest.mark.asyncio
async def test_list_bookings_unauthenticated(client: AsyncClient):
    """Test: Unauthenticated user cannot list bookings"""
    response = await client.get("/api/v1/bookings")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_bookings_ordered_by_date(
    client: AsyncClient,
    auth_token: str,
    bookings_different_dates: list[Booking]
):
    """Test: Bookings are ordered by date (most recent first)"""
    response = await client.get(
        "/api/v1/bookings",
        headers={"Authorization": f"Bearer {auth_token}"}
    )

    assert response.status_code == 200
    data = response.json()

    # Verify descending order
    dates = [datetime.fromisoformat(item["booking_date"].replace("Z", "+00:00"))
             for item in data["items"]]

    for i in range(len(dates) - 1):
        assert dates[i] >= dates[i + 1]
```

#### File: `tests/test_bookings/test_list_trip_bookings.py` (NEW)

```python
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from apps.users.domain.models.user import User
from apps.trips.domain.models.trip import Trip
from apps.trips.domain.models.booking import Booking, BookingStatus


@pytest.mark.asyncio
async def test_list_trip_bookings_as_driver(
    client: AsyncClient,
    auth_token_driver: str,
    driver_user: User,
    driver_trip: Trip,
    trip_bookings: list[Booking]
):
    """Test: Driver can list bookings for their trip"""
    response = await client.get(
        f"/api/v1/trips/{driver_trip.id}/bookings",
        headers={"Authorization": f"Bearer {auth_token_driver}"}
    )

    assert response.status_code == 200
    data = response.json()

    # Check structure
    assert "items" in data
    assert "pagination" in data

    # Check items have passenger info
    for item in data["items"]:
        assert "passenger" in item
        assert "name" in item["passenger"]
        assert "email" in item["passenger"]


@pytest.mark.asyncio
async def test_list_trip_bookings_not_driver_forbidden(
    client: AsyncClient,
    auth_token: str,
    other_user: User,
    driver_trip: Trip
):
    """Test: Non-driver user cannot view trip bookings"""
    response = await client.get(
        f"/api/v1/trips/{driver_trip.id}/bookings",
        headers={"Authorization": f"Bearer {auth_token}"}
    )

    assert response.status_code == 403
    assert "driver" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_list_trip_bookings_trip_not_found(
    client: AsyncClient,
    auth_token: str
):
    """Test: 404 for non-existent trip"""
    response = await client.get(
        "/api/v1/trips/nonexistent_id/bookings",
        headers={"Authorization": f"Bearer {auth_token}"}
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_trip_bookings_filter_status(
    client: AsyncClient,
    auth_token_driver: str,
    driver_trip: Trip,
    confirmed_trip_bookings: list[Booking],
    pending_trip_bookings: list[Booking]
):
    """Test: Filter trip bookings by status"""
    response = await client.get(
        f"/api/v1/trips/{driver_trip.id}/bookings?status=confirmed",
        headers={"Authorization": f"Bearer {auth_token_driver}"}
    )

    assert response.status_code == 200
    data = response.json()

    for item in data["items"]:
        assert item["status"] == "confirmed"


@pytest.mark.asyncio
async def test_list_trip_bookings_pagination(
    client: AsyncClient,
    auth_token_driver: str,
    driver_trip: Trip,
    many_trip_bookings: list[Booking]  # 20 bookings
):
    """Test: Pagination for trip bookings"""
    response = await client.get(
        f"/api/v1/trips/{driver_trip.id}/bookings?skip=0&limit=10",
        headers={"Authorization": f"Bearer {auth_token_driver}"}
    )

    assert response.status_code == 200
    data = response.json()

    assert len(data["items"]) == 10
    assert data["pagination"]["total"] == 20
    assert data["pagination"]["limit"] == 10


@pytest.mark.asyncio
async def test_list_trip_bookings_empty(
    client: AsyncClient,
    auth_token_driver: str,
    driver_trip_no_bookings: Trip
):
    """Test: Trip with no bookings returns empty list"""
    response = await client.get(
        f"/api/v1/trips/{driver_trip_no_bookings.id}/bookings",
        headers={"Authorization": f"Bearer {auth_token_driver}"}
    )

    assert response.status_code == 200
    data = response.json()

    assert len(data["items"]) == 0
    assert data["pagination"]["total"] == 0
```

### N+1 Query Prevention Test

```python
@pytest.mark.asyncio
async def test_no_n_plus_1_queries(
    client: AsyncClient,
    auth_token: str,
    bookings_for_n_plus_1_test: list[Booking],  # 10 bookings
    db_session: AsyncSession
):
    """
    Test: Verify no N+1 query problem.
    Should execute constant number of queries regardless of booking count.
    """
    from sqlalchemy import event

    query_count = []

    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        query_count.append(statement)

    event.listen(db_session.sync_engine, "after_cursor_execute", after_cursor_execute)

    response = await client.get(
        "/api/v1/bookings",
        headers={"Authorization": f"Bearer {auth_token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 10

    # Should be 2 queries max:
    # 1. SELECT bookings with JOINs (trips, users)
    # 2. COUNT query for pagination
    # NOT 10 separate queries for trips or drivers
    assert len(query_count) <= 3, f"Too many queries: {len(query_count)}"
```

---

## Router Registration

### File: `apps/trips/api/v1/__init__.py`

Register the new bookings router:

```python
from fastapi import APIRouter
from apps.trips.api.v1 import trips, bookings

router = APIRouter(prefix="/v1")

router.include_router(trips.router)
router.include_router(bookings.router)  # NEW
```

---

## Error Handling

### Standard Error Responses

All endpoints should return consistent error formats:

**401 Unauthorized** (No auth token):
```json
{
  "detail": "Not authenticated"
}
```

**403 Forbidden** (Not the driver):
```json
{
  "detail": "Only the trip driver can view bookings for this trip"
}
```

**404 Not Found** (Trip doesn't exist):
```json
{
  "detail": "Trip with id {trip_id} not found"
}
```

**422 Validation Error** (Invalid query params):
```json
{
  "detail": [
    {
      "loc": ["query", "status"],
      "msg": "value is not a valid enumeration member",
      "type": "type_error.enum"
    }
  ]
}
```

---

## Performance Considerations

### Query Optimization

**Problem**: Without eager loading, listing 10 bookings would execute:
- 1 query to get bookings
- 10 queries to get trips (one per booking)
- 10 queries to get drivers (one per trip)
- **Total: 21 queries (N+1+1 problem)**

**Solution**: Using `joinedload()`:
- 1 query with LEFT OUTER JOINs for bookings + trips + drivers
- 1 query for count (pagination)
- **Total: 2 queries (constant time)**

### Database Indexes

Ensure these indexes exist for optimal performance:

```python
# In Booking model
passenger_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
trip_id = Column(String, ForeignKey("trips.id"), nullable=False, index=True)
status = Column(Enum(BookingStatus), nullable=False, index=True)
booking_date = Column(DateTime, nullable=False, index=True)
is_active = Column(Boolean, default=True, index=True)
```

**Composite Index** (for common query patterns):
```sql
CREATE INDEX idx_bookings_passenger_status_date
ON bookings(passenger_id, status, booking_date DESC);

CREATE INDEX idx_bookings_trip_status
ON bookings(trip_id, status);
```

---

## Open Questions

1. **Soft Delete Behavior**: Should cancelled bookings be shown in lists, or only active bookings? Currently filtering by `is_active=True`.

2. **Response Size**: `BookingWithDetailsResponse` includes full trip details. Should we use a minimal `TripSummaryResponse` to reduce payload size?

3. **Driver Privacy**: When passengers list their bookings, should driver phone number be visible immediately, or only after booking is confirmed?

4. **Rate Limiting**: Should we add rate limiting to these list endpoints to prevent abuse?

5. **Caching**: For trips with many bookings, should we cache the booking count? (Depends on booking frequency)

6. **Real-time Updates**: If bookings are made while a driver is viewing the list, should they see updates? (Would require WebSocket or polling)

---

## Implementation Checklist

### Phase 1: Database & Repository (2-3 hours)

- [ ] Verify SQLAlchemy models have correct relationships:
  - [ ] `Booking.trip` relationship exists
  - [ ] `Booking.passenger` relationship exists
  - [ ] `Trip.driver` relationship exists
  - [ ] `Trip.bookings` relationship exists
- [ ] Update `IBookingRepository` interface with new methods
- [ ] Implement `get_by_passenger_with_relations()` in `BookingRepository`
- [ ] Implement `get_by_trip_with_relations()` in `BookingRepository`
- [ ] Implement count methods for pagination
- [ ] Add database indexes (passenger_id, trip_id, status, booking_date)
- [ ] Test repository methods in isolation (unit tests)

### Phase 2: API Schemas (1 hour)

- [ ] Create `BookingWithDetailsResponse` schema
- [ ] Create `BookingWithPassengerResponse` schema
- [ ] Create `TripSummaryResponse` schema
- [ ] Create `PaginationMetadata` schema
- [ ] Create `BookingListResponse` wrapper
- [ ] Create `TripBookingListResponse` wrapper
- [ ] Import `UserResponse` from users module
- [ ] Add JSON schema examples for documentation

### Phase 3: API Endpoints (3-4 hours)

- [ ] Create `apps/trips/api/v1/bookings.py` file
- [ ] Implement `GET /bookings` endpoint
  - [ ] Add authentication dependency
  - [ ] Add query parameter validation
  - [ ] Call repository with filters
  - [ ] Build response with pagination
  - [ ] Add comprehensive docstring
- [ ] Update `apps/trips/api/v1/trips.py`
  - [ ] Add `GET /trips/{trip_id}/bookings` endpoint
  - [ ] Implement driver authorization check
  - [ ] Call repository with filters
  - [ ] Build response with pagination
  - [ ] Add comprehensive docstring
- [ ] Register bookings router in main app

### Phase 4: Testing (4-5 hours)

- [ ] Create test fixtures:
  - [ ] `sample_booking` fixture
  - [ ] `multiple_bookings` fixture (15+ bookings)
  - [ ] `driver_trip` fixture
  - [ ] `trip_bookings` fixture
  - [ ] `auth_token_driver` fixture
- [ ] Test GET /bookings:
  - [ ] Success case with bookings
  - [ ] Empty list case
  - [ ] Status filter
  - [ ] Date range filter
  - [ ] Pagination (first page, second page)
  - [ ] Ordering (most recent first)
  - [ ] Unauthenticated access (401)
- [ ] Test GET /trips/{trip_id}/bookings:
  - [ ] Success as driver
  - [ ] Forbidden for non-driver (403)
  - [ ] Trip not found (404)
  - [ ] Status filter
  - [ ] Pagination
  - [ ] Empty list
- [ ] Test N+1 query prevention
- [ ] Run full test suite: `pytest tests/test_bookings/ -v`

### Phase 5: Documentation & Verification (1 hour)

- [ ] Verify OpenAPI docs at `/docs`
- [ ] Test all endpoints manually with curl/Postman
- [ ] Verify response examples in Swagger UI
- [ ] Check error responses (401, 403, 404)
- [ ] Verify pagination metadata is correct
- [ ] Test with large dataset (100+ bookings)
- [ ] Measure query performance with SQL logging
- [ ] Update API documentation if needed

### Phase 6: Code Review & Cleanup (1 hour)

- [ ] Code review checklist:
  - [ ] All SQL queries use eager loading
  - [ ] Authorization checks in place
  - [ ] Error messages are clear and helpful
  - [ ] Type hints on all functions
  - [ ] Docstrings on all endpoints
  - [ ] No hardcoded values
  - [ ] Consistent naming conventions
- [ ] Remove any debug print statements
- [ ] Verify no security issues (no exposed sensitive data)
- [ ] Run linter: `ruff check apps/trips/`
- [ ] Run type checker: `mypy apps/trips/`

---

## Success Criteria

✅ **Functional Requirements Met:**
- [ ] Passenger can list all their bookings with trip and driver details
- [ ] Driver can list all bookings for their trips with passenger details
- [ ] Status filtering works (pending, confirmed, cancelled, completed)
- [ ] Date range filtering works
- [ ] Pagination works correctly with metadata
- [ ] Authorization prevents users from seeing others' data
- [ ] Unauthenticated requests are rejected

✅ **Performance Requirements Met:**
- [ ] No N+1 query problem (verified in tests)
- [ ] List 100 bookings completes in < 200ms
- [ ] Database indexes in place
- [ ] Efficient pagination (offset/limit at DB level)

✅ **Code Quality Requirements Met:**
- [ ] All tests pass (100% for new code)
- [ ] Type hints on all functions
- [ ] Docstrings on all public methods
- [ ] Clean Architecture principles followed
- [ ] No coupling between layers

✅ **Documentation Requirements Met:**
- [ ] OpenAPI documentation complete and accurate
- [ ] Examples in Swagger UI
- [ ] Error responses documented
- [ ] Authorization requirements clear

---

## Next Steps After Completion

Once RF-004 is complete and all criteria are met:

1. **RF-006**: Implement advanced matching engine (high complexity)
2. **RF-005**: Add map visualization for routes
3. **Performance Monitoring**: Add logging/metrics for query performance
4. **Caching**: Consider Redis caching for frequent queries
5. **Real-time Updates**: Evaluate WebSocket for live booking updates

---

## Additional Resources

**SQLAlchemy Eager Loading:**
- [SQLAlchemy Relationship Loading Techniques](https://docs.sqlalchemy.org/en/20/orm/queryguide/relationships.html)
- [Avoiding N+1 Queries](https://docs.sqlalchemy.org/en/20/orm/queryguide/relationships.html#joined-eager-loading)

**FastAPI Best Practices:**
- [FastAPI Dependency Injection](https://fastapi.tiangolo.com/tutorial/dependencies/)
- [FastAPI Query Parameters](https://fastapi.tiangolo.com/tutorial/query-params/)

**Testing:**
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
