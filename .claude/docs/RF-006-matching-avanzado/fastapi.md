# FastAPI Implementation Plan: RF-006 - Advanced Matching Engine

**Status**: READY
**Version**: 1.0.0
**Last Updated**: 2025-11-13
**Related Docs**:
- `.claude/plans/07-RF-006-matching-avanzado.md` (Functional Requirements)
- Depends on: RF-001 (Trip Publication), RF-005 (Maps/Geocoding)

---

## Summary

The Advanced Matching Engine is a core domain service that identifies compatible trips for passenger travel requests. This implementation uses **SQLite3 with SQLAlchemy async** to persist travel requests and leverage geographic calculations (Haversine formula) to compute compatibility scores based on:

1. **Geographic proximity**: How close pickup/dropoff points are to the trip route
2. **Temporal compatibility**: Date matching and optional time range filtering
3. **Cumulative detour constraint**: Ensuring `current_detour + additional_detour ≤ max_detour`
4. **Availability**: Sufficient seats remaining

The matching algorithm is pure domain logic with zero framework dependencies. The service orchestrates queries via repository interfaces and returns scored results sorted by compatibility.

This is **NOT** a simple CRUD feature - it's a sophisticated domain service implementing business-critical matching logic that forms the heart of the carpooling platform.

---

## Architecture Mapping

### Domain → FastAPI Mapping

| Domain Concept | FastAPI/Infrastructure Construct | Location | Notes |
|---------------|----------------------------------|----------|-------|
| TravelRequest (Aggregate) | SQLAlchemy model + Pydantic domain model | `domain/entities.py`, `adapters/orm/models.py` | Pure domain object + ORM mapping |
| MatchResult (Value Object) | Pydantic model | `domain/value_objects.py` | Immutable result object |
| MatchScore (Value Object) | Pydantic model | `domain/value_objects.py` | Score breakdown (0-100) |
| WaypointInsertion (Value Object) | Pydantic model | `domain/value_objects.py` | Proposed roadmap insertion |
| IMatchingService (Interface) | Abstract base class | `domain/services/matching_service.py` | Domain service contract |
| MatchingService (Implementation) | Concrete service | `application/services/matching_service.py` | Orchestrates matching algorithm |
| ITravelRequestRepository | Abstract base class | `domain/repositories/travel_request_repository.py` | Repository contract |
| SQLAlchemyTravelRequestRepository | SQLAlchemy implementation | `adapters/repositories/travel_request_repository.py` | Database persistence |
| DetourCalculator | Utility class | `domain/services/geo_calculator.py` | Pure functions for Haversine |
| POST /matching/find-trips | FastAPI endpoint | `entrypoints/http/routers/matching.py` | HTTP adapter |

### Layer Responsibilities

**Domain Layer** (`domain/`):
- `entities.py`: TravelRequest aggregate (pure Python dataclass)
- `value_objects.py`: MatchResult, MatchScore, WaypointInsertion (immutable Pydantic models)
- `services/matching_service.py`: IMatchingService interface (abstract contract)
- `services/geo_calculator.py`: GeoCalculator utility (Haversine distance, detour estimation)
- `repositories/travel_request_repository.py`: ITravelRequestRepository interface
- **Zero dependencies on FastAPI, SQLAlchemy, or any framework**

**Application Layer** (`application/`):
- `services/matching_service.py`: MatchingService implementation (orchestrates domain logic)
- `use_cases/find_compatible_trips.py`: Use case for finding matches
- `use_cases/accept_match.py`: Use case for accepting a match and creating booking
- Depends only on domain layer interfaces

**Adapters Layer** (`adapters/`):
- `orm/models.py`: SQLAlchemy models for TravelRequest
- `repositories/travel_request_repository.py`: SQLAlchemyTravelRequestRepository
- Mapping functions: `to_domain()`, `from_domain()` for ORM ↔ Domain conversion

**HTTP Entrypoints** (`entrypoints/http/`):
- `routers/matching.py`: FastAPI router with endpoints
- `schemas/matching.py`: Pydantic request/response DTOs
- `dependencies.py`: Dependency injection setup

---

## File Actions

### Create New Files

#### Domain Layer
- `apps/matching/domain/entities.py`
  - Purpose: TravelRequest aggregate root (pure Python dataclass)

- `apps/matching/domain/value_objects.py`
  - Purpose: MatchResult, MatchScore, WaypointInsertion value objects

- `apps/matching/domain/services/matching_service.py`
  - Purpose: IMatchingService interface (abstract base class)

- `apps/matching/domain/services/geo_calculator.py`
  - Purpose: GeoCalculator utility for Haversine distance and detour calculations

- `apps/matching/domain/repositories/travel_request_repository.py`
  - Purpose: ITravelRequestRepository interface

#### Application Layer
- `apps/matching/application/services/matching_service.py`
  - Purpose: MatchingService implementation (concrete service)

- `apps/matching/application/use_cases/find_compatible_trips.py`
  - Purpose: Use case for finding matches

- `apps/matching/application/use_cases/accept_match.py`
  - Purpose: Use case for accepting matches

#### Adapters Layer
- `apps/matching/adapters/orm/models.py`
  - Purpose: SQLAlchemy TravelRequest model

- `apps/matching/adapters/repositories/travel_request_repository.py`
  - Purpose: SQLAlchemyTravelRequestRepository implementation

- `apps/matching/adapters/orm/mappers.py`
  - Purpose: ORM ↔ Domain mapping functions

#### HTTP Entrypoints
- `apps/matching/entrypoints/http/routers/matching.py`
  - Purpose: FastAPI router with matching endpoints

- `apps/matching/entrypoints/http/schemas/matching.py`
  - Purpose: Pydantic request/response DTOs

- `apps/matching/entrypoints/http/dependencies.py`
  - Purpose: Dependency injection for matching service

#### Database Migrations
- `alembic/versions/XXXX_create_travel_requests_table.py`
  - Purpose: Alembic migration to create travel_requests table

### Modify Existing Files

- `apps/matching/__init__.py`
  - Add: Module initialization

- `main.py`
  - Add: Include matching router

- `config/database.py`
  - Ensure: Async session factory is configured

---

## API Endpoints

| Method | Path | Request Model | Response Model | Use Case | Auth |
|--------|------|--------------|----------------|----------|------|
| POST | /api/v1/matching/travel-requests | CreateTravelRequestDTO | TravelRequestResponseDTO | Create travel request | Required |
| GET | /api/v1/matching/travel-requests/{id}/matches | - | MatchListResponseDTO | Find compatible trips | Required |
| POST | /api/v1/matching/travel-requests/{id}/accept | AcceptMatchDTO | AcceptMatchResponseDTO | Accept match & create booking | Required |
| GET | /api/v1/matching/my-travel-requests | Query params: skip, limit | List[TravelRequestResponseDTO] | List user's travel requests | Required |
| GET | /api/v1/matching/travel-requests/{id} | - | TravelRequestResponseDTO | Get travel request by ID | Required |
| DELETE | /api/v1/matching/travel-requests/{id} | - | 204 No Content | Cancel travel request | Required |

### Endpoint Specifications

#### POST /api/v1/matching/travel-requests
**Purpose**: Create a new travel request with geocoded coordinates

**Request Body**:
```json
{
  "origin_address": "Jerez de la Frontera, España",
  "destination_address": "Dos Hermanas, España",
  "travel_date": "2025-12-15",
  "time_from": "09:00:00",
  "time_to": "11:00:00",
  "seats_requested": 1,
  "passenger_notes": "Prefiero no fumar"
}
```

**Process**:
1. Validate input (addresses, date, seats)
2. Geocode origin using map service → coordinates
3. Geocode destination using map service → coordinates
4. Create TravelRequest domain entity
5. Persist via repository
6. Return response with ID and coordinates

**Response**: TravelRequestResponseDTO (201 Created)

---

