# FastAPI Implementation Plan: CO2 Emissions Calculation (BONUS)

**Status**: READY
**Feature Type**: BONUS / OPTIONAL
**Version**: 1.0.0
**Last Updated**: 2025-11-13
**Related Docs**:
- `.claude/plans/09-RF-BONUS-002-estimacion-co2-evitado.md`
- Issue #11

---

## Summary

This bonus feature calculates and tracks CO2 emissions avoided through carpooling, providing environmental impact metrics to incentivize platform usage. The implementation follows Clean Architecture principles with a pure domain service for emission calculations, SQLAlchemy async repositories for statistics aggregation, and RESTful endpoints for querying CO2 impact data.

**Key Components:**
1. **Domain Service**: `CO2Calculator` with emission factor formulas (120 g/km gasoline, 105 g/km diesel, 70 g/km hybrid, 0 g/km electric)
2. **Database Layer**: SQLAlchemy async models with aggregation queries for user and trip statistics
3. **API Endpoints**: `GET /trips/{id}/co2-impact` and `GET /users/{id}/co2-stats`
4. **Environmental Equivalences**: Convert kg CO2 to meaningful metrics (trees, car kilometers, flights)

The calculation logic: `CO2_avoided = distance_km × emission_factor × passengers_count`

---

## Architecture Mapping

### Domain → FastAPI Mapping

| Domain Concept | FastAPI Construct | Location | Notes |
|---------------|------------------|----------|-------|
| VehicleType Enum | Enum + EmissionFactors | `domain/models/vehicle.py` | Pure Python enum with emission constants |
| CO2Calculator Service | Domain Service | `domain/services/co2_service.py` | Pure business logic, zero framework dependencies |
| Trip CO2 Fields | SQLAlchemy Model Columns | `adapters/persistence/models.py` | `distance_km`, `co2_saved_per_passenger_kg`, `total_co2_saved_kg` |
| CO2Impact DTO | Pydantic Response Model | `entrypoints/http/schemas/responses.py` | API contract for CO2 data |
| Trip Statistics | Repository Method | `adapters/persistence/repositories/trip_repository.py` | SQLAlchemy aggregation queries |
| User Statistics | Repository Method | `adapters/persistence/repositories/booking_repository.py` | Join queries for user CO2 totals |
| CO2 Endpoints | FastAPI Router | `entrypoints/http/routers/co2_router.py` | Separate router for CO2-specific endpoints |

### Layer Responsibilities

**Domain Layer** (`domain/`):
- `VehicleType` enum: Define vehicle types (gasoline, diesel, hybrid, electric)
- `EmissionFactors` class: Store emission constants (g CO2/km per vehicle type)
- `CO2Calculator` service: Pure calculation logic for emissions, savings, equivalences
- `ICO2Service` interface: Abstract contract for calculation service

**Application Layer** (`application/`):
- `CalculateTripCO2Command`: Command to calculate and persist CO2 data for a trip
- `GetUserCO2StatsQuery`: Query to aggregate user's total CO2 savings
- `GetTripCO2ImpactQuery`: Query to retrieve trip CO2 metrics
- Integration with `BookingService`: Auto-calculate CO2 when bookings are created

**Adapters Layer** (`adapters/`):
- SQLAlchemy models: Add CO2 fields to `Trip` table
- Repository methods: Aggregation queries for statistics
- Migration scripts: Alembic migration to add new columns
- Data migration: Script to backfill CO2 for existing trips

**HTTP Entrypoints** (`entrypoints/http/`):
- `CO2Router`: Dedicated router for CO2 endpoints
- Pydantic schemas: Request/response models for CO2 data
- Dependency injection: Wire CO2 calculator and repositories
- Error handling: Map domain errors to HTTP responses

---

## File Actions

### Create New Files

#### Domain Layer
- `domain/models/vehicle.py`
  - Purpose: Define `VehicleType` enum and `EmissionFactors` constants
  - Contents: Pure Python enums and dataclasses, no framework dependencies

- `domain/services/co2_service.py`
  - Purpose: `CO2Calculator` service with all calculation logic
  - Methods: `calculate_trip_emissions()`, `calculate_savings_per_passenger()`, `calculate_total_savings()`, `get_environmental_equivalence()`, `estimate_yearly_impact()`

- `domain/interfaces/co2_service_interface.py`
  - Purpose: Abstract interface for CO2 calculation service
  - Contents: `ICO2Service` ABC with method signatures

#### Application Layer
- `application/commands/calculate_trip_co2.py`
  - Purpose: Command to calculate and persist CO2 data for a specific trip
  - Handler: `CalculateTripCO2Handler` orchestrates calculation and persistence

- `application/queries/get_user_co2_stats.py`
  - Purpose: Query handler to aggregate user CO2 statistics
  - Handler: `GetUserCO2StatsHandler` uses repository aggregation methods

- `application/queries/get_trip_co2_impact.py`
  - Purpose: Query handler to retrieve trip CO2 metrics
  - Handler: `GetTripCO2ImpactHandler` fetches and enriches trip data

#### Adapters Layer
- `adapters/persistence/alembic/versions/XXXX_add_co2_fields_to_trips.py`
  - Purpose: Alembic migration to add CO2 columns to trips table
  - Columns: `distance_km`, `vehicle_type`, `vehicle_model`, `vehicle_plate`, `co2_saved_per_passenger_kg`, `total_co2_saved_kg`

- `adapters/scripts/backfill_co2_data.py`
  - Purpose: Data migration script to calculate CO2 for existing trips
  - Logic: Query trips with distance > 0, calculate CO2, update records

#### HTTP Entrypoints
- `entrypoints/http/routers/co2_router.py`
  - Purpose: FastAPI router for CO2-specific endpoints
  - Endpoints: `GET /trips/{trip_id}/co2-impact`, `GET /users/me/co2-stats`

- `entrypoints/http/schemas/co2_schemas.py`
  - Purpose: Pydantic models for CO2 requests and responses
  - Models: `CO2ImpactResponse`, `UserCO2StatsResponse`, `EnvironmentalEquivalenceResponse`

#### Testing
- `tests/unit/domain/services/test_co2_calculator.py`
  - Purpose: Unit tests for CO2 calculation formulas
  - Coverage: All calculation methods with various vehicle types and distances

- `tests/integration/test_co2_endpoints.py`
  - Purpose: Integration tests for CO2 API endpoints
  - Coverage: Trip CO2 impact endpoint, user CO2 stats endpoint

- `tests/integration/test_co2_booking_integration.py`
  - Purpose: Test CO2 calculation during booking creation
  - Coverage: Auto-calculation when bookings are made

### Modify Existing Files

- `adapters/persistence/models.py`
  - **Changes**: Add CO2 fields to `Trip` SQLAlchemy model
  - **New Columns**: `distance_km`, `vehicle_type`, `vehicle_model`, `vehicle_plate`, `co2_saved_per_passenger_kg`, `total_co2_saved_kg`
  - **Indexes**: Add index on `vehicle_type` for filtering

- `adapters/persistence/repositories/trip_repository.py`
  - **Changes**: Add method `get_co2_statistics()` for aggregation queries
  - **New Method**: Aggregate total CO2 saved across all trips

- `adapters/persistence/repositories/booking_repository.py`
  - **Changes**: Add method `get_user_co2_stats(user_id)` for user statistics
  - **New Method**: Join bookings with trips, sum CO2 savings per user

- `application/services/booking_service.py`
  - **Changes**: Inject `CO2Calculator`, auto-calculate CO2 when booking is created
  - **Logic**: After booking creation, calculate CO2 based on trip distance and passengers
  - **Update**: Update trip's total CO2 saved

- `entrypoints/http/routers/trip_router.py`
  - **Changes**: Include CO2 data in `TripResponse` schema
  - **New Fields**: `vehicle_type`, `distance_km`, `co2_saved_per_passenger_kg`, `total_co2_saved_kg`

- `entrypoints/http/schemas/trip_schemas.py`
  - **Changes**: Add CO2 fields to `CreateTripRequest` and `TripResponse`
  - **New Request Fields**: `vehicle_type`, `vehicle_model`, `vehicle_plate`
  - **New Response Fields**: `distance_km`, `co2_saved_per_passenger_kg`, `total_co2_saved_kg`, `co2_impact` (nested object)

- `entrypoints/http/dependencies.py`
  - **Changes**: Add dependency for `CO2Calculator` injection
  - **New Dependency**: `get_co2_calculator()` returns singleton instance

- `main.py`
  - **Changes**: Register `co2_router` with FastAPI app
  - **Route**: Mount at `/api/v1/co2`

---

## API Endpoints

### Trip CO2 Impact Endpoint

| Method | Path | Request Model | Response Model | Use Case | Auth |
|--------|------|--------------|----------------|----------|------|
| GET | `/api/v1/trips/{trip_id}/co2-impact` | - | `CO2ImpactResponse` | Retrieve environmental impact of a specific trip | Optional |

**Response Schema: `CO2ImpactResponse`**
```json
{
  "trip_id": "uuid",
  "distance_km": 125.0,
  "vehicle_type": "gasoline",
  "co2_saved_per_passenger_kg": 15.0,
  "total_co2_saved_kg": 30.0,
  "passengers_count": 2,
  "equivalences": {
    "trees_equivalent": 1.4,
    "car_km_equivalent": 250,
    "madrid_barcelona_flights": 0.35,
    "message": "Has evitado 30.0 kg de CO₂. ¡Como no conducir 250 km!"
  }
}
```

**Business Rules:**
- Returns 404 if trip not found
- Returns 400 if trip has no CO2 data (distance = 0 or null)
- Calculates equivalences dynamically using `CO2Calculator.get_environmental_equivalence()`

---

### User CO2 Statistics Endpoint

| Method | Path | Request Model | Response Model | Use Case | Auth |
|--------|------|--------------|----------------|----------|------|
| GET | `/api/v1/users/me/co2-stats` | - | `UserCO2StatsResponse` | Retrieve aggregated CO2 savings for authenticated user | Required |
| GET | `/api/v1/users/{user_id}/co2-stats` | - | `UserCO2StatsResponse` | Retrieve public CO2 stats for any user | Optional |

**Response Schema: `UserCO2StatsResponse`**
```json
{
  "user_id": "uuid",
  "total_co2_saved_kg": 245.5,
  "trips_as_passenger_count": 12,
  "trips_as_driver_count": 8,
  "total_distance_km": 1850.0,
  "equivalences": {
    "trees_equivalent": 11.7,
    "car_km_equivalent": 2045,
    "madrid_barcelona_flights": 2.89,
    "message": "Has evitado 245.5 kg de CO₂. ¡Equivale a 2.89 vuelos Madrid-Barcelona!"
  },
  "monthly_average_kg": 20.5,
  "yearly_projection_kg": 246.0
}
```

**Business Rules:**
- `/me` endpoint requires authentication, returns current user's stats
- `/{user_id}` endpoint is public, allows viewing others' environmental impact
- Only counts confirmed or completed bookings
- Aggregates CO2 from all trips where user was a passenger
- Optionally includes trips where user was a driver (if implemented)

---

### List Top Environmental Contributors (Future Enhancement)

| Method | Path | Request Model | Response Model | Use Case | Auth |
|--------|------|--------------|----------------|----------|------|
| GET | `/api/v1/co2/leaderboard` | Query params: `limit`, `period` | `List[LeaderboardEntryResponse]` | Display top CO2 savers for gamification | Optional |

**Note**: This endpoint is a future enhancement, not required for MVP.

---

## Domain Model: CO2 Calculation

### VehicleType Enum

**File**: `domain/models/vehicle.py`

```python
from enum import Enum

class VehicleType(str, Enum):
    """
    Vehicle types with associated emission factors.
    Values represent real-world average emissions in g CO2/km.
    """
    GASOLINE = "gasoline"
    DIESEL = "diesel"
    HYBRID = "hybrid"
    ELECTRIC = "electric"
```

### EmissionFactors Constants

**File**: `domain/models/vehicle.py`

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class EmissionFactors:
    """
    Standard emission factors in grams CO2 per kilometer.

    Sources:
    - European Environment Agency (EEA) average passenger car emissions 2023
    - Gasoline: 120 g CO2/km
    - Diesel: 105 g CO2/km
    - Hybrid: 70 g CO2/km
    - Electric: 0 g CO2/km (direct emissions only, excludes electricity generation)
    """
    GASOLINE: int = 120
    DIESEL: int = 105
    HYBRID: int = 70
    ELECTRIC: int = 0

    DEFAULT: int = 120  # Default to gasoline if unknown

    @classmethod
    def get_factor(cls, vehicle_type: VehicleType) -> int:
        """
        Get emission factor for a vehicle type.

        Args:
            vehicle_type: The type of vehicle

        Returns:
            Emission factor in g CO2/km
        """
        mapping = {
            VehicleType.GASOLINE: cls.GASOLINE,
            VehicleType.DIESEL: cls.DIESEL,
            VehicleType.HYBRID: cls.HYBRID,
            VehicleType.ELECTRIC: cls.ELECTRIC,
        }
        return mapping.get(vehicle_type, cls.DEFAULT)
```

### CO2Calculator Service

**File**: `domain/services/co2_service.py`

**Key Methods:**

1. **`calculate_trip_emissions(distance_km, vehicle_type) -> float`**
   - Calculates total emissions if the trip were done solo
   - Formula: `emissions_kg = (distance_km × emission_factor) / 1000`
   - Returns: kg CO2

2. **`calculate_savings_per_passenger(distance_km, vehicle_type) -> float`**
   - Calculates CO2 saved by one passenger not driving their own car
   - Logic: Each passenger avoids making the trip in their own vehicle
   - Formula: Same as trip emissions (each passenger saves a full trip's worth)
   - Returns: kg CO2 per passenger

3. **`calculate_total_savings(distance_km, vehicle_type, passengers_count) -> float`**
   - Calculates total CO2 saved across all passengers
   - Formula: `total_kg = savings_per_passenger × passengers_count`
   - Note: `passengers_count` excludes the driver
   - Returns: kg CO2

4. **`get_environmental_equivalence(co2_kg) -> dict`**
   - Converts kg CO2 to relatable metrics
   - Equivalences:
     - **Trees**: 1 tree absorbs ~21 kg CO2/year
     - **Car km**: 1 km in average car = ~0.12 kg CO2
     - **Flights**: Madrid-Barcelona flight = ~85 kg CO2
   - Returns: Dict with equivalences and motivational message

5. **`estimate_yearly_impact(trips_per_month, avg_distance_km, avg_passengers, vehicle_type) -> dict`**
   - Projects annual CO2 savings based on usage patterns
   - Useful for user profile statistics
   - Returns: Monthly and yearly projections

**Implementation Notes:**
- All calculation methods are pure functions (no side effects)
- Rounding: Always round to 2 decimal places for display
- Zero handling: Electric vehicles return 0 kg CO2
- Validation: Ensure distance_km >= 0, passengers_count >= 0

---

## Data Persistence: SQLAlchemy Models

### Trip Model Extensions

**File**: `adapters/persistence/models.py`

**New Columns to Add:**

```python
from sqlalchemy import Column, String, Float, Enum
from sqlalchemy.orm import declarative_base