#### GET /api/v1/matching/travel-requests/{id}/matches
**Purpose**: Find compatible trips for a travel request

**Query Parameters**: None

**Process**:
1. Fetch travel request by ID
2. Verify ownership (current_user.id == travel_request.passenger_id)
3. Execute matching algorithm via MatchingService.find_compatible_trips()
4. Return scored, sorted list of MatchResult

**Matching Algorithm**:
```
FOR EACH active trip on travel_request.travel_date:
  1. Check temporal compatibility (time_from, time_to)
  2. Check geographic compatibility:
     - Is pickup point near trip route? (threshold: 15km)
     - Is dropoff point near trip route? (threshold: 15km)
  3. Calculate additional detour distance (Haversine)
  4. Estimate additional detour time (distance / avg_speed)
  5. Verify cumulative detour constraint:
     - current_detour + additional_detour ≤ max_detour
  6. Calculate proximity score (0-100)
  7. Calculate time compatibility score (0-100)
  8. Calculate final score: 0.6 * proximity + 0.4 * time
  9. Build MatchResult with all details

FILTER results WHERE is_compatible = true
SORT results BY match_score DESC
RETURN top matches
```

**Response**: MatchListResponseDTO (200 OK)
```json
{
  "travel_request_id": "uuid",
  "matches": [
    {
      "trip_id": "uuid",
      "is_compatible": true,
      "trip_origin": "Cádiz",
      "trip_destination": "Sevilla",
      "departure_time": "09:00:00",
      "available_seats": 3,
      "current_detour_minutes": 0,
      "max_detour_minutes": 30,
      "additional_detour_minutes": 20,
      "projected_total_detour": 20,
      "match_score": {
        "trip_id": "uuid",
        "score": 85.5,
        "detour_additional": 20,
        "proximity_score": 90.0,
        "time_compatibility_score": 95.0
      },
      "proposed_insertion": {
        "pickup_index": 0,
        "dropoff_index": 1,
        "pickup_location": {"lat": 36.5271, "lng": -6.2886, "address": "Jerez"},
        "dropoff_location": {"lat": 37.3891, "lng": -5.9845, "address": "Dos Hermanas"},
        "additional_detour_minutes": 20
      },
      "driver_id": "uuid"
    }
  ],
  "total_matches": 1
}
```

---

#### POST /api/v1/matching/travel-requests/{id}/accept
**Purpose**: Accept a match and create a booking

**Request Body**:
```json
{
  "trip_id": "uuid"
}
```

**Process**:
1. Fetch travel request by ID
2. Verify ownership
3. Re-evaluate compatibility (race condition protection)
4. Create booking via BookingService
5. Update trip roadmap with pickup/dropoff waypoints
6. Update trip.current_detour_minutes += additional_detour
7. Update travel_request.status = "ACCEPTED"
8. Update travel_request.matched_trip_id = trip_id
9. Return success response

**Response**: (201 Created)
```json
{
  "message": "Match aceptado exitosamente",
  "booking_id": "uuid",
  "trip_id": "uuid"
}
```

---

## Data Persistence

### SQLAlchemy Models

#### TravelRequest Table

```python
# apps/matching/adapters/orm/models.py

from sqlalchemy import Column, Integer, String, Float, Date, Time, DateTime, Enum
from sqlalchemy.sql import func
from config.database import Base
import enum

class TravelRequestStatusEnum(enum.Enum):
    PENDING = "pending"
    MATCHED = "matched"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CANCELLED = "cancelled"

class TravelRequestORM(Base):
    __tablename__ = "travel_requests"

    id = Column(String, primary_key=True)
    passenger_id = Column(String, nullable=False, index=True)

    # Geographic coordinates
    origin_lat = Column(Float, nullable=False)
    origin_lng = Column(Float, nullable=False)
    destination_lat = Column(Float, nullable=False)
    destination_lng = Column(Float, nullable=False)

    # Address strings
    origin_address = Column(String(500), nullable=True)
    destination_address = Column(String(500), nullable=True)

    # Temporal criteria
    travel_date = Column(Date, nullable=False, index=True)
    time_from = Column(Time, nullable=True)
    time_to = Column(Time, nullable=True)

    # Request details
    seats_requested = Column(Integer, nullable=False, default=1)
    passenger_notes = Column(String(1000), nullable=True)

    # Status tracking
    status = Column(Enum(TravelRequestStatusEnum), nullable=False, default=TravelRequestStatusEnum.PENDING, index=True)
    matched_trip_id = Column(String, nullable=True, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    # Indexes
    __table_args__ = (
        # Composite index for matching queries
        Index('idx_travel_date_status', 'travel_date', 'status'),
        Index('idx_passenger_created', 'passenger_id', 'created_at'),
    )
```

### Alembic Migration

```python
# alembic/versions/XXXX_create_travel_requests_table.py

"""create travel_requests table

Revision ID: XXXX
Revises: YYYY
Create Date: 2025-11-13
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'travel_requests',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('passenger_id', sa.String(), nullable=False),
        sa.Column('origin_lat', sa.Float(), nullable=False),
        sa.Column('origin_lng', sa.Float(), nullable=False),
        sa.Column('destination_lat', sa.Float(), nullable=False),
        sa.Column('destination_lng', sa.Float(), nullable=False),
        sa.Column('origin_address', sa.String(length=500), nullable=True),
        sa.Column('destination_address', sa.String(length=500), nullable=True),
        sa.Column('travel_date', sa.Date(), nullable=False),
        sa.Column('time_from', sa.Time(), nullable=True),
        sa.Column('time_to', sa.Time(), nullable=True),
        sa.Column('seats_requested', sa.Integer(), nullable=False),
        sa.Column('passenger_notes', sa.String(length=1000), nullable=True),
        sa.Column('status', sa.Enum('PENDING', 'MATCHED', 'ACCEPTED', 'REJECTED', 'CANCELLED', name='travelrequeststatus'), nullable=False),
        sa.Column('matched_trip_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_passenger_id', 'travel_requests', ['passenger_id'])
    op.create_index('idx_travel_date', 'travel_requests', ['travel_date'])
    op.create_index('idx_status', 'travel_requests', ['status'])
    op.create_index('idx_matched_trip_id', 'travel_requests', ['matched_trip_id'])
    op.create_index('idx_travel_date_status', 'travel_requests', ['travel_date', 'status'])
    op.create_index('idx_passenger_created', 'travel_requests', ['passenger_id', 'created_at'])

def downgrade():
    op.drop_index('idx_passenger_created', table_name='travel_requests')
    op.drop_index('idx_travel_date_status', table_name='travel_requests')
    op.drop_index('idx_matched_trip_id', table_name='travel_requests')
    op.drop_index('idx_status', table_name='travel_requests')
    op.drop_index('idx_travel_date', table_name='travel_requests')
    op.drop_index('idx_passenger_id', table_name='travel_requests')
    op.drop_table('travel_requests')
    op.execute('DROP TYPE travelrequeststatus')
```

---

## Domain Models

### Domain Entity: TravelRequest

```python
# apps/matching/domain/entities.py

from dataclasses import dataclass, field
from datetime import datetime, date, time
from typing import Optional
from enum import Enum

class TravelRequestStatus(str, Enum):
    PENDING = "pending"
    MATCHED = "matched"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CANCELLED = "cancelled"

@dataclass
class TravelRequest:
    """
    Aggregate root representing a passenger's travel request.
    Pure domain entity with zero framework dependencies.
    """
    passenger_id: str
    origin_lat: float
    origin_lng: float
    destination_lat: float
    destination_lng: float
    travel_date: date
    seats_requested: int

    id: Optional[str] = None
    origin_address: Optional[str] = None
    destination_address: Optional[str] = None
    time_from: Optional[time] = None
    time_to: Optional[time] = None
    passenger_notes: Optional[str] = None
    status: TravelRequestStatus = TravelRequestStatus.PENDING
    matched_trip_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        self._validate()

    def _validate(self):
        """Domain validation rules"""
        if not -90 <= self.origin_lat <= 90:
            raise ValueError("origin_lat must be between -90 and 90")
        if not -180 <= self.origin_lng <= 180:
            raise ValueError("origin_lng must be between -180 and 180")
        if not -90 <= self.destination_lat <= 90:
            raise ValueError("destination_lat must be between -90 and 90")
        if not -180 <= self.destination_lng <= 180:
            raise ValueError("destination_lng must be between -180 and 180")
        if self.seats_requested < 1 or self.seats_requested > 10:
            raise ValueError("seats_requested must be between 1 and 10")

    def mark_as_accepted(self, trip_id: str):
        """Domain method: Accept match"""
        self.status = TravelRequestStatus.ACCEPTED
        self.matched_trip_id = trip_id
        self.updated_at = datetime.utcnow()

    def cancel(self):
        """Domain method: Cancel request"""
        if self.status == TravelRequestStatus.ACCEPTED:
            raise ValueError("Cannot cancel accepted travel request")
        self.status = TravelRequestStatus.CANCELLED
        self.updated_at = datetime.utcnow()
```

### Value Objects

```python
# apps/matching/domain/value_objects.py

from pydantic import BaseModel, Field
from datetime import time
from typing import Optional

class Coordinates(BaseModel):
    """Value object for geographic coordinates"""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)

class WaypointInsertion(BaseModel):
    """Proposed insertion of pickup/dropoff waypoints into trip roadmap"""
    pickup_index: int = Field(..., description="Index where to insert pickup waypoint")
    dropoff_index: int = Field(..., description="Index where to insert dropoff waypoint")
    pickup_location: dict = Field(..., description="Pickup coordinates and address")
    dropoff_location: dict = Field(..., description="Dropoff coordinates and address")
    additional_detour_minutes: int = Field(..., description="Estimated additional detour time")

class MatchScore(BaseModel):
    """Breakdown of compatibility scoring (0-100)"""
    trip_id: str
    score: float = Field(..., ge=0, le=100, description="Overall compatibility score")
    detour_additional: int = Field(..., description="Additional detour in minutes")
    proximity_score: float = Field(..., ge=0, le=100, description="Geographic proximity score")
    time_compatibility_score: float = Field(..., ge=0, le=100, description="Temporal compatibility score")

class MatchResult(BaseModel):
    """
    Result of matching evaluation for a single trip.
    Contains compatibility decision and detailed scoring.
    """
    trip_id: str
    is_compatible: bool
    reason: Optional[str] = None  # Explanation if not compatible

    # Trip information
    trip_origin: str
    trip_destination: str
    departure_time: time
    available_seats: int

    # Detour analysis
    current_detour_minutes: int
    max_detour_minutes: int
    additional_detour_minutes: Optional[int] = None
    projected_total_detour: Optional[int] = None

    # Proposed insertion (if compatible)
    proposed_insertion: Optional[WaypointInsertion] = None

    # Scoring (if compatible)
    match_score: Optional[MatchScore] = None

    # Driver info
    driver_id: str
```

---

## Domain Services

### GeoCalculator Utility

```python
# apps/matching/domain/services/geo_calculator.py

import math
from apps.matching.domain.value_objects import Coordinates

class GeoCalculator:
    """
    Pure utility class for geographic calculations.
    Zero dependencies on frameworks or infrastructure.
    """

    @staticmethod
    def haversine_distance(coord1: Coordinates, coord2: Coordinates) -> float:
        """
        Calculate great-circle distance between two points using Haversine formula.

        Args:
            coord1: First coordinate
            coord2: Second coordinate

        Returns:
            Distance in kilometers
        """
        R = 6371.0  # Earth radius in kilometers

        lat1 = math.radians(coord1.latitude)
        lat2 = math.radians(coord2.latitude)
        dlat = math.radians(coord2.latitude - coord1.latitude)
        dlon = math.radians(coord2.longitude - coord1.longitude)

        a = (math.sin(dlat / 2) ** 2 +
             math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2)
        c = 2 * math.asin(math.sqrt(a))

        return R * c

    @staticmethod
    def estimate_detour_minutes(distance_km: float, avg_speed_kmh: float = 80.0) -> int:
        """
        Estimate travel time for a detour.

        Args:
            distance_km: Detour distance in kilometers
            avg_speed_kmh: Average speed (default: 80 km/h for highways)

        Returns:
            Estimated time in minutes (rounded up)
        """
        if distance_km <= 0:
            return 0
        hours = distance_km / avg_speed_kmh
        return int(math.ceil(hours * 60))

    @staticmethod
    def is_point_near_segment(
        point: Coordinates,
        segment_start: Coordinates,
        segment_end: Coordinates,
        threshold_km: float = 15.0
    ) -> bool:
        """
        Check if a point is near a line segment (simplified algorithm for MVP).

        Uses a simplified approach: checks if average distance to segment endpoints
        is within threshold. More sophisticated perpendicular distance calculation
        can be implemented in future iterations.

        Args:
            point: Point to check
            segment_start: Start of line segment
            segment_end: End of line segment
            threshold_km: Maximum acceptable distance

        Returns:
            True if point is near the segment
        """
        dist_to_start = GeoCalculator.haversine_distance(point, segment_start)
        dist_to_end = GeoCalculator.haversine_distance(point, segment_end)

        # If close to either endpoint, consider it near
        if dist_to_start <= threshold_km or dist_to_end <= threshold_km:
            return True

        # Check if point is roughly "between" the endpoints
        # Simplified: use average distance as approximation
        avg_distance = (dist_to_start + dist_to_end) / 2
        segment_length = GeoCalculator.haversine_distance(segment_start, segment_end)

        # If point is "on the way", avg distance should be close to half segment length
        # For MVP, just check if avg distance is reasonable
        return avg_distance <= threshold_km * 1.5
```

### Matching Service Interface

```python
# apps/matching/domain/services/matching_service.py

from abc import ABC, abstractmethod
from typing import List, Optional
from apps.matching.domain.entities import TravelRequest
from apps.matching.domain.value_objects import MatchResult

class IMatchingService(ABC):
    """
    Domain service contract for trip matching.
    Defines the interface without implementation details.
    """

    @abstractmethod
    async def find_compatible_trips(
        self,
        travel_request: TravelRequest
    ) -> List[MatchResult]:
        """
        Find all compatible trips for a travel request.

        Algorithm:
        1. Query trips by date
        2. Filter by seat availability
        3. Evaluate geographic compatibility
        4. Evaluate temporal compatibility
        5. Verify cumulative detour constraint
        6. Calculate compatibility scores
        7. Sort by score descending

        Args:
            travel_request: The passenger's travel request

        Returns:
            List of MatchResult, sorted by score (best first)
        """
        pass

    @abstractmethod
    async def evaluate_single_trip(
        self,
        travel_request: TravelRequest,
        trip_id: str
    ) -> Optional[MatchResult]:
        """
        Evaluate compatibility of a specific trip.

        Args:
            travel_request: The passenger's travel request
            trip_id: Specific trip to evaluate

        Returns:
            MatchResult or None if trip not found
        """
        pass
```

---

## Application Services

### Matching Service Implementation