class Trip(Base):
    __tablename__ = "trips"

    # ... existing columns ...

    # Vehicle Information
    vehicle_type = Column(
        Enum(VehicleType),
        nullable=False,
        default=VehicleType.GASOLINE,
        index=True,
        comment="Type of vehicle used for the trip"
    )
    vehicle_model = Column(
        String(100),
        nullable=True,
        comment="Vehicle model/make (e.g., 'Toyota Prius')"
    )
    vehicle_plate = Column(
        String(20),
        nullable=True,
        comment="Vehicle license plate (optional, for driver reference)"
    )

    # Distance and CO2 Metrics
    distance_km = Column(
        Float,
        nullable=True,
        index=True,
        comment="Total trip distance in kilometers"
    )
    co2_saved_per_passenger_kg = Column(
        Float,
        nullable=True,
        comment="CO2 avoided by each passenger in kg"
    )
    total_co2_saved_kg = Column(
        Float,
        nullable=True,
        default=0.0,
        index=True,
        comment="Total CO2 avoided by all passengers in kg"
    )

    # Indexes for efficient querying
    __table_args__ = (
        Index('idx_trip_co2_stats', 'vehicle_type', 'total_co2_saved_kg'),
        Index('idx_trip_distance', 'distance_km'),
    )
```

**Indexes Rationale:**
- `vehicle_type`: For filtering trips by vehicle type in analytics
- `total_co2_saved_kg`: For leaderboards and top trips queries
- `distance_km`: For distance-based filtering and statistics
- Composite index `idx_trip_co2_stats`: For queries filtering by vehicle type and sorting by CO2

---

## Alembic Migration

**File**: `adapters/persistence/alembic/versions/XXXX_add_co2_fields_to_trips.py`

**Migration Operations:**

**Upgrade:**
```python
def upgrade():
    # Add vehicle information columns
    op.add_column('trips', sa.Column('vehicle_type', sa.Enum('gasoline', 'diesel', 'hybrid', 'electric', name='vehicletype'), nullable=False, server_default='gasoline'))
    op.add_column('trips', sa.Column('vehicle_model', sa.String(length=100), nullable=True))
    op.add_column('trips', sa.Column('vehicle_plate', sa.String(length=20), nullable=True))

    # Add distance and CO2 columns
    op.add_column('trips', sa.Column('distance_km', sa.Float(), nullable=True))
    op.add_column('trips', sa.Column('co2_saved_per_passenger_kg', sa.Float(), nullable=True))
    op.add_column('trips', sa.Column('total_co2_saved_kg', sa.Float(), nullable=True, server_default='0.0'))

    # Add indexes
    op.create_index('idx_trip_vehicle_type', 'trips', ['vehicle_type'], unique=False)
    op.create_index('idx_trip_co2_stats', 'trips', ['vehicle_type', 'total_co2_saved_kg'], unique=False)
    op.create_index('idx_trip_distance', 'trips', ['distance_km'], unique=False)
```

**Downgrade:**
```python
def downgrade():
    # Drop indexes
    op.drop_index('idx_trip_distance', table_name='trips')
    op.drop_index('idx_trip_co2_stats', table_name='trips')
    op.drop_index('idx_trip_vehicle_type', table_name='trips')

    # Drop columns
    op.drop_column('trips', 'total_co2_saved_kg')
    op.drop_column('trips', 'co2_saved_per_passenger_kg')
    op.drop_column('trips', 'distance_km')
    op.drop_column('trips', 'vehicle_plate')
    op.drop_column('trips', 'vehicle_model')
    op.drop_column('trips', 'vehicle_type')
```

---

## Repository Methods: Statistics Aggregation

### TripRepository Extensions

**File**: `adapters/persistence/repositories/trip_repository.py`

**New Methods:**

```python
async def get_total_co2_saved(self) -> float:
    """
    Get total CO2 saved across all trips in the platform.

    Returns:
        Total kg CO2 saved
    """
    async with self.session() as session:
        result = await session.execute(
            select(func.sum(Trip.total_co2_saved_kg))
            .where(Trip.is_active == True)
            .where(Trip.total_co2_saved_kg.isnot(None))
        )
        total = result.scalar_one_or_none()
        return total if total else 0.0

async def get_co2_by_vehicle_type(self) -> dict[str, float]:
    """
    Get CO2 savings aggregated by vehicle type.

    Returns:
        Dict mapping vehicle type to total kg CO2 saved
    """
    async with self.session() as session:
        result = await session.execute(
            select(
                Trip.vehicle_type,
                func.sum(Trip.total_co2_saved_kg).label('total_co2')
            )
            .where(Trip.is_active == True)
            .group_by(Trip.vehicle_type)
        )
        return {row.vehicle_type: row.total_co2 for row in result}