```python
# apps/matching/application/services/matching_service.py

from typing import List, Optional
from datetime import time as time_type
from apps.matching.domain.entities import TravelRequest
from apps.matching.domain.value_objects import (
    MatchResult, MatchScore, WaypointInsertion, Coordinates
)
from apps.matching.domain.services.matching_service import IMatchingService
from apps.matching.domain.services.geo_calculator import GeoCalculator
from apps.trips.domain.repositories.trip_repository import ITripRepository

class MatchingService(IMatchingService):
    """
    Concrete implementation of matching algorithm.
    Orchestrates domain logic and repository queries.
    """

    def __init__(self, trip_repository: ITripRepository):
        self.trip_repo = trip_repository
        self.geo_calc = GeoCalculator()

    async def find_compatible_trips(
        self,
        travel_request: TravelRequest
    ) -> List[MatchResult]:
        """
        Main matching algorithm implementation.
        """
        # Step 1: Fetch trips for requested date
        trips = await self.trip_repo.find_by_date(
            date=travel_request.travel_date,
            status="active"
        )

        # Step 2: Filter trips with sufficient seats
        trips = [
            t for t in trips
            if t.available_seats >= travel_request.seats_requested
        ]

        # Step 3: Evaluate each trip
        results: List[MatchResult] = []
        for trip in trips:
            result = await self._evaluate_trip(travel_request, trip)
            if result:
                results.append(result)

        # Step 4: Filter compatible and sort by score
        compatible = [r for r in results if r.is_compatible]
        compatible.sort(
            key=lambda r: r.match_score.score if r.match_score else 0,
            reverse=True
        )

        return compatible

    async def evaluate_single_trip(
        self,
        travel_request: TravelRequest,
        trip_id: str
    ) -> Optional[MatchResult]:
        """
        Evaluate a specific trip.
        """
        trip = await self.trip_repo.get_by_id(trip_id)
        if not trip:
            return None
        return await self._evaluate_trip(travel_request, trip)

    async def _evaluate_trip(self, travel_request: TravelRequest, trip) -> Optional[MatchResult]:
        """
        Core evaluation logic for a single trip.

        Checks:
        1. Temporal compatibility
        2. Geographic compatibility (pickup/dropoff near route)
        3. Cumulative detour constraint
        4. Calculates scores
        """
        # Base result template
        base_result = {
            "trip_id": trip.id,
            "trip_origin": trip.origin,
            "trip_destination": trip.destination,
            "departure_time": trip.departure_time,
            "available_seats": trip.available_seats,
            "current_detour_minutes": trip.current_detour_minutes,
            "max_detour_minutes": trip.max_detour_minutes,
            "driver_id": trip.driver_id
        }

        # Check 1: Temporal compatibility
        if not self._is_time_compatible(
            trip.departure_time,
            travel_request.time_from,
            travel_request.time_to
        ):
            return MatchResult(
                **base_result,
                is_compatible=False,
                reason="Horario no compatible con preferencias del pasajero"
            )

        # Check 2: Geographic coordinates present
        if not all([
            trip.origin_lat, trip.origin_lng,
            trip.destination_lat, trip.destination_lng
        ]):
            return MatchResult(
                **base_result,
                is_compatible=False,
                reason="Trayecto no tiene coordenadas geocodificadas"
            )

        # Create coordinate objects
        req_origin = Coordinates(
            latitude=travel_request.origin_lat,
            longitude=travel_request.origin_lng
        )
        req_dest = Coordinates(
            latitude=travel_request.destination_lat,
            longitude=travel_request.destination_lng
        )
        trip_origin = Coordinates(
            latitude=trip.origin_lat,
            longitude=trip.origin_lng
        )
        trip_dest = Coordinates(
            latitude=trip.destination_lat,
            longitude=trip.destination_lng
        )

        # Check 3: Pickup point near trip route
        if not self.geo_calc.is_point_near_segment(
            req_origin, trip_origin, trip_dest, threshold_km=15.0
        ):
            return MatchResult(
                **base_result,
                is_compatible=False,
                reason="Punto de recogida demasiado lejos de la ruta (>15km)"
            )

        # Check 4: Dropoff point near trip route
        if not self.geo_calc.is_point_near_segment(
            req_dest, trip_origin, trip_dest, threshold_km=15.0
        ):
            return MatchResult(
                **base_result,
                is_compatible=False,
                reason="Punto de destino demasiado lejos de la ruta (>15km)"
            )

        # Check 5: Calculate detour
        detour_dist_pickup = self.geo_calc.haversine_distance(trip_origin, req_origin)
        detour_dist_dropoff = self.geo_calc.haversine_distance(req_dest, trip_dest)
        total_detour_km = detour_dist_pickup + detour_dist_dropoff

        additional_detour_min = self.geo_calc.estimate_detour_minutes(total_detour_km)
        projected_total = trip.current_detour_minutes + additional_detour_min

        # Check 6: Cumulative detour constraint (CRITICAL)
        if projected_total > trip.max_detour_minutes:
            return MatchResult(
                **base_result,
                is_compatible=False,
                reason=f"Desvío acumulado excedido: {projected_total} > {trip.max_detour_minutes} min",
                additional_detour_minutes=additional_detour_min,
                projected_total_detour=projected_total
            )

        # Calculate scores
        proximity_score = self._calculate_proximity_score(
            detour_dist_pickup, detour_dist_dropoff
        )
        time_score = self._calculate_time_score(
            trip.departure_time,
            travel_request.time_from,
            travel_request.time_to
        )

        # Weighted final score
        final_score = 0.6 * proximity_score + 0.4 * time_score

        # Build proposed insertion
        proposed_insertion = WaypointInsertion(
            pickup_index=0,  # Simplified: insert at beginning
            dropoff_index=1,  # Simplified: insert after pickup
            pickup_location={
                "lat": req_origin.latitude,
                "lng": req_origin.longitude,
                "address": travel_request.origin_address
            },
            dropoff_location={
                "lat": req_dest.latitude,
                "lng": req_dest.longitude,
                "address": travel_request.destination_address
            },
            additional_detour_minutes=additional_detour_min
        )

        match_score = MatchScore(
            trip_id=trip.id,
            score=final_score,
            detour_additional=additional_detour_min,
            proximity_score=proximity_score,
            time_compatibility_score=time_score
        )

        return MatchResult(
            **base_result,
            is_compatible=True,
            additional_detour_minutes=additional_detour_min,
            projected_total_detour=projected_total,
            proposed_insertion=proposed_insertion,
            match_score=match_score
        )

    def _is_time_compatible(
        self,
        trip_time: time_type,
        time_from: Optional[time_type],
        time_to: Optional[time_type]
    ) -> bool:
        """Check if trip departure time is within passenger's time range"""
        if time_from and trip_time < time_from:
            return False
        if time_to and trip_time > time_to:
            return False
        return True

    def _calculate_proximity_score(
        self,
        pickup_dist_km: float,
        dropoff_dist_km: float
    ) -> float:
        """
        Calculate proximity score (0-100) based on distance.
        Closer distances get higher scores.
        """
        total_dist = pickup_dist_km + dropoff_dist_km

        if total_dist <= 5:
            return 100.0
        elif total_dist <= 10:
            return 90.0
        elif total_dist <= 20:
            return 70.0
        elif total_dist <= 30:
            return 50.0
        else:
            # Linear decay after 30km
            return max(0.0, 50.0 - (total_dist - 30))

    def _calculate_time_score(
        self,
        trip_time: time_type,
        time_from: Optional[time_type],
        time_to: Optional[time_type]
    ) -> float:
        """
        Calculate time compatibility score (0-100).
        Perfect match = 100, outside range = 50.
        """
        if not time_from and not time_to:
            return 100.0  # No time constraint = perfect

        if time_from and time_to:
            if time_from <= trip_time <= time_to:
                return 100.0
            else:
                return 50.0

        if time_from:
            return 100.0 if trip_time >= time_from else 50.0

        if time_to:
            return 100.0 if trip_time <= time_to else 50.0

        return 100.0
```

---

## Repository Implementation

### SQLAlchemy Repository

```python
# apps/matching/adapters/repositories/travel_request_repository.py

from typing import List, Optional
from datetime import date
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from apps.matching.domain.repositories.travel_request_repository import ITravelRequestRepository
from apps.matching.domain.entities import TravelRequest, TravelRequestStatus
from apps.matching.adapters.orm.models import TravelRequestORM
from apps.matching.adapters.orm.mappers import to_domain, from_domain
import uuid

class SQLAlchemyTravelRequestRepository(ITravelRequestRepository):
    """
    SQLAlchemy implementation of travel request repository.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, travel_request: TravelRequest) -> TravelRequest:
        """Persist new travel request"""
        if not travel_request.id:
            travel_request.id = str(uuid.uuid4())

        orm_obj = from_domain(travel_request)
        self.session.add(orm_obj)
        await self.session.commit()
        await self.session.refresh(orm_obj)

        return to_domain(orm_obj)

    async def get_by_id(self, request_id: str) -> Optional[TravelRequest]:
        """Fetch by ID"""
        stmt = select(TravelRequestORM).where(TravelRequestORM.id == request_id)
        result = await self.session.execute(stmt)
        orm_obj = result.scalar_one_or_none()

        return to_domain(orm_obj) if orm_obj else None

    async def get_by_passenger(
        self,
        passenger_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[TravelRequest]:
        """Fetch all requests by passenger"""
        stmt = (
            select(TravelRequestORM)
            .where(TravelRequestORM.passenger_id == passenger_id)
            .order_by(TravelRequestORM.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        orm_objs = result.scalars().all()

        return [to_domain(obj) for obj in orm_objs]

    async def find_pending_by_date(self, travel_date: date) -> List[TravelRequest]:
        """Find pending requests for a specific date"""
        stmt = select(TravelRequestORM).where(
            and_(
                TravelRequestORM.travel_date == travel_date,
                TravelRequestORM.status == TravelRequestStatusEnum.PENDING
            )
        )
        result = await self.session.execute(stmt)
        orm_objs = result.scalars().all()

        return [to_domain(obj) for obj in orm_objs]

    async def update(self, travel_request: TravelRequest) -> bool:
        """Update existing travel request"""
        stmt = select(TravelRequestORM).where(TravelRequestORM.id == travel_request.id)
        result = await self.session.execute(stmt)
        orm_obj = result.scalar_one_or_none()

        if not orm_obj:
            return False

        # Update fields
        orm_obj.status = travel_request.status.value
        orm_obj.matched_trip_id = travel_request.matched_trip_id
        orm_obj.updated_at = travel_request.updated_at

        await self.session.commit()
        return True

    async def delete(self, request_id: str) -> bool:
        """Delete travel request"""
        stmt = select(TravelRequestORM).where(TravelRequestORM.id == request_id)
        result = await self.session.execute(stmt)
        orm_obj = result.scalar_one_or_none()

        if not orm_obj:
            return False

        await self.session.delete(orm_obj)
        await self.session.commit()
        return True
```

### ORM Mappers

```python
# apps/matching/adapters/orm/mappers.py

from apps.matching.domain.entities import TravelRequest, TravelRequestStatus
from apps.matching.adapters.orm.models import TravelRequestORM, TravelRequestStatusEnum

def to_domain(orm_obj: TravelRequestORM) -> TravelRequest:
    """Convert ORM model to domain entity"""
    return TravelRequest(
        id=orm_obj.id,
        passenger_id=orm_obj.passenger_id,
        origin_lat=orm_obj.origin_lat,
        origin_lng=orm_obj.origin_lng,
        destination_lat=orm_obj.destination_lat,
        destination_lng=orm_obj.destination_lng,
        origin_address=orm_obj.origin_address,
        destination_address=orm_obj.destination_address,
        travel_date=orm_obj.travel_date,
        time_from=orm_obj.time_from,
        time_to=orm_obj.time_to,
        seats_requested=orm_obj.seats_requested,
        passenger_notes=orm_obj.passenger_notes,
        status=TravelRequestStatus(orm_obj.status.value),
        matched_trip_id=orm_obj.matched_trip_id,
        created_at=orm_obj.created_at,
        updated_at=orm_obj.updated_at
    )

def from_domain(entity: TravelRequest) -> TravelRequestORM:
    """Convert domain entity to ORM model"""
    return TravelRequestORM(
        id=entity.id,
        passenger_id=entity.passenger_id,
        origin_lat=entity.origin_lat,
        origin_lng=entity.origin_lng,
        destination_lat=entity.destination_lat,
        destination_lng=entity.destination_lng,
        origin_address=entity.origin_address,
        destination_address=entity.destination_address,
        travel_date=entity.travel_date,
        time_from=entity.time_from,
        time_to=entity.time_to,
        seats_requested=entity.seats_requested,
        passenger_notes=entity.passenger_notes,
        status=TravelRequestStatusEnum[entity.status.value.upper()],
        matched_trip_id=entity.matched_trip_id,
        created_at=entity.created_at,
        updated_at=entity.updated_at
    )
```

---

## HTTP Entrypoints

### Request/Response Schemas

```python
# apps/matching/entrypoints/http/schemas/matching.py

from pydantic import BaseModel, Field
from datetime import date, time
from typing import Optional, List

class CreateTravelRequestDTO(BaseModel):
    """DTO for creating travel request"""
    origin_address: str = Field(..., min_length=3, max_length=500)
    destination_address: str = Field(..., min_length=3, max_length=500)
    travel_date: date
    time_from: Optional[time] = None
    time_to: Optional[time] = None
    seats_requested: int = Field(default=1, ge=1, le=10)
    passenger_notes: Optional[str] = Field(None, max_length=1000)

    class Config:
        json_schema_extra = {
            "example": {
                "origin_address": "Jerez de la Frontera, España",
                "destination_address": "Dos Hermanas, España",
                "travel_date": "2025-12-15",
                "time_from": "09:00:00",
                "time_to": "11:00:00",
                "seats_requested": 1,
                "passenger_notes": "Prefiero no fumar"
            }
        }

class TravelRequestResponseDTO(BaseModel):
    """DTO for travel request response"""
    id: str
    passenger_id: str
    origin_lat: float
    origin_lng: float
    destination_lat: float
    destination_lng: float
    origin_address: Optional[str]
    destination_address: Optional[str]
    travel_date: date
    time_from: Optional[time]
    time_to: Optional[time]
    seats_requested: int
    passenger_notes: Optional[str]
    status: str
    matched_trip_id: Optional[str]
    created_at: str

class AcceptMatchDTO(BaseModel):
    """DTO for accepting a match"""
    trip_id: str = Field(..., description="ID of trip to book")

class AcceptMatchResponseDTO(BaseModel):
    """DTO for accept match response"""
    message: str
    booking_id: str
    trip_id: str

class MatchResultResponseDTO(BaseModel):
    """DTO for match result (wraps domain MatchResult)"""
    # Reuse domain value object structure
    pass  # Import and extend from domain.value_objects.MatchResult

class MatchListResponseDTO(BaseModel):
    """DTO for list of matches"""
    travel_request_id: str
    matches: List[MatchResultResponseDTO]
    total_matches: int
```

### FastAPI Router