async def get_trips_with_co2(
    self,
    skip: int = 0,
    limit: int = 100
) -> list[Trip]:
    """
    Get trips that have CO2 data calculated.

    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return

    Returns:
        List of trips with CO2 data
    """
    async with self.session() as session:
        result = await session.execute(
            select(Trip)
            .where(Trip.is_active == True)
            .where(Trip.total_co2_saved_kg > 0)
            .order_by(Trip.total_co2_saved_kg.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
```

### BookingRepository Extensions

**File**: `adapters/persistence/repositories/booking_repository.py`

**New Methods:**

```python
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload

async def get_user_co2_stats(self, user_id: str) -> dict:
    """
    Get aggregated CO2 statistics for a user.

    Args:
        user_id: User ID (as passenger)

    Returns:
        Dict with total CO2 saved, trip count, distance
    """
    async with self.session() as session:
        # Get all confirmed/completed bookings with trip data
        result = await session.execute(
            select(
                func.count(Booking.id).label('trips_count'),
                func.sum(Trip.co2_saved_per_passenger_kg * Booking.seats_booked).label('total_co2_saved'),
                func.sum(Trip.distance_km).label('total_distance_km')
            )
            .join(Trip, Booking.trip_id == Trip.id)
            .where(Booking.passenger_id == user_id)
            .where(Booking.status.in_(['confirmed', 'completed']))
            .where(Trip.co2_saved_per_passenger_kg.isnot(None))
        )

        row = result.one()

        return {
            'trips_count': row.trips_count or 0,
            'total_co2_saved_kg': round(row.total_co2_saved or 0.0, 2),
            'total_distance_km': round(row.total_distance_km or 0.0, 2),
        }

async def get_driver_co2_stats(self, driver_id: str) -> dict:
    """
    Get CO2 statistics for trips where user was the driver.

    Args:
        driver_id: User ID (as driver)

    Returns:
        Dict with total CO2 facilitated, trip count
    """
    async with self.session() as session:
        result = await session.execute(
            select(
                func.count(Trip.id).label('trips_count'),
                func.sum(Trip.total_co2_saved_kg).label('total_co2_saved'),
                func.sum(Trip.distance_km).label('total_distance_km')
            )
            .where(Trip.driver_id == driver_id)
            .where(Trip.is_active == True)
            .where(Trip.total_co2_saved_kg.isnot(None))
        )

        row = result.one()

        return {
            'trips_count': row.trips_count or 0,
            'total_co2_facilitated_kg': round(row.total_co2_saved or 0.0, 2),
            'total_distance_km': round(row.total_distance_km or 0.0, 2),
        }
```

**Query Optimization Notes:**
- Use `joinedload` for eager loading if returning full entities
- Use `func.sum()` and `func.count()` for aggregations
- Filter by booking status to only count completed trips
- Multiply `co2_saved_per_passenger_kg` by `seats_booked` for accurate user savings
- Index on `passenger_id`, `driver_id`, and `status` columns for performance

---

## Dependencies

### Required Packages

```toml
[tool.poetry.dependencies]
# Core Framework
fastapi = "^0.104.0"
pydantic = "^2.5.0"
pydantic-settings = "^2.1.0"

# Database (SQLite3 + SQLAlchemy Async)
sqlalchemy = "^2.0.23"
aiosqlite = "^0.19.0"  # Async SQLite driver
alembic = "^1.12.1"

# Dependency Injection
dependency-injector = "^4.41.0"  # Optional, for advanced DI patterns

[tool.poetry.group.dev.dependencies]
# Testing
pytest = "^7.4.0"
pytest-asyncio = "^0.21.0"
httpx = "^0.25.0"  # For async HTTP client in tests
pytest-cov = "^4.1.0"

# Code Quality
ruff = "^0.1.0"
mypy = "^1.7.0"
black = "^23.11.0"
```

### SQLite3 Async Configuration

**File**: `config/database.py`

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite+aiosqlite:///./vibe_coding.db"

engine = create_async_engine(
    DATABASE_URL,
    echo=True,  # Set to False in production
    future=True,
)

async_session_maker = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_session() -> AsyncSession:
    """
    Dependency for FastAPI endpoints to get database session.
    """
    async with async_session_maker() as session:
        yield session
```

### Dependency Injection Hierarchy

**File**: `entrypoints/http/dependencies.py`

```python
from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_session
from domain.services.co2_service import CO2Calculator
from adapters.persistence.repositories.trip_repository import TripRepository
from adapters.persistence.repositories.booking_repository import BookingRepository

# Database session dependency
SessionDep = Annotated[AsyncSession, Depends(get_session)]

# CO2 Calculator (singleton, pure service with no state)
def get_co2_calculator() -> CO2Calculator:
    """
    Provides CO2Calculator instance.
    Can be a singleton as it's a stateless service.
    """
    return CO2Calculator()

CO2CalculatorDep = Annotated[CO2Calculator, Depends(get_co2_calculator)]

# Repository dependencies
def get_trip_repository(session: SessionDep) -> TripRepository:
    return TripRepository(session)

def get_booking_repository(session: SessionDep) -> BookingRepository:
    return BookingRepository(session)

TripRepoDep = Annotated[TripRepository, Depends(get_trip_repository)]
BookingRepoDep = Annotated[BookingRepository, Depends(get_booking_repository)]
```

**Dependency Graph:**
```
FastAPI Endpoint
    ↓
SessionDep (AsyncSession)
    ↓
Repository (TripRepository, BookingRepository)
    ↓
Domain Service (CO2Calculator)
```

---

## Background Tasks

### CO2 Calculation Triggers

**Primary Trigger**: Booking Creation

When a new booking is confirmed:
1. Retrieve trip with current passenger count
2. Calculate CO2 savings using `CO2Calculator`
3. Update trip's `total_co2_saved_kg` field
4. Persist updated trip to database

**Implementation Location**: `application/services/booking_service.py`

```python
class BookingService:
    def __init__(
        self,
        booking_repo: BookingRepository,
        trip_repo: TripRepository,
        co2_calculator: CO2Calculator,
    ):
        self.booking_repo = booking_repo
        self.trip_repo = trip_repo
        self.co2_calculator = co2_calculator

    async def create_booking(
        self,
        trip_id: str,
        passenger_id: str,
        seats_requested: int
    ) -> Booking:
        # ... booking creation logic ...

        # After successful booking creation
        trip = await self.trip_repo.get_by_id(trip_id)

        if trip.distance_km and trip.distance_km > 0:
            # Calculate current passenger count (exclude driver)
            passengers_count = trip.total_seats - trip.available_seats - 1

            # Calculate CO2 savings
            trip.co2_saved_per_passenger_kg = self.co2_calculator.calculate_savings_per_passenger(
                trip.distance_km,
                trip.vehicle_type
            )
            trip.total_co2_saved_kg = self.co2_calculator.calculate_total_savings(
                trip.distance_km,
                trip.vehicle_type,
                passengers_count
            )

            # Persist updated trip
            await self.trip_repo.update(trip_id, trip)

        return booking
```

**Secondary Trigger**: Trip Creation

When a trip is created with distance information:
1. Initialize `co2_saved_per_passenger_kg` (0 passengers yet)
2. Set `total_co2_saved_kg` to 0
3. Calculate and store potential savings for display

**Optional: Scheduled Recalculation**

For trips with dynamic passenger counts, consider a background job:
- Frequency: Nightly or after booking status changes
- Logic: Recalculate CO2 for all active trips with passengers
- Implementation: Celery task or FastAPI BackgroundTasks

---

## Error Handling

### Domain Error Mapping

| Domain Error | HTTP Status | Response Format | When It Occurs |
|--------------|-------------|----------------|----------------|
| `TripNotFoundError` | 404 | `{"detail": "Trip not found"}` | Trip ID doesn't exist |
| `CO2DataUnavailableError` | 400 | `{"detail": "CO2 data not available for this trip"}` | Trip has no distance or passengers |
| `InvalidVehicleTypeError` | 422 | `{"detail": "Invalid vehicle type"}` | Unknown vehicle type provided |
| `NegativeDistanceError` | 422 | `{"detail": "Distance must be positive"}` | Distance < 0 |
| `DatabaseConnectionError` | 503 | `{"detail": "Service temporarily unavailable"}` | SQLite connection issues |

### Exception Handlers

**File**: `entrypoints/http/exception_handlers.py`

```python
from fastapi import Request, status
from fastapi.responses import JSONResponse
from domain.exceptions import (
    TripNotFoundError,
    CO2DataUnavailableError,
    InvalidVehicleTypeError,
)

async def trip_not_found_handler(request: Request, exc: TripNotFoundError):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": str(exc)},
    )

async def co2_data_unavailable_handler(request: Request, exc: CO2DataUnavailableError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "detail": str(exc),
            "help": "Trip must have distance and passengers to calculate CO2",
        },
    )

async def invalid_vehicle_type_handler(request: Request, exc: InvalidVehicleTypeError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": str(exc),
            "valid_types": ["gasoline", "diesel", "hybrid", "electric"],
        },
    )

# Register in main.py
app.add_exception_handler(TripNotFoundError, trip_not_found_handler)
app.add_exception_handler(CO2DataUnavailableError, co2_data_unavailable_handler)
app.add_exception_handler(InvalidVehicleTypeError, invalid_vehicle_type_handler)
```

---

## Testing Strategy

### Unit Tests: CO2 Calculator

**File**: `tests/unit/domain/services/test_co2_calculator.py`

**Test Cases:**

1. **Test Emission Calculation Accuracy**
   ```python
   def test_calculate_trip_emissions_gasoline():
       calculator = CO2Calculator()
       emissions = calculator.calculate_trip_emissions(100, VehicleType.GASOLINE)
       assert emissions == 12.0  # 100 km × 120 g/km = 12000 g = 12 kg

   def test_calculate_trip_emissions_electric():
       calculator = CO2Calculator()
       emissions = calculator.calculate_trip_emissions(100, VehicleType.ELECTRIC)
       assert emissions == 0.0
   ```

2. **Test Savings Per Passenger**
   ```python
   def test_calculate_savings_per_passenger():
       calculator = CO2Calculator()
       savings = calculator.calculate_savings_per_passenger(125, VehicleType.DIESEL)
       assert savings == 13.125  # 125 km × 105 g/km = 13125 g = 13.125 kg
   ```

3. **Test Total Savings**
   ```python
   def test_calculate_total_savings():
       calculator = CO2Calculator()
       total = calculator.calculate_total_savings(100, VehicleType.GASOLINE, 3)
       assert total == 36.0  # 12 kg per passenger × 3 passengers
   ```

4. **Test Environmental Equivalences**
   ```python
   def test_get_environmental_equivalence():
       calculator = CO2Calculator()
       equiv = calculator.get_environmental_equivalence(21.0)

       assert equiv["co2_kg"] == 21.0
       assert equiv["trees_equivalent"] == 1.0  # 21 kg / 21 kg per tree
       assert equiv["car_km_equivalent"] == 175  # 21 kg / 0.12 kg per km
       assert "message" in equiv
   ```

5. **Test Edge Cases**
   ```python
   def test_zero_distance():
       calculator = CO2Calculator()
       emissions = calculator.calculate_trip_emissions(0, VehicleType.GASOLINE)
       assert emissions == 0.0

   def test_zero_passengers():
       calculator = CO2Calculator()
       total = calculator.calculate_total_savings(100, VehicleType.GASOLINE, 0)
       assert total == 0.0
   ```

6. **Test Yearly Projection**
   ```python
   def test_estimate_yearly_impact():
       calculator = CO2Calculator()
       projection = calculator.estimate_yearly_impact(
           trips_per_month=4,
           avg_distance_km=100,
           avg_passengers=2,
           vehicle_type=VehicleType.GASOLINE
       )

       # 4 trips/month × 12 months × 100 km × 120 g/km × 2 passengers
       # = 48 trips × 100 km × 120 g × 2 / 1000 = 1152 kg
       assert projection["yearly_co2_saved_kg"] == 1152.0
   ```

**Coverage Target**: 100% for domain service (pure business logic)

---

### Integration Tests: API Endpoints

**File**: `tests/integration/test_co2_endpoints.py`

**Test Cases:**

1. **Test Get Trip CO2 Impact - Success**
   ```python
   @pytest.mark.asyncio
   async def test_get_trip_co2_impact_success(client, test_trip_with_co2):
       response = await client.get(f"/api/v1/trips/{test_trip_with_co2.id}/co2-impact")

       assert response.status_code == 200
       data = response.json()
       assert data["trip_id"] == str(test_trip_with_co2.id)
       assert data["co2_saved_per_passenger_kg"] > 0
       assert data["total_co2_saved_kg"] > 0
       assert "equivalences" in data
   ```

2. **Test Get Trip CO2 Impact - Not Found**
   ```python
   @pytest.mark.asyncio
   async def test_get_trip_co2_impact_not_found(client):
       response = await client.get("/api/v1/trips/nonexistent-id/co2-impact")
       assert response.status_code == 404
   ```

3. **Test Get Trip CO2 Impact - No Data**
   ```python
   @pytest.mark.asyncio
   async def test_get_trip_co2_impact_no_data(client, test_trip_without_distance):
       response = await client.get(f"/api/v1/trips/{test_trip_without_distance.id}/co2-impact")
       assert response.status_code == 400
       assert "not available" in response.json()["detail"].lower()
   ```

4. **Test Get User CO2 Stats - Authenticated**
   ```python
   @pytest.mark.asyncio
   async def test_get_user_co2_stats_authenticated(client, auth_headers, test_user_with_bookings):
       response = await client.get(
           "/api/v1/users/me/co2-stats",
           headers=auth_headers
       )

       assert response.status_code == 200
       data = response.json()
       assert "total_co2_saved_kg" in data
       assert "trips_as_passenger_count" in data
       assert data["total_co2_saved_kg"] > 0
   ```

5. **Test Get User CO2 Stats - Unauthenticated**
   ```python
   @pytest.mark.asyncio
   async def test_get_user_co2_stats_unauthenticated(client):
       response = await client.get("/api/v1/users/me/co2-stats")
       assert response.status_code == 401
   ```

6. **Test Get Other User CO2 Stats - Public**
   ```python
   @pytest.mark.asyncio
   async def test_get_other_user_co2_stats(client, test_user):
       response = await client.get(f"/api/v1/users/{test_user.id}/co2-stats")
       assert response.status_code == 200
   ```

**Coverage Target**: 90%+ for HTTP endpoints

---

### Integration Tests: Booking CO2 Calculation

**File**: `tests/integration/test_co2_booking_integration.py`

**Test Cases:**

1. **Test CO2 Calculation on Booking Creation**
   ```python
   @pytest.mark.asyncio
   async def test_booking_triggers_co2_calculation(
       client,
       auth_headers,
       test_trip_with_distance
   ):
       # Initial CO2 should be 0 (no passengers yet)
       trip = await get_trip(test_trip_with_distance.id)
       assert trip.total_co2_saved_kg == 0.0

       # Create booking
       response = await client.post(
           f"/api/v1/bookings/",
           json={
               "trip_id": str(test_trip_with_distance.id),
               "seats_requested": 2
           },
           headers=auth_headers
       )
       assert response.status_code == 201

       # Check trip CO2 was updated
       trip = await get_trip(test_trip_with_distance.id)
       assert trip.total_co2_saved_kg > 0
       assert trip.co2_saved_per_passenger_kg > 0
   ```

2. **Test CO2 Updates with Multiple Bookings**
   ```python
   @pytest.mark.asyncio
   async def test_co2_updates_with_multiple_bookings(
       client,
       test_trip_with_distance
   ):
       # First booking
       await create_booking(test_trip_with_distance.id, seats=1)
       trip = await get_trip(test_trip_with_distance.id)
       first_total = trip.total_co2_saved_kg

       # Second booking
       await create_booking(test_trip_with_distance.id, seats=1)
       trip = await get_trip(test_trip_with_distance.id)
       second_total = trip.total_co2_saved_kg

       # CO2 should increase with more passengers
       assert second_total > first_total
       assert second_total == pytest.approx(first_total * 2)
   ```

**Coverage Target**: 85%+ for integration scenarios

---

### Test Fixtures

**File**: `tests/conftest.py`

```python
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from domain.models.vehicle import VehicleType
from adapters.persistence.models import Trip, User, Booking

@pytest.fixture
async def test_trip_with_co2(db_session):
    """Creates a trip with CO2 data calculated."""
    trip = Trip(
        driver_id="user-123",
        origin="Madrid",
        destination="Barcelona",
        distance_km=500.0,
        vehicle_type=VehicleType.GASOLINE,
        total_seats=4,
        available_seats=2,  # 2 passengers
        co2_saved_per_passenger_kg=60.0,  # 500 km × 120 g/km = 60 kg
        total_co2_saved_kg=120.0,  # 60 kg × 2 passengers
    )
    db_session.add(trip)
    await db_session.commit()
    await db_session.refresh(trip)
    return trip

@pytest.fixture
async def test_trip_without_distance(db_session):
    """Creates a trip without distance information."""
    trip = Trip(
        driver_id="user-456",
        origin="Valencia",
        destination="Alicante",
        distance_km=None,
        vehicle_type=VehicleType.DIESEL,
        total_seats=3,
        available_seats=3,
    )
    db_session.add(trip)
    await db_session.commit()
    await db_session.refresh(trip)
    return trip

@pytest.fixture
async def test_user_with_bookings(db_session, test_trip_with_co2):
    """Creates a user with confirmed bookings."""
    user = User(id="user-789", username="ecodriver")
    booking = Booking(
        trip_id=test_trip_with_co2.id,
        passenger_id=user.id,
        seats_booked=1,
        status="confirmed"
    )
    db_session.add_all([user, booking])
    await db_session.commit()
    return user
```

---

## Data Migration Script

### Backfill CO2 for Existing Trips

**File**: `adapters/scripts/backfill_co2_data.py`

**Purpose**: Calculate CO2 for trips created before this feature was implemented.

**Logic:**
1. Query all trips with `distance_km > 0` and `total_co2_saved_kg IS NULL or = 0`
2. For each trip, calculate current passenger count
3. Use `CO2Calculator` to compute CO2 savings
4. Update trip record with calculated values
5. Log progress and errors

**Implementation:**

```python
import asyncio
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import async_session_maker
from adapters.persistence.models import Trip, Booking
from domain.services.co2_service import CO2Calculator
from domain.models.vehicle import VehicleType

async def backfill_co2_data():
    """
    Backfill CO2 data for existing trips.
    Run once after deploying CO2 feature.
    """
    calculator = CO2Calculator()
    updated_count = 0
    error_count = 0

    async with async_session_maker() as session:
        # Find trips needing CO2 calculation
        result = await session.execute(
            select(Trip)
            .where(
                and_(
                    Trip.is_active == True,
                    Trip.distance_km > 0,
                    or_(
                        Trip.total_co2_saved_kg.is_(None),
                        Trip.total_co2_saved_kg == 0
                    )
                )
            )
        )
        trips = result.scalars().all()

        print(f"Found {len(trips)} trips to process")

        for trip in trips:
            try:
                # Calculate passenger count
                passengers_count = trip.total_seats - trip.available_seats - 1

                if passengers_count > 0:
                    # Calculate CO2
                    trip.co2_saved_per_passenger_kg = calculator.calculate_savings_per_passenger(
                        trip.distance_km,
                        trip.vehicle_type
                    )
                    trip.total_co2_saved_kg = calculator.calculate_total_savings(
                        trip.distance_km,
                        trip.vehicle_type,
                        passengers_count
                    )

                    session.add(trip)
                    updated_count += 1

                    print(f"✓ Trip {trip.id}: {trip.total_co2_saved_kg} kg CO2")

            except Exception as e:
                error_count += 1
                print(f"✗ Error processing trip {trip.id}: {e}")

        await session.commit()

    print(f"\nBackfill complete:")
    print(f"  ✓ Updated: {updated_count} trips")
    print(f"  ✗ Errors: {error_count} trips")

if __name__ == "__main__":
    asyncio.run(backfill_co2_data())
```

**Usage:**
```bash
# Run from project root
python -m adapters.scripts.backfill_co2_data

# Or via poetry
poetry run python -m adapters.scripts.backfill_co2_data
```

**Safety Considerations:**
- Run in maintenance window (low traffic)
- Add transaction batching for large datasets (commit every 100 trips)
- Add dry-run mode (`--dry-run` flag) to preview changes
- Log all updates for audit trail
- Consider running with `--limit` flag for testing

---

## Observability

### Logging

**Structured Logging for CO2 Operations:**

```python
import logging
import structlog

logger = structlog.get_logger(__name__)

# Log CO2 calculation
logger.info(
    "co2_calculated",
    trip_id=trip_id,
    distance_km=distance_km,
    vehicle_type=vehicle_type.value,
    passengers_count=passengers_count,
    co2_saved_kg=total_co2_saved_kg,
)

# Log aggregation query
logger.info(
    "user_co2_stats_retrieved",
    user_id=user_id,
    total_co2_saved=stats["total_co2_saved_kg"],
    trips_count=stats["trips_count"],
    duration_ms=elapsed_time,
)

# Log migration progress
logger.info(
    "co2_backfill_progress",
    processed=processed_count,
    total=total_count,
    percentage=round((processed_count / total_count) * 100, 2),
)
```

**Log Levels:**
- **INFO**: Successful CO2 calculations, user stats queries
- **WARNING**: Missing distance data, electric vehicle with null type
- **ERROR**: Calculation failures, database errors
- **DEBUG**: Detailed calculation steps, SQL queries

---

### Metrics

**Prometheus Metrics to Track:**

```python
from prometheus_client import Counter, Histogram, Gauge

# CO2 calculation metrics
co2_calculations_total = Counter(
    "co2_calculations_total",
    "Total number of CO2 calculations performed",
    ["vehicle_type"]
)

co2_saved_kg_total = Gauge(
    "co2_saved_kg_total",
    "Total kg of CO2 saved across all trips"
)

co2_calculation_duration_seconds = Histogram(
    "co2_calculation_duration_seconds",
    "Time taken to calculate CO2 for a trip"
)

# User stats metrics
user_co2_stats_requests_total = Counter(
    "user_co2_stats_requests_total",
    "Total requests for user CO2 statistics"
)

user_co2_stats_duration_seconds = Histogram(
    "user_co2_stats_duration_seconds",
    "Time taken to aggregate user CO2 statistics"
)

# Usage in code
with co2_calculation_duration_seconds.time():
    co2_saved = calculator.calculate_total_savings(distance, vehicle_type, passengers)

co2_calculations_total.labels(vehicle_type=vehicle_type.value).inc()
co2_saved_kg_total.set(total_platform_co2_saved)
```

**Dashboard Panels:**
- Total CO2 saved (gauge)
- CO2 calculations per hour (rate)
- Average CO2 per trip (gauge)
- CO2 by vehicle type (stacked bar)
- User stats query latency (histogram)

---

### Tracing

**OpenTelemetry Spans:**

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

async def get_user_co2_stats(user_id: str):
    with tracer.start_as_current_span("get_user_co2_stats") as span:
        span.set_attribute("user_id", user_id)

        # Database query
        with tracer.start_as_current_span("db.query_user_bookings"):
            stats = await booking_repo.get_user_co2_stats(user_id)

        # Calculation
        with tracer.start_as_current_span("calculate_equivalences"):
            equivalences = co2_calculator.get_environmental_equivalence(
                stats["total_co2_saved_kg"]
            )

        span.set_attribute("co2_saved_kg", stats["total_co2_saved_kg"])
        span.set_attribute("trips_count", stats["trips_count"])

        return {**stats, "equivalences": equivalences}
```

**Trace Key Operations:**
- CO2 calculation (`calculate_trip_co2`)
- User stats aggregation (`get_user_co2_stats`)
- Trip CO2 impact query (`get_trip_co2_impact`)
- Backfill migration (`backfill_co2_data`)

---

## Open Questions

1. **Distance Data Source**:
   - Q: Where does `distance_km` come from initially?
   - Options:
     - A) User input when creating trip
     - B) Calculated from coordinates using mapping service (RF-005)
     - C) Both (calculated automatically, but user can override)
   - **Recommendation**: Option C - Calculate automatically from coordinates if available, allow manual override for accuracy

2. **Driver CO2 Attribution**:
   - Q: Should drivers receive CO2 "credit" for facilitating carpooling?
   - Options:
     - A) Driver gets credit for total CO2 saved (all passengers)
     - B) Driver gets no credit (only passengers avoid emissions)
     - C) Driver gets partial credit (e.g., 50% of total)
   - **Recommendation**: Option A for gamification, but clearly distinguish "facilitated" vs "avoided" in UI

3. **Electric Vehicle Calculation**:
   - Q: Should we account for electricity generation emissions for EVs?
   - Context: Currently EVs = 0 g CO2/km (direct emissions only)
   - Options:
     - A) Keep at 0 (simpler, more motivating)
     - B) Use grid average (e.g., 50 g CO2/km for Spain)
     - C) Make configurable per region
   - **Recommendation**: Option A for MVP (aligns with industry practice of reporting direct emissions)

4. **Historical Data Accuracy**:
   - Q: For trips created before RF-005 (maps), distance may be missing. How to handle?
   - Options:
     - A) Leave CO2 null for old trips without distance
     - B) Estimate distance from origin/destination city pairs
     - C) Mark as "estimated" with lower confidence
   - **Recommendation**: Option A - Only show CO2 for trips with accurate distance data

5. **Booking Cancellation**:
   - Q: When a booking is cancelled, should we recalculate trip's CO2?
   - Options:
     - A) Yes, immediately recalculate (accurate but more complex)
     - B) No, keep snapshot at booking time (simpler)
     - C) Recalculate only for active bookings (hybrid)
   - **Recommendation**: Option C - Recalculate when booking status changes to ensure accuracy

6. **API Rate Limiting**:
   - Q: Should user CO2 stats endpoint be cached or rate limited?
   - Context: Aggregation query could be expensive with many bookings
   - Options:
     - A) Cache stats with 1-hour TTL
     - B) Rate limit to 10 requests/minute per user
     - C) Both
   - **Recommendation**: Option C - Cache with 1-hour TTL + rate limit 30 req/min

7. **Yearly Projection Visibility**:
   - Q: Should yearly projection be shown in public user profiles?
   - Context: Projection is based on patterns, may not be accurate for new users
   - **Recommendation**: Only show if user has >= 3 completed trips (enough data for meaningful projection)

---

## Implementation Checklist

### Phase 1: Domain Layer (Pure Business Logic)

- [ ] **Create** `domain/models/vehicle.py`
  - [ ] Define `VehicleType` enum (gasoline, diesel, hybrid, electric)
  - [ ] Define `EmissionFactors` dataclass with constants
  - [ ] Implement `get_factor(vehicle_type)` method
  - [ ] Add docstrings with emission sources

- [ ] **Create** `domain/interfaces/co2_service_interface.py`
  - [ ] Define `ICO2Service` ABC
  - [ ] Declare method signatures for calculation methods
  - [ ] Add type hints and docstrings

- [ ] **Create** `domain/services/co2_service.py`
  - [ ] Implement `CO2Calculator` class
  - [ ] Implement `calculate_trip_emissions(distance_km, vehicle_type)`
  - [ ] Implement `calculate_savings_per_passenger(distance_km, vehicle_type)`
  - [ ] Implement `calculate_total_savings(distance_km, vehicle_type, passengers_count)`
  - [ ] Implement `get_environmental_equivalence(co2_kg)`
  - [ ] Implement `estimate_yearly_impact(trips_per_month, avg_distance_km, avg_passengers, vehicle_type)`
  - [ ] Add helper method `_generate_message(co2_kg)` for motivational messages
  - [ ] Ensure all methods are pure functions (no side effects)

- [ ] **Create** `domain/exceptions.py` (if not exists)
  - [ ] Define `CO2DataUnavailableError`
  - [ ] Define `InvalidVehicleTypeError`
  - [ ] Define `NegativeDistanceError`

### Phase 2: Database Layer (Persistence)

- [ ] **Modify** `adapters/persistence/models.py`
  - [ ] Add `vehicle_type` column to `Trip` model (Enum, indexed)
  - [ ] Add `vehicle_model` column (String, nullable)
  - [ ] Add `vehicle_plate` column (String, nullable)
  - [ ] Add `distance_km` column (Float, indexed)
  - [ ] Add `co2_saved_per_passenger_kg` column (Float)
  - [ ] Add `total_co2_saved_kg` column (Float, indexed, default=0.0)
  - [ ] Add composite index `idx_trip_co2_stats`

- [ ] **Create** Alembic migration `XXXX_add_co2_fields_to_trips.py`
  - [ ] Write `upgrade()` function to add columns and indexes
  - [ ] Write `downgrade()` function to remove columns and indexes
  - [ ] Test migration on development database
  - [ ] Verify rollback works correctly

- [ ] **Run** migration
  ```bash
  alembic upgrade head
  ```

- [ ] **Modify** `adapters/persistence/repositories/trip_repository.py`
  - [ ] Add `get_total_co2_saved() -> float` method
  - [ ] Add `get_co2_by_vehicle_type() -> dict[str, float]` method
  - [ ] Add `get_trips_with_co2(skip, limit) -> list[Trip]` method
  - [ ] Optimize queries with proper joins and aggregations

- [ ] **Modify** `adapters/persistence/repositories/booking_repository.py`
  - [ ] Add `get_user_co2_stats(user_id) -> dict` method
  - [ ] Add `get_driver_co2_stats(driver_id) -> dict` method
  - [ ] Ensure queries join with trips table and filter by booking status
  - [ ] Add indexes on foreign keys if missing

### Phase 3: Application Layer (Use Cases)

- [ ] **Create** `application/commands/calculate_trip_co2.py`
  - [ ] Define `CalculateTripCO2Command` dataclass
  - [ ] Implement `CalculateTripCO2Handler` class
  - [ ] Inject `TripRepository` and `CO2Calculator`
  - [ ] Handle business logic for calculating and persisting CO2

- [ ] **Create** `application/queries/get_user_co2_stats.py`
  - [ ] Define `GetUserCO2StatsQuery` dataclass
  - [ ] Implement `GetUserCO2StatsHandler` class
  - [ ] Inject `BookingRepository` and `CO2Calculator`
  - [ ] Aggregate user statistics and calculate equivalences

- [ ] **Create** `application/queries/get_trip_co2_impact.py`
  - [ ] Define `GetTripCO2ImpactQuery` dataclass
  - [ ] Implement `GetTripCO2ImpactHandler` class
  - [ ] Inject `TripRepository` and `CO2Calculator`
  - [ ] Fetch trip and enrich with equivalence data

- [ ] **Modify** `application/services/booking_service.py`
  - [ ] Inject `CO2Calculator` in `__init__`
  - [ ] After booking creation, check if trip has distance
  - [ ] Calculate passenger count (total_seats - available_seats - 1)
  - [ ] Call `calculate_total_savings()` and update trip
  - [ ] Persist updated trip to database
  - [ ] Handle case where distance is missing (log warning, skip calculation)

### Phase 4: HTTP Layer (API Endpoints)

- [ ] **Create** `entrypoints/http/schemas/co2_schemas.py`
  - [ ] Define `CO2ImpactResponse` Pydantic model
  - [ ] Define `EnvironmentalEquivalenceResponse` Pydantic model
  - [ ] Define `UserCO2StatsResponse` Pydantic model
  - [ ] Add validation and examples

- [ ] **Modify** `entrypoints/http/schemas/trip_schemas.py`
  - [ ] Add `vehicle_type`, `vehicle_model`, `vehicle_plate` to `CreateTripRequest`
  - [ ] Add `distance_km`, `co2_saved_per_passenger_kg`, `total_co2_saved_kg` to `TripResponse`
  - [ ] Add optional `co2_impact` nested object to `TripResponse`

- [ ] **Create** `entrypoints/http/routers/co2_router.py`
  - [ ] Create FastAPI router
  - [ ] Implement `GET /trips/{trip_id}/co2-impact` endpoint
    - [ ] Inject `TripRepository` and `CO2Calculator`
    - [ ] Fetch trip by ID
    - [ ] Validate CO2 data exists
    - [ ] Return `CO2ImpactResponse`
  - [ ] Implement `GET /users/me/co2-stats` endpoint
    - [ ] Require authentication
    - [ ] Inject `BookingRepository` and `CO2Calculator`
    - [ ] Aggregate user statistics
    - [ ] Return `UserCO2StatsResponse`
  - [ ] Implement `GET /users/{user_id}/co2-stats` endpoint (public)
    - [ ] No authentication required
    - [ ] Same logic as `/me` but for specified user

- [ ] **Modify** `entrypoints/http/dependencies.py`
  - [ ] Add `get_co2_calculator()` dependency function
  - [ ] Return singleton instance of `CO2Calculator`
  - [ ] Add type alias `CO2CalculatorDep`

- [ ] **Modify** `entrypoints/http/exception_handlers.py`
  - [ ] Add handler for `TripNotFoundError` → 404
  - [ ] Add handler for `CO2DataUnavailableError` → 400
  - [ ] Add handler for `InvalidVehicleTypeError` → 422

- [ ] **Modify** `main.py`
  - [ ] Import `co2_router`
  - [ ] Register router: `app.include_router(co2_router, prefix="/api/v1", tags=["co2"])`
  - [ ] Register exception handlers

### Phase 5: Data Migration

- [ ] **Create** `adapters/scripts/backfill_co2_data.py`
  - [ ] Implement async function `backfill_co2_data()`
  - [ ] Query trips with distance > 0 and no CO2 data
  - [ ] For each trip, calculate passenger count
  - [ ] Use `CO2Calculator` to compute CO2 savings
  - [ ] Update trip records
  - [ ] Log progress and errors
  - [ ] Add command-line arguments (--dry-run, --limit, --batch-size)

- [ ] **Test** migration script on development database
  - [ ] Run with `--dry-run` flag first
  - [ ] Verify output matches expectations
  - [ ] Run actual migration on dev database
  - [ ] Check updated records in database

- [ ] **Document** migration process in README or docs

### Phase 6: Testing

#### Unit Tests

- [ ] **Create** `tests/unit/domain/services/test_co2_calculator.py`
  - [ ] Test `calculate_trip_emissions()` for all vehicle types
  - [ ] Test `calculate_savings_per_passenger()` with various distances
  - [ ] Test `calculate_total_savings()` with different passenger counts
  - [ ] Test `get_environmental_equivalence()` calculations
  - [ ] Test `estimate_yearly_impact()` projections
  - [ ] Test edge cases (zero distance, zero passengers, electric vehicle)
  - [ ] Verify rounding to 2 decimal places

- [ ] **Run** unit tests and ensure 100% coverage for domain service
  ```bash
  pytest tests/unit/domain/services/test_co2_calculator.py -v --cov
  ```

#### Integration Tests

- [ ] **Create** `tests/integration/test_co2_endpoints.py`
  - [ ] Test `GET /trips/{trip_id}/co2-impact` success case
  - [ ] Test `GET /trips/{trip_id}/co2-impact` not found (404)
  - [ ] Test `GET /trips/{trip_id}/co2-impact` no data (400)
  - [ ] Test `GET /users/me/co2-stats` authenticated
  - [ ] Test `GET /users/me/co2-stats` unauthenticated (401)
  - [ ] Test `GET /users/{user_id}/co2-stats` public access
  - [ ] Test response schemas match Pydantic models

- [ ] **Create** `tests/integration/test_co2_booking_integration.py`
  - [ ] Test CO2 calculation triggered on booking creation
  - [ ] Test CO2 updates with multiple bookings
  - [ ] Test CO2 remains 0 when no distance data
  - [ ] Test CO2 calculation with different vehicle types

- [ ] **Create** test fixtures in `tests/conftest.py`
  - [ ] `test_trip_with_co2` - Trip with CO2 data
  - [ ] `test_trip_without_distance` - Trip missing distance
  - [ ] `test_user_with_bookings` - User with confirmed bookings
  - [ ] `test_co2_calculator` - CO2Calculator instance

- [ ] **Run** integration tests
  ```bash
  pytest tests/integration/ -v --cov
  ```

#### Contract Tests

- [ ] **Verify** API contract matches OpenAPI spec
  - [ ] Generate OpenAPI schema from FastAPI
  - [ ] Compare with documented schemas
  - [ ] Ensure all fields are present and correctly typed

### Phase 7: Documentation

- [ ] **Update** API documentation (Swagger/ReDoc)
  - [ ] Add descriptions to all CO2 endpoints
  - [ ] Add example requests and responses
  - [ ] Document error responses
  - [ ] Add tags and summaries

- [ ] **Create** README section for CO2 feature
  - [ ] Explain emission factors and calculation logic
  - [ ] Provide usage examples (curl commands)
  - [ ] Document environmental equivalences

- [ ] **Add** architectural decision record (ADR)
  - [ ] Document decision to use standard emission factors
  - [ ] Explain why electric vehicles = 0 g CO2/km
  - [ ] Justify calculation formula (CO2_avoided = distance × factor × passengers)

- [ ] **Update** deployment guide
  - [ ] Add migration step for CO2 fields
  - [ ] Document backfill script usage
  - [ ] Note database size increase (new indexes and columns)

### Phase 8: Deployment & Verification

- [ ] **Run** database migration in staging
  ```bash
  alembic upgrade head
  ```

- [ ] **Run** backfill script in staging
  ```bash
  python -m adapters.scripts.backfill_co2_data --batch-size=100
  ```

- [ ] **Verify** data in staging database
  - [ ] Check trips have CO2 data populated
  - [ ] Verify calculations are accurate (spot check)
  - [ ] Ensure indexes are created

- [ ] **Test** endpoints in staging
  ```bash
  # Test trip CO2 impact
  curl https://staging.api.vibe-coding.com/api/v1/trips/{trip_id}/co2-impact

  # Test user CO2 stats (with auth)
  curl https://staging.api.vibe-coding.com/api/v1/users/me/co2-stats \
    -H "Authorization: Bearer {token}"
  ```

- [ ] **Monitor** performance
  - [ ] Check query latency for user CO2 stats (should be < 200ms)
  - [ ] Monitor database CPU usage during aggregation queries
  - [ ] Verify no N+1 query issues

- [ ] **Deploy** to production
  - [ ] Run migration
  - [ ] Run backfill script (off-peak hours)
  - [ ] Monitor error rates and latency

- [ ] **Verify** in production
  - [ ] Create test trip with vehicle type and distance
  - [ ] Create test booking for that trip
  - [ ] Check trip CO2 data is calculated
  - [ ] Verify user CO2 stats endpoint returns correct data

### Phase 9: Monitoring & Observability

- [ ] **Set up** logging
  - [ ] Add structured logs for CO2 calculations
  - [ ] Log user stats queries with duration
  - [ ] Log migration progress

- [ ] **Set up** metrics (if Prometheus available)
  - [ ] Instrument CO2 calculation counter
  - [ ] Instrument user stats query duration histogram
  - [ ] Set up dashboard for CO2 metrics

- [ ] **Set up** alerts
  - [ ] Alert on high CO2 calculation error rate (> 5%)
  - [ ] Alert on slow user stats queries (> 500ms p95)

### Phase 10: Future Enhancements (Optional)

- [ ] **Leaderboard** endpoint (`GET /api/v1/co2/leaderboard`)
  - [ ] Rank users by total CO2 saved
  - [ ] Support filtering by time period (month, year)

- [ ] **Badges** system for CO2 milestones
  - [ ] "First 10 kg saved" badge
  - [ ] "100 kg saved" badge
  - [ ] "Eco Warrior" badge (1000 kg saved)

- [ ] **Certificates** - Generate downloadable PDFs
  - [ ] User CO2 impact certificate
  - [ ] Include equivalences and motivational message

- [ ] **Dashboard** - Platform-wide CO2 statistics
  - [ ] Total CO2 saved by all users
  - [ ] CO2 savings over time (line chart)
  - [ ] CO2 by vehicle type (pie chart)

- [ ] **Integration** with carbon offset APIs
  - [ ] Allow users to purchase carbon offsets
  - [ ] Track offset purchases in database

---

## Self-Verification

**Before Marking This Feature as Complete:**

- [x] All domain aggregates have corresponding repositories
  - `Trip` model has `TripRepository` with CO2 aggregation methods
  - `Booking` model has `BookingRepository` with user CO2 stats methods

- [x] All commands/queries map to API endpoints
  - `CalculateTripCO2Command` → Auto-triggered on booking creation
  - `GetTripCO2ImpactQuery` → `GET /trips/{trip_id}/co2-impact`
  - `GetUserCO2StatsQuery` → `GET /users/me/co2-stats`

- [x] Dependency rules are enforced (no domain→framework dependencies)
  - Domain layer (`CO2Calculator`) has zero FastAPI/SQLAlchemy imports
  - All framework dependencies are in adapters/entrypoints layers

- [x] Testing strategy covers integration and contract tests
  - Unit tests for domain service (calculation accuracy)
  - Integration tests for API endpoints
  - Integration tests for booking CO2 calculation trigger

- [x] Error handling preserves domain error semantics
  - `CO2DataUnavailableError` → 400 Bad Request
  - `TripNotFoundError` → 404 Not Found
  - `InvalidVehicleTypeError` → 422 Unprocessable Entity

- [x] Open questions are clearly flagged
  - 7 open questions documented with recommendations

- [x] Implementation checklist is complete and ordered
  - 10 phases with 100+ actionable tasks
  - Tasks are ordered by dependency (domain → DB → application → HTTP)

---

## Summary

This implementation plan provides a complete roadmap for adding CO2 emissions calculation to the Vibe Coding carpooling platform. The feature follows Clean Architecture principles with:

- **Pure domain logic** in `CO2Calculator` service (zero framework dependencies)
- **SQLAlchemy async** for database operations with optimized aggregation queries
- **FastAPI** endpoints for retrieving CO2 impact and user statistics
- **Comprehensive testing** strategy covering unit, integration, and contract tests
- **Data migration** script to backfill CO2 for existing trips

**Key Technical Decisions:**
1. Standard emission factors from European Environment Agency (EEA)
2. CO2 calculation formula: `distance_km × emission_factor × passengers_count`
3. Electric vehicles treated as 0 g CO2/km (direct emissions only)
4. Automatic calculation triggered on booking creation
5. User statistics aggregate across all confirmed/completed bookings

**Implementation Complexity**: Low-Medium (2-3 hours as estimated in requirements)

**Feature Status**: BONUS / OPTIONAL - Can be implemented after core features are stable

**Next Steps**: Follow implementation checklist starting with Phase 1 (Domain Layer)