```python
# apps/matching/entrypoints/http/routers/matching.py

from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, status
from apps.matching.domain.entities import TravelRequest
from apps.matching.domain.services.matching_service import IMatchingService
from apps.matching.domain.repositories.travel_request_repository import ITravelRequestRepository
from apps.matching.entrypoints.http.schemas.matching import (
    CreateTravelRequestDTO,
    TravelRequestResponseDTO,
    AcceptMatchDTO,
    AcceptMatchResponseDTO,
    MatchListResponseDTO
)
from apps.matching.entrypoints.http.dependencies import (
    get_matching_service,
    get_travel_request_repository
)
from apps.users.entrypoints.http.dependencies import get_current_user
from apps.maps.domain.services.map_service import IMapService
from apps.maps.entrypoints.http.dependencies import get_map_service

router = APIRouter(prefix="/api/v1/matching", tags=["Matching"])

@router.post("/travel-requests", response_model=TravelRequestResponseDTO, status_code=status.HTTP_201_CREATED)
async def create_travel_request(
    payload: CreateTravelRequestDTO,
    current_user: Annotated[dict, Depends(get_current_user)],
    travel_request_repo: Annotated[ITravelRequestRepository, Depends(get_travel_request_repository)],
    map_service: Annotated[IMapService, Depends(get_map_service)]
):
    """
    Create a new travel request.

    Process:
    1. Geocode origin and destination addresses
    2. Create TravelRequest domain entity
    3. Persist to database
    4. Return response with coordinates
    """
    # Geocode origin
    origin_coords = await map_service.geocode(payload.origin_address)
    if not origin_coords:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Origin address not found: {payload.origin_address}"
        )

    # Geocode destination
    dest_coords = await map_service.geocode(payload.destination_address)
    if not dest_coords:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Destination address not found: {payload.destination_address}"
        )

    # Create domain entity
    travel_request = TravelRequest(
        passenger_id=current_user["id"],
        origin_lat=origin_coords.latitude,
        origin_lng=origin_coords.longitude,
        destination_lat=dest_coords.latitude,
        destination_lng=dest_coords.longitude,
        origin_address=payload.origin_address,
        destination_address=payload.destination_address,
        travel_date=payload.travel_date,
        time_from=payload.time_from,
        time_to=payload.time_to,
        seats_requested=payload.seats_requested,
        passenger_notes=payload.passenger_notes
    )

    # Persist
    created = await travel_request_repo.create(travel_request)

    return TravelRequestResponseDTO(
        id=created.id,
        passenger_id=created.passenger_id,
        origin_lat=created.origin_lat,
        origin_lng=created.origin_lng,
        destination_lat=created.destination_lat,
        destination_lng=created.destination_lng,
        origin_address=created.origin_address,
        destination_address=created.destination_address,
        travel_date=created.travel_date,
        time_from=created.time_from,
        time_to=created.time_to,
        seats_requested=created.seats_requested,
        passenger_notes=created.passenger_notes,
        status=created.status.value,
        matched_trip_id=created.matched_trip_id,
        created_at=created.created_at.isoformat()
    )

@router.get("/travel-requests/{request_id}/matches", response_model=MatchListResponseDTO)
async def find_matches(
    request_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    matching_service: Annotated[IMatchingService, Depends(get_matching_service)],
    travel_request_repo: Annotated[ITravelRequestRepository, Depends(get_travel_request_repository)]
):
    """
    Find compatible trips for a travel request.

    Executes matching algorithm and returns sorted results.
    """
    # Fetch travel request
    travel_request = await travel_request_repo.get_by_id(request_id)
    if not travel_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Travel request not found"
        )

    # Verify ownership
    if travel_request.passenger_id != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this travel request"
        )

    # Execute matching
    matches = await matching_service.find_compatible_trips(travel_request)

    return MatchListResponseDTO(
        travel_request_id=request_id,
        matches=[m.dict() for m in matches],
        total_matches=len(matches)
    )

@router.post("/travel-requests/{request_id}/accept", response_model=AcceptMatchResponseDTO, status_code=status.HTTP_201_CREATED)
async def accept_match(
    request_id: str,
    payload: AcceptMatchDTO,
    current_user: Annotated[dict, Depends(get_current_user)],
    matching_service: Annotated[IMatchingService, Depends(get_matching_service)],
    travel_request_repo: Annotated[ITravelRequestRepository, Depends(get_travel_request_repository)]
):
    """
    Accept a match and create booking.

    This endpoint:
    1. Re-validates compatibility
    2. Creates booking via BookingService
    3. Updates trip roadmap
    4. Updates trip current_detour
    5. Marks travel request as accepted
    """
    # Implementation delegates to use case
    # (Implementation would call accept_match use case)
    pass

@router.get("/my-travel-requests", response_model=List[TravelRequestResponseDTO])
async def get_my_travel_requests(
    current_user: Annotated[dict, Depends(get_current_user)],
    travel_request_repo: Annotated[ITravelRequestRepository, Depends(get_travel_request_repository)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500)
):
    """List current user's travel requests"""
    requests = await travel_request_repo.get_by_passenger(
        current_user["id"],
        skip=skip,
        limit=limit
    )

    return [
        TravelRequestResponseDTO(
            id=r.id,
            passenger_id=r.passenger_id,
            origin_lat=r.origin_lat,
            origin_lng=r.origin_lng,
            destination_lat=r.destination_lat,
            destination_lng=r.destination_lng,
            origin_address=r.origin_address,
            destination_address=r.destination_address,
            travel_date=r.travel_date,
            time_from=r.time_from,
            time_to=r.time_to,
            seats_requested=r.seats_requested,
            passenger_notes=r.passenger_notes,
            status=r.status.value,
            matched_trip_id=r.matched_trip_id,
            created_at=r.created_at.isoformat()
        )
        for r in requests
    ]

@router.delete("/travel-requests/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_travel_request(
    request_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    travel_request_repo: Annotated[ITravelRequestRepository, Depends(get_travel_request_repository)]
):
    """Cancel a travel request"""
    travel_request = await travel_request_repo.get_by_id(request_id)
    if not travel_request:
        raise HTTPException(status_code=404, detail="Travel request not found")

    if travel_request.passenger_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    try:
        travel_request.cancel()
        await travel_request_repo.update(travel_request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return None
```

### Dependency Injection

```python
# apps/matching/entrypoints/http/dependencies.py

from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from config.database import get_db_session
from apps.matching.domain.services.matching_service import IMatchingService
from apps.matching.application.services.matching_service import MatchingService
from apps.matching.domain.repositories.travel_request_repository import ITravelRequestRepository
from apps.matching.adapters.repositories.travel_request_repository import SQLAlchemyTravelRequestRepository
from apps.trips.entrypoints.http.dependencies import get_trip_repository
from apps.trips.domain.repositories.trip_repository import ITripRepository

async def get_travel_request_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)]
) -> ITravelRequestRepository:
    """Inject travel request repository"""
    return SQLAlchemyTravelRequestRepository(session)

async def get_matching_service(
    trip_repo: Annotated[ITripRepository, Depends(get_trip_repository)]
) -> IMatchingService:
    """Inject matching service"""
    return MatchingService(trip_repository=trip_repo)
```

---

## Testing Strategy

### Integration Tests

**File**: `tests/integration/matching/test_matching_service.py`

```python
import pytest
from datetime import date, time
from apps.matching.application.services.matching_service import MatchingService
from apps.matching.domain.entities import TravelRequest

@pytest.mark.asyncio
class TestMatchingService:
    """Integration tests for matching algorithm"""

    async def test_find_compatible_trips_basic(self, db_session, sample_trips):
        """Test basic matching with geographic proximity"""
        # Arrange: Create travel request
        travel_request = TravelRequest(
            passenger_id="passenger_1",
            origin_lat=36.5271,  # Jerez
            origin_lng=-6.2886,
            destination_lat=37.3891,  # Dos Hermanas
            destination_lng=-5.9845,
            travel_date=date(2025, 12, 15),
            seats_requested=1
        )

        # Act: Find matches
        matching_service = MatchingService(trip_repository=...)
        results = await matching_service.find_compatible_trips(travel_request)

        # Assert
        assert len(results) > 0
        assert all(r.is_compatible for r in results)
        assert results[0].match_score.score >= results[-1].match_score.score  # Sorted

    async def test_detour_constraint_respected(self, db_session):
        """Test that trips exceeding max detour are filtered out"""
        # Arrange: Trip with low max_detour, request far away
        # Act: Find matches
        # Assert: No compatible trips due to detour constraint
        pass

    async def test_time_compatibility_filtering(self, db_session):
        """Test temporal filtering with time_from and time_to"""
        # Arrange: Travel request with specific time window
        # Act: Find matches
        # Assert: Only trips within time window returned
        pass

    async def test_geographic_threshold(self, db_session):
        """Test that trips too far away are filtered out"""
        # Arrange: Request with origin/destination far from any trip
        # Act: Find matches
        # Assert: No compatible trips (geographic threshold exceeded)
        pass
```

### Unit Tests

**File**: `tests/unit/matching/test_geo_calculator.py`

```python
import pytest
from apps.matching.domain.services.geo_calculator import GeoCalculator
from apps.matching.domain.value_objects import Coordinates

class TestGeoCalculator:
    """Unit tests for geographic calculations"""

    def test_haversine_distance_known_values(self):
        """Test Haversine with known city distances"""
        madrid = Coordinates(latitude=40.4168, longitude=-3.7038)
        barcelona = Coordinates(latitude=41.3851, longitude=2.1734)

        distance = GeoCalculator.haversine_distance(madrid, barcelona)

        # Approximately 504 km
        assert 500 <= distance <= 510

    def test_estimate_detour_minutes(self):
        """Test detour time estimation"""
        distance_km = 80.0
        minutes = GeoCalculator.estimate_detour_minutes(distance_km, avg_speed_kmh=80.0)

        assert minutes == 60  # 80km at 80km/h = 1 hour = 60 minutes

    def test_is_point_near_segment(self):
        """Test point-to-segment proximity check"""
        # Arrange
        segment_start = Coordinates(latitude=36.0, longitude=-6.0)
        segment_end = Coordinates(latitude=37.0, longitude=-5.0)
        point_near = Coordinates(latitude=36.5, longitude=-5.5)
        point_far = Coordinates(latitude=40.0, longitude=-3.0)

        # Act & Assert
        assert GeoCalculator.is_point_near_segment(point_near, segment_start, segment_end, threshold_km=15.0)
        assert not GeoCalculator.is_point_near_segment(point_far, segment_start, segment_end, threshold_km=15.0)
```

### Contract Tests

**File**: `tests/contract/test_matching_api.py`

```python
import pytest
from httpx import AsyncClient
from datetime import date

@pytest.mark.asyncio
class TestMatchingAPIContracts:
    """Contract tests for matching endpoints"""

    async def test_create_travel_request_contract(self, async_client: AsyncClient, auth_token):
        """Test POST /travel-requests response contract"""
        response = await async_client.post(
            "/api/v1/matching/travel-requests",
            json={
                "origin_address": "Jerez de la Frontera, España",
                "destination_address": "Dos Hermanas, España",
                "travel_date": "2025-12-15",
                "seats_requested": 1
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 201
        data = response.json()

        # Validate response schema
        assert "id" in data
        assert "origin_lat" in data
        assert "origin_lng" in data
        assert "destination_lat" in data
        assert "destination_lng" in data
        assert data["status"] == "pending"

    async def test_find_matches_contract(self, async_client: AsyncClient, auth_token, sample_travel_request_id):
        """Test GET /travel-requests/{id}/matches response contract"""
        response = await async_client.get(
            f"/api/v1/matching/travel-requests/{sample_travel_request_id}/matches",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 200
        data = response.json()

        # Validate response schema
        assert "travel_request_id" in data
        assert "matches" in data
        assert "total_matches" in data

        if len(data["matches"]) > 0:
            match = data["matches"][0]
            assert "trip_id" in match
            assert "is_compatible" in match
            assert "match_score" in match
            assert match["match_score"]["score"] >= 0
            assert match["match_score"]["score"] <= 100
```

### Test Fixtures

**File**: `tests/fixtures/matching_fixtures.py`

```python
import pytest
from datetime import date, time
from apps.matching.domain.entities import TravelRequest

@pytest.fixture
def sample_travel_request():
    """Sample travel request for testing"""
    return TravelRequest(
        passenger_id="test_passenger",
        origin_lat=36.5271,
        origin_lng=-6.2886,
        destination_lat=37.3891,
        destination_lng=-5.9845,
        origin_address="Jerez de la Frontera",
        destination_address="Dos Hermanas",
        travel_date=date(2025, 12, 15),
        time_from=time(9, 0),
        time_to=time(11, 0),
        seats_requested=1
    )

@pytest.fixture
def sample_trips(db_session):
    """Create sample trips in database for matching tests"""
    # Create trips with various routes and availability
    pass
```

---

## Dependencies

### Required Packages

```toml
[tool.poetry.dependencies]
python = "^3.11"

# Core framework
fastapi = "^0.104.0"
uvicorn = {extras = ["standard"], version = "^0.24.0"}

# Data validation
pydantic = "^2.5.0"
pydantic-settings = "^2.1.0"

# Database
sqlalchemy = {extras = ["asyncio"], version = "^2.0.23"}
aiosqlite = "^0.19.0"  # Async SQLite driver
alembic = "^1.12.1"

# Geographic calculations (optional - we implement Haversine manually)
# geopy = "^2.4.0"  # Only if needed for geocoding

[tool.poetry.group.dev.dependencies]
# Testing
pytest = "^7.4.3"
pytest-asyncio = "^0.21.1"
httpx = "^0.25.2"
pytest-cov = "^4.1.0"

# Linting
ruff = "^0.1.7"
black = "^23.12.0"
mypy = "^1.7.1"
```

### Why These Dependencies?

- **FastAPI**: Modern async web framework with OpenAPI docs
- **SQLAlchemy 2.0**: Async ORM with type hints
- **aiosqlite**: Async driver for SQLite3
- **Alembic**: Database migrations
- **Pydantic v2**: Data validation and serialization (5-10x faster than v1)
- **pytest-asyncio**: Async test support
- **httpx**: Async HTTP client for integration tests

---

## Observability

### Logging Strategy

```python
# apps/matching/application/services/matching_service.py

import logging
from typing import List
from apps.matching.domain.entities import TravelRequest
from apps.matching.domain.value_objects import MatchResult

logger = logging.getLogger(__name__)

class MatchingService:
    async def find_compatible_trips(self, travel_request: TravelRequest) -> List[MatchResult]:
        logger.info(
            "Executing matching algorithm",
            extra={
                "travel_request_id": travel_request.id,
                "passenger_id": travel_request.passenger_id,
                "travel_date": str(travel_request.travel_date),
                "origin": f"{travel_request.origin_lat},{travel_request.origin_lng}",
                "destination": f"{travel_request.destination_lat},{travel_request.destination_lng}"
            }
        )

        trips = await self.trip_repo.find_by_date(...)
        logger.debug(f"Found {len(trips)} candidate trips for matching")

        results = []
        for trip in trips:
            result = await self._evaluate_trip(travel_request, trip)
            if result and result.is_compatible:
                logger.debug(
                    f"Compatible trip found: {trip.id} with score {result.match_score.score}"
                )
            results.append(result)

        compatible_count = sum(1 for r in results if r.is_compatible)
        logger.info(
            f"Matching complete: {compatible_count}/{len(results)} compatible trips",
            extra={
                "travel_request_id": travel_request.id,
                "total_evaluated": len(results),
                "compatible_count": compatible_count
            }
        )

        return results
```

### Metrics (Future Enhancement)

Consider adding Prometheus metrics:
- `matching_requests_total`: Counter of matching requests
- `matching_duration_seconds`: Histogram of matching algorithm execution time
- `matching_results_count`: Histogram of number of compatible trips found
- `geographic_calculation_duration`: Timing for Haversine calculations

---

## Open Questions

1. **Roadmap Insertion Algorithm**: The current implementation uses simplified insertion logic (pickup at index 0, dropoff at index 1). Should we implement more sophisticated insertion logic that:
   - Finds optimal insertion points in existing roadmap?
   - Minimizes total detour across all passengers?
   - Considers geographical order of waypoints?

2. **Background Matching**: Should we implement a background job that automatically notifies passengers when new compatible trips are published? This would require:
   - Celery or similar task queue
   - Notification service integration
   - TravelRequest status transitions

3. **Caching Strategy**: Should we cache matching results for a short TTL (e.g., 5 minutes) to avoid re-calculating for repeated requests? Consider:
   - Redis cache for hot paths
   - Cache invalidation on trip updates
   - Trade-off: freshness vs performance

4. **Geographic Complexity**: The current `is_point_near_segment` uses a simplified algorithm. Should we implement:
   - Perpendicular distance to line segment?
   - Route-based distance via OSRM/routing API?
   - Voronoi/spatial partitioning for large-scale matching?

5. **Trip Repository Dependency**: The matching service depends on the Trip repository from `apps/trips`. Should this be injected via interface to maintain loose coupling, or is direct dependency acceptable within the same monolith?

6. **Accept Match Transaction**: The `accept_match` operation involves multiple updates (booking, trip roadmap, travel request status). Should this be wrapped in a distributed transaction or use saga pattern?

---

## Implementation Checklist

### Phase 1: Domain Layer (No External Dependencies)
- [ ] Create `apps/matching/domain/entities.py`
  - [ ] TravelRequest dataclass
  - [ ] TravelRequestStatus enum
  - [ ] Domain validation logic
- [ ] Create `apps/matching/domain/value_objects.py`
  - [ ] Coordinates
  - [ ] MatchResult
  - [ ] MatchScore
  - [ ] WaypointInsertion
- [ ] Create `apps/matching/domain/services/geo_calculator.py`
  - [ ] haversine_distance()
  - [ ] estimate_detour_minutes()
  - [ ] is_point_near_segment()
- [ ] Create `apps/matching/domain/services/matching_service.py`
  - [ ] IMatchingService interface
- [ ] Create `apps/matching/domain/repositories/travel_request_repository.py`
  - [ ] ITravelRequestRepository interface

### Phase 2: Adapters Layer (Infrastructure)
- [ ] Create `apps/matching/adapters/orm/models.py`
  - [ ] TravelRequestORM SQLAlchemy model
  - [ ] TravelRequestStatusEnum
- [ ] Create `apps/matching/adapters/orm/mappers.py`
  - [ ] to_domain() converter
  - [ ] from_domain() converter
- [ ] Create `apps/matching/adapters/repositories/travel_request_repository.py`
  - [ ] SQLAlchemyTravelRequestRepository
  - [ ] Implement all CRUD methods
- [ ] Create Alembic migration
  - [ ] `alembic revision -m "create travel_requests table"`
  - [ ] Define schema with indexes
  - [ ] Run migration: `alembic upgrade head`

### Phase 3: Application Layer (Use Cases & Services)
- [ ] Create `apps/matching/application/services/matching_service.py`
  - [ ] MatchingService implementation
  - [ ] find_compatible_trips() algorithm
  - [ ] evaluate_single_trip() method
  - [ ] _evaluate_trip() private method
  - [ ] Scoring functions (_calculate_proximity_score, _calculate_time_score)
- [ ] Create `apps/matching/application/use_cases/find_compatible_trips.py` (optional)
- [ ] Create `apps/matching/application/use_cases/accept_match.py` (optional)

### Phase 4: HTTP Entrypoints
- [ ] Create `apps/matching/entrypoints/http/schemas/matching.py`
  - [ ] CreateTravelRequestDTO
  - [ ] TravelRequestResponseDTO
  - [ ] AcceptMatchDTO
  - [ ] MatchListResponseDTO
- [ ] Create `apps/matching/entrypoints/http/dependencies.py`
  - [ ] get_travel_request_repository()
  - [ ] get_matching_service()
- [ ] Create `apps/matching/entrypoints/http/routers/matching.py`
  - [ ] POST /travel-requests
  - [ ] GET /travel-requests/{id}/matches
  - [ ] POST /travel-requests/{id}/accept
  - [ ] GET /my-travel-requests
  - [ ] DELETE /travel-requests/{id}
- [ ] Register router in `main.py`

### Phase 5: Testing
- [ ] Write unit tests for GeoCalculator
  - [ ] Test haversine_distance with known values
  - [ ] Test detour estimation
  - [ ] Test point-to-segment proximity
- [ ] Write integration tests for MatchingService
  - [ ] Test basic matching flow
  - [ ] Test detour constraint enforcement
  - [ ] Test time compatibility filtering
  - [ ] Test geographic threshold
- [ ] Write contract tests for API endpoints
  - [ ] Test request/response schemas
  - [ ] Test error responses
  - [ ] Test authorization
- [ ] Create test fixtures
  - [ ] Sample travel requests
  - [ ] Sample trips with various routes

### Phase 6: Validation & Documentation
- [ ] Test all endpoints via Swagger UI (`/docs`)
- [ ] Verify database schema with `sqlite3` or DB browser
- [ ] Test matching algorithm with realistic data
- [ ] Document API in OpenAPI (auto-generated)
- [ ] Add logging for observability
- [ ] Review with team for feedback

### Phase 7: Integration with Existing Features
- [ ] Ensure geocoding service integration works (RF-005 dependency)
- [ ] Integrate with Trip repository (RF-001 dependency)
- [ ] Integrate accept_match with BookingService (RF-003)
- [ ] Test end-to-end flow: create request → find matches → accept → booking created

---

## Acceptance Criteria (from RF-006)

- [x] **AC1**: System executes automated matching algorithm
  - Implementation: `MatchingService.find_compatible_trips()`

- [x] **AC2**: Identifies geographic and temporal coincidences
  - Implementation: Geographic checks via `GeoCalculator`, temporal checks in `_is_time_compatible()`

- [x] **AC3**: Verifies cumulative maximum detour
  - Implementation: `projected_total = current_detour + additional_detour <= max_detour`

- [x] **AC4**: Generates prioritized suggestions
  - Implementation: Sorted by `match_score.score` descending

- [x] **AC5**: Users receive relevant matches
  - Implementation: API returns only compatible trips with scores

- [x] **AC6**: Algorithm works with exact and approximate searches
  - Implementation: Threshold-based proximity (`is_point_near_segment`) allows flexible matching

- [x] **AC7**: Matching updates when new trips are published
  - Implementation: Stateless algorithm queries fresh trip data on each request

---

## Next Steps After Implementation

Once RF-006 is complete, consider these enhancements:

1. **RF-BONUS-001: Approximate Geographic Matching**
   - Implement perpendicular distance to route
   - Add routing API integration (OSRM)
   - Optimize with spatial indexes (PostGIS if migrating from SQLite)

2. **RF-BONUS-002: CO₂ Savings Estimation**
   - Calculate emissions saved per trip
   - Display on match results
   - Aggregate user impact statistics

3. **Background Matching Job**
   - Celery periodic task to find matches for pending TravelRequests
   - Send notifications when new compatible trips are published

4. **Machine Learning Score Enhancement**
   - Train model on accepted matches to improve scoring
   - Personalize scores based on passenger preferences

5. **Performance Optimization**
   - Add Redis caching for hot matching queries
   - Implement pagination for large result sets
   - Add database query optimization (explain analyze)

---

## Summary

This implementation plan provides a complete roadmap for building the RF-006 Advanced Matching Engine with:

- **Clean Architecture**: Pure domain logic separated from infrastructure
- **Async SQLite**: Modern async database access with SQLAlchemy 2.0
- **Geographic Intelligence**: Haversine distance calculations and detour estimation
- **Scoring Algorithm**: Multi-factor compatibility scoring (proximity + time)
- **Cumulative Detour Constraint**: Enforces business rule preventing excessive detours
- **RESTful API**: FastAPI endpoints with Pydantic validation
- **Comprehensive Testing**: Unit, integration, and contract tests
- **Production-Ready**: Logging, error handling, and security (auth)

The plan maintains architectural integrity by enforcing strict dependency rules: domain layer has zero framework dependencies, application layer orchestrates use cases, adapters handle infrastructure concerns, and HTTP entrypoints translate between HTTP and domain models.

Implementation should proceed in phases, starting with domain logic (which can be tested in isolation) and progressively adding infrastructure and HTTP layers.
