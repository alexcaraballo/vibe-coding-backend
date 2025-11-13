# FastAPI Implementation Plan: RF-BONUS-003 - Passenger Visibility & Privacy

**Status**: READY
**Version**: 1.0.0
**Last Updated**: 2025-11-13
**Related Docs**:
- Functional Requirements: `.claude/plans/10-RF-BONUS-003-visualizacion-reservas-otros.md`
- Dependencies: RF-003 (Trip Booking), RF-004 (Booking Listing)

**Feature Type**: BONUS/OPTIONAL - Privacy & Transparency Enhancement
**Priority**: LOW
**Estimated Effort**: 2-3 hours

---

## Summary

Implements a privacy-respecting passenger visibility system allowing drivers and confirmed passengers to view fellow travelers in a trip. Extends existing booking functionality with user privacy controls, public profile management, and selective information sharing.

**Core Capabilities:**
- Drivers see all confirmed passengers in their trips
- Confirmed passengers see fellow travelers for coordination
- User-controlled privacy settings (email, phone, profile visibility)
- Public profile system with bio and photo
- Permission-based access control (only trip participants)

**Architecture Pattern**: Clean Architecture with application service layer handling permission logic and privacy filtering.

---

## Architecture Mapping

### Domain → FastAPI Mapping

| Domain Concept | FastAPI Construct | Location | Notes |
|---------------|------------------|----------|-------|
| User Privacy Settings | Domain Model Fields | `apps/users/domain/models.py` | Add privacy flags to User model |
| Public Profile Logic | Domain Method | `User.get_public_profile()` | Privacy-aware profile builder |
| Passenger Visibility Rules | Application Service | `apps/trips/infrastructure/services/` | Permission + privacy logic |
| Privacy Configuration | Request/Response DTOs | `apps/users/api/versioning/v1/schemas/` | Privacy settings schemas |
| Passenger List View | Response DTO | `apps/trips/api/versioning/v1/schemas/responses.py` | Public passenger profiles |

### Layer Responsibilities

**Domain Layer** (`apps/users/domain/`, `apps/trips/domain/`):
- User model with privacy fields: `profile_photo_url`, `show_email_to_fellow_travelers`, `show_phone_to_fellow_travelers`, `bio`
- `User.get_public_profile(is_fellow_traveler: bool)` method returning filtered profile dict
- Pure business logic, no HTTP or database dependencies

**Application Layer** (`apps/trips/infrastructure/services/`):
- `PassengerVisibilityService`: Orchestrates permission checks and profile aggregation
- `can_view_passengers()`: Authorization logic (driver or confirmed passenger)
- `get_trip_passengers()`: Aggregates driver + passengers with privacy filtering
- Depends on repository interfaces, not implementations

**Adapters Layer** (`apps/users/infrastructure/repositories/`):
- User repository queries (already implemented in RF-001)
- No new repository methods required
- Uses existing `IUserRepository.get_by_id()`, `ITripRepository.get_by_id()`, `IBookingRepository.get_by_trip()`

**HTTP Entrypoints** (`apps/trips/api/versioning/v1/`, `apps/users/api/versioning/v1/`):
- `GET /trips/{trip_id}/passengers` - View trip participants
- `PUT /users/me/privacy-settings` - Update privacy configuration
- `GET /users/me/privacy-settings` - Get current privacy settings
- FastAPI dependency injection for authentication and service wiring

---

## File Actions

### Modify Existing Files

#### 1. `apps/users/domain/models.py`
**Purpose**: Add privacy fields and public profile logic to User model

**Changes Required**:
```python
# ADD new fields to User class:
profile_photo_url: Optional[str] = Field(None, max_length=500)
show_email_to_fellow_travelers: bool = Field(default=False)
show_phone_to_fellow_travelers: bool = Field(default=False)
bio: Optional[str] = Field(None, max_length=500)

# ADD new method:
def get_public_profile(self, is_fellow_traveler: bool = False) -> dict:
    """Returns privacy-filtered profile dictionary"""
    # Returns name, photo, bio always
    # Returns email/phone only if flags are True AND is_fellow_traveler=True
```

**SQLAlchemy Migration**: Required for new database columns
- Migration file: `alembic/versions/xxx_add_user_privacy_fields.py`
- Add columns: `profile_photo_url`, `show_email_to_fellow_travelers`, `show_phone_to_fellow_travelers`, `bio`

#### 2. `apps/users/infrastructure/persistence/sqlalchemy_models.py`
**Purpose**: Add SQLAlchemy columns for privacy fields

**Changes Required**:
```python
# ADD to UserTable:
profile_photo_url = Column(String(500), nullable=True)
show_email_to_fellow_travelers = Column(Boolean, default=False, nullable=False)
show_phone_to_fellow_travelers = Column(Boolean, default=False, nullable=False)
bio = Column(String(500), nullable=True)
```

#### 3. `apps/users/api/versioning/v1/schemas/responses.py`
**Purpose**: Add privacy settings response schema

**Changes Required**:
```python
# ADD new schema:
class PrivacySettingsResponse(BaseModel):
    show_email_to_fellow_travelers: bool
    show_phone_to_fellow_travelers: bool
    profile_photo_url: Optional[str]
    bio: Optional[str]
```

#### 4. `apps/users/api/versioning/v1/views.py`
**Purpose**: Add privacy settings endpoints

**Changes Required**:
```python
# ADD endpoints:
# PUT /users/me/privacy-settings
# GET /users/me/privacy-settings
```

#### 5. `apps/trips/api/versioning/v1/views.py`
**Purpose**: Add passenger list endpoint

**Changes Required**:
```python
# ADD endpoint:
# GET /trips/{trip_id}/passengers
```

### Create New Files

#### 6. `apps/trips/api/versioning/v1/schemas/passenger_schemas.py`
**Purpose**: DTOs for passenger visibility responses

**Contents**:
```python
class PassengerPublicProfileResponse(BaseModel):
    user_id: str
    name: str
    profile_photo_url: Optional[str] = None
    bio: Optional[str] = None
    seats_booked: int
    pickup_location: Optional[str] = None
    dropoff_location: Optional[str] = None
    email: Optional[str] = None  # Only if shared
    phone: Optional[str] = None  # Only if shared

class TripPassengersResponse(BaseModel):
    trip_id: str
    driver: PassengerPublicProfileResponse
    passengers: list[PassengerPublicProfileResponse]
    total_passengers: int
    available_seats: int
```

#### 7. `apps/trips/infrastructure/services/passenger_visibility_service.py`
**Purpose**: Application service for passenger visibility logic

**Contents**:
```python
class PassengerVisibilityService:
    def __init__(self, trip_repo, booking_repo, user_repo):
        # Store repository dependencies

    async def can_view_passengers(self, trip_id: str, user_id: str) -> bool:
        """Returns True if user is driver or confirmed passenger"""
        # Check if user is trip driver
        # OR has active confirmed booking for this trip

    async def get_trip_passengers(
        self,
        trip_id: str,
        requesting_user_id: str
    ) -> TripPassengersResponse:
        """Returns driver + passengers with privacy-filtered profiles"""
        # 1. Check permissions with can_view_passengers()
        # 2. Get trip and driver
        # 3. Get confirmed bookings
        # 4. Build driver profile with get_public_profile(is_fellow_traveler=True)
        # 5. Build passenger profiles with privacy filtering
        # 6. Return TripPassengersResponse
```

**Key Logic**:
- Permission check: `trip.driver_id == user_id OR has_active_booking`
- Privacy filtering: Use `User.get_public_profile(is_fellow_traveler=True)`
- Only return confirmed bookings with `status="confirmed"` and `is_active=True`

#### 8. `apps/users/api/versioning/v1/schemas/privacy_schemas.py`
**Purpose**: Request schema for privacy settings update

**Contents**:
```python
class UpdatePrivacySettingsRequest(BaseModel):
    show_email_to_fellow_travelers: Optional[bool] = None
    show_phone_to_fellow_travelers: Optional[bool] = None
    profile_photo_url: Optional[str] = Field(None, max_length=500)
    bio: Optional[str] = Field(None, max_length=500)

    # All fields optional to allow partial updates
```

#### 9. `apps/trips/infrastructure/dependencies.py` (if not exists)
**Purpose**: Dependency injection for PassengerVisibilityService

**Contents**:
```python
async def get_passenger_visibility_service(
    trip_repo: Annotated[ITripRepository, Depends(get_trip_repository)],
    booking_repo: Annotated[IBookingRepository, Depends(get_booking_repository)],
    user_repo: Annotated[IUserRepository, Depends(get_user_repository)]
) -> PassengerVisibilityService:
    return PassengerVisibilityService(trip_repo, booking_repo, user_repo)
```

---

## API Endpoints

| Method | Path | Request Model | Response Model | Use Case | Auth | Permission |
|--------|------|--------------|----------------|----------|------|-----------|
| GET | `/api/v1/trips/{trip_id}/passengers` | - | `TripPassengersResponse` | View fellow travelers | Required | Driver or confirmed passenger |
| PUT | `/api/v1/users/me/privacy-settings` | `UpdatePrivacySettingsRequest` | `PrivacySettingsResponse` | Configure privacy | Required | Self only |
| GET | `/api/v1/users/me/privacy-settings` | - | `PrivacySettingsResponse` | Get current settings | Required | Self only |

### Endpoint Details

#### GET /trips/{trip_id}/passengers

**Authorization Logic**:
1. User must be authenticated
2. User must be EITHER:
   - The trip driver (`trip.driver_id == current_user.id`)
   - OR a confirmed passenger (has active booking with `status="confirmed"`)
3. Returns 403 Forbidden if neither condition met

**Response Construction**:
```python
# Driver profile always includes:
- user_id, name, profile_photo_url, bio
- email/phone IF driver.show_*_to_fellow_travelers = True

# Passenger profiles include:
- user_id, name, profile_photo_url, bio, seats_booked
- pickup_location, dropoff_location (from booking)
- email/phone IF passenger.show_*_to_fellow_travelers = True
```

**SQLAlchemy Queries**:
```python
# 1. Check if user is driver
trip = await session.get(TripTable, trip_id)
is_driver = (trip.driver_id == user_id)

# 2. Check if user has confirmed booking
stmt = select(BookingTable).where(
    BookingTable.trip_id == trip_id,
    BookingTable.passenger_id == user_id,
    BookingTable.status == "confirmed",
    BookingTable.is_active == True
)
booking = await session.scalar(stmt)
is_passenger = booking is not None

# 3. Get all confirmed bookings
stmt = select(BookingTable).where(
    BookingTable.trip_id == trip_id,
    BookingTable.status == "confirmed",
    BookingTable.is_active == True
)
bookings = await session.scalars(stmt)

# 4. Get user profiles for driver + passengers
user_ids = [trip.driver_id] + [b.passenger_id for b in bookings]
stmt = select(UserTable).where(UserTable.id.in_(user_ids))
users = await session.scalars(stmt)
```

#### PUT /users/me/privacy-settings

**Update Logic**:
```python
# Partial update - only update provided fields
if payload.show_email_to_fellow_travelers is not None:
    user.show_email_to_fellow_travelers = payload.show_email_to_fellow_travelers
if payload.show_phone_to_fellow_travelers is not None:
    user.show_phone_to_fellow_travelers = payload.show_phone_to_fellow_travelers
if payload.profile_photo_url is not None:
    user.profile_photo_url = payload.profile_photo_url
if payload.bio is not None:
    user.bio = payload.bio

await user_repo.update(user.id, user)
```

**Validation**:
- `profile_photo_url`: Max 500 characters, must be valid URL format
- `bio`: Max 500 characters
- Boolean flags: No validation needed

---

## Dependencies

### Required Packages

**No New Dependencies Required** - Uses existing stack:

```toml
[tool.poetry.dependencies]
# Already installed:
fastapi = "^0.104.0"         # HTTP framework
pydantic = "^2.5.0"          # Validation and serialization
sqlalchemy = "^2.0.0"        # Database ORM
alembic = "^1.12.0"          # Migrations

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.0"            # Testing
httpx = "^0.25.0"            # HTTP client for tests
pytest-asyncio = "^0.21.0"   # Async test support
```

### Dependency Injection Hierarchy

```
FastAPI Endpoint (GET /trips/{trip_id}/passengers)
    ↓ Depends(get_current_user)
    ├─→ CurrentUser (from JWT token)
    ↓ Depends(get_passenger_visibility_service)
    └─→ PassengerVisibilityService
        ↓ __init__ dependencies
        ├─→ ITripRepository (Depends: get_trip_repository)
        ├─→ IBookingRepository (Depends: get_booking_repository)
        └─→ IUserRepository (Depends: get_user_repository)
            ↓ Each repository depends on
            └─→ AsyncSession (Depends: get_db_session)
```

**Dependency Lifecycle**:
- `AsyncSession`: Per-request scope (transaction boundary)
- Repositories: Per-request scope (stateless)
- Services: Per-request scope (stateless)
- `CurrentUser`: Per-request scope (from authentication middleware)

---

## Data Persistence

### SQLAlchemy Models

#### UserTable Extensions

```python
# apps/users/infrastructure/persistence/sqlalchemy_models.py

class UserTable(Base):
    __tablename__ = "users"

    # Existing fields...
    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    phone = Column(String)

    # NEW FIELDS:
    profile_photo_url = Column(String(500), nullable=True)
    show_email_to_fellow_travelers = Column(Boolean, default=False, nullable=False)
    show_phone_to_fellow_travelers = Column(Boolean, default=False, nullable=False)
    bio = Column(String(500), nullable=True)
```

### Migration Strategy

**Migration File**: `alembic/versions/xxx_add_user_privacy_fields.py`

```python
def upgrade() -> None:
    op.add_column('users', sa.Column('profile_photo_url', sa.String(500), nullable=True))
    op.add_column('users', sa.Column('show_email_to_fellow_travelers', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('show_phone_to_fellow_travelers', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('bio', sa.String(500), nullable=True))

def downgrade() -> None:
    op.drop_column('users', 'bio')
    op.drop_column('users', 'show_phone_to_fellow_travelers')
    op.drop_column('users', 'show_email_to_fellow_travelers')
    op.drop_column('users', 'profile_photo_url')
```

**Migration Commands**:
```bash
# Generate migration
alembic revision --autogenerate -m "add_user_privacy_fields"

# Apply migration
alembic upgrade head

# Rollback if needed
alembic downgrade -1
```

### Repository Interface

**No new repository methods required** - Uses existing:

```python
# From IUserRepository:
async def get_by_id(self, user_id: str) -> Optional[User]
async def update(self, user_id: str, user: User) -> User

# From ITripRepository:
async def get_by_id(self, trip_id: str) -> Optional[Trip]

# From IBookingRepository:
async def get_by_trip(self, trip_id: str, skip: int = 0, limit: int = 100) -> list[Booking]
# Note: May need to add filtering by status="confirmed" and is_active=True
# OR filter in application service layer
```

**Repository Enhancement (Optional)**:
```python
# Add to IBookingRepository if performance is critical:
async def get_confirmed_bookings_by_trip(self, trip_id: str) -> list[Booking]:
    """Returns only confirmed and active bookings"""
    # WHERE trip_id = ? AND status = 'confirmed' AND is_active = true
```

---

## Error Handling

### Domain Error Mapping

| Error Condition | HTTP Status | Error Response | Handler Location |
|----------------|-------------|---------------|------------------|
| User not authenticated | 401 Unauthorized | `{"detail": "Not authenticated"}` | FastAPI auth middleware |
| User not trip participant | 403 Forbidden | `{"detail": "No tienes permiso para ver los pasajeros de este trayecto"}` | `PassengerVisibilityService.get_trip_passengers()` |
| Trip not found | 404 Not Found | `{"detail": "Trayecto no encontrado"}` | `PassengerVisibilityService.get_trip_passengers()` |
| User not found | 404 Not Found | `{"detail": "Usuario no encontrado"}` | `PassengerVisibilityService.get_trip_passengers()` |
| Invalid privacy settings | 422 Unprocessable Entity | Pydantic validation errors | FastAPI automatic validation |

### Exception Handlers

**Application Service Exceptions**:
```python
# In PassengerVisibilityService.get_trip_passengers()

# Permission denied
if not can_view:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="No tienes permiso para ver los pasajeros de este trayecto"
    )

# Trip not found
if not trip:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Trayecto no encontrado"
    )

# Driver not found (shouldn't happen but defensive)
if not driver:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Conductor no encontrado"
    )
```

**Endpoint-Level Error Handling**:
- Pydantic handles all request validation automatically
- Service layer raises HTTPException (propagates to client)
- No custom exception handler needed for this feature

---

## Testing Strategy

### Integration Tests

**Test File**: `tests/test_trips/test_passenger_visibility.py`

#### Test Scenarios

| Test Name | Scenario | Expected Result | Setup Required |
|-----------|----------|-----------------|----------------|
| `test_driver_can_view_passengers` | Driver requests passenger list | 200 OK with driver + passengers | Trip with driver auth token |
| `test_confirmed_passenger_can_view` | Confirmed passenger requests list | 200 OK with driver + passengers | Trip + confirmed booking + passenger token |
| `test_pending_passenger_cannot_view` | Pending passenger requests list | 403 Forbidden | Trip + pending booking + passenger token |
| `test_external_user_cannot_view` | Unrelated user requests list | 403 Forbidden | Trip + external user token |
| `test_privacy_email_hidden` | Privacy disabled for email | Response excludes email field | User with `show_email_to_fellow_travelers=False` |
| `test_privacy_email_shown` | Privacy enabled for email | Response includes email field | User with `show_email_to_fellow_travelers=True` |
| `test_privacy_phone_hidden` | Privacy disabled for phone | Response excludes phone field | User with `show_phone_to_fellow_travelers=False` |
| `test_only_confirmed_bookings` | Trip has pending + confirmed | Only confirmed in response | Multiple bookings with different statuses |
| `test_update_privacy_settings` | User updates privacy | 200 OK with updated values | Auth token |
| `test_get_privacy_settings` | User fetches current settings | 200 OK with all privacy fields | Auth token |
| `test_partial_privacy_update` | User updates only bio | Other fields unchanged | Existing user with privacy settings |

#### Test Fixtures

```python
# conftest.py additions

@pytest.fixture
async def trip_with_passengers(db_session, driver_user, passenger_users):
    """Creates trip with driver and multiple confirmed passengers"""
    trip = create_test_trip(driver_id=driver_user.id)
    bookings = [
        create_test_booking(
            trip_id=trip.id,
            passenger_id=passenger.id,
            status="confirmed",
            is_active=True
        )
        for passenger in passenger_users
    ]
    return trip, bookings

@pytest.fixture
def auth_token_driver(driver_user):
    """JWT token for driver"""
    return create_jwt_token(user_id=driver_user.id)

@pytest.fixture
def auth_token_passenger(passenger_users):
    """JWT token for first passenger"""
    return create_jwt_token(user_id=passenger_users[0].id)

@pytest.fixture
def auth_token_external(external_user):
    """JWT token for non-participant user"""
    return create_jwt_token(user_id=external_user.id)

@pytest.fixture
async def user_with_privacy_settings(db_session):
    """User with specific privacy configuration"""
    user = create_test_user(
        show_email_to_fellow_travelers=True,
        show_phone_to_fellow_travelers=False,
        bio="Test bio"
    )
    return user
```

#### Example Test Implementation

```python
@pytest.mark.asyncio
async def test_driver_can_view_passengers(
    client: AsyncClient,
    trip_with_passengers,
    auth_token_driver
):
    """Test that trip driver can view all confirmed passengers"""
    trip, bookings = trip_with_passengers

    response = await client.get(
        f"/api/v1/trips/{trip.id}/passengers",
        headers={"Authorization": f"Bearer {auth_token_driver}"}
    )

    assert response.status_code == 200
    data = response.json()

    # Verify structure
    assert "trip_id" in data
    assert "driver" in data
    assert "passengers" in data
    assert "total_passengers" in data
    assert "available_seats" in data

    # Verify driver info
    assert data["driver"]["user_id"] == trip.driver_id
    assert data["driver"]["name"] is not None
    assert data["driver"]["seats_booked"] == 0

    # Verify passenger count
    assert data["total_passengers"] == len(bookings)
    assert len(data["passengers"]) == len(bookings)

    # Verify passenger info
    for passenger_data in data["passengers"]:
        assert "user_id" in passenger_data
        assert "name" in passenger_data
        assert "seats_booked" in passenger_data
        assert passenger_data["seats_booked"] > 0

@pytest.mark.asyncio
async def test_privacy_settings_respected(
    client: AsyncClient,
    trip_with_passengers,
    user_with_privacy_settings,
    auth_token_driver
):
    """Test that email/phone only shown when user enables sharing"""
    trip, _ = trip_with_passengers

    response = await client.get(
        f"/api/v1/trips/{trip.id}/passengers",
        headers={"Authorization": f"Bearer {auth_token_driver}"}
    )

    assert response.status_code == 200
    passengers = response.json()["passengers"]

    # Find passenger with specific privacy settings
    test_passenger = next(
        p for p in passengers
        if p["user_id"] == user_with_privacy_settings.id
    )

    # Email should be present (enabled)
    assert "email" in test_passenger
    assert test_passenger["email"] is not None

    # Phone should be absent (disabled)
    assert test_passenger.get("phone") is None
```

### Contract Tests

**Test File**: `tests/test_trips/test_passenger_visibility_contracts.py`

```python
@pytest.mark.asyncio
async def test_passenger_list_response_schema():
    """Verify response matches TripPassengersResponse schema"""
    # Use Pydantic schema validation to ensure contract compliance
    response_data = {
        "trip_id": "test-trip-id",
        "driver": {
            "user_id": "driver-id",
            "name": "Driver Name",
            "seats_booked": 0
        },
        "passengers": [
            {
                "user_id": "pass-1",
                "name": "Passenger One",
                "seats_booked": 2,
                "email": "pass1@test.com"
            }
        ],
        "total_passengers": 1,
        "available_seats": 2
    }

    # Should not raise ValidationError
    validated = TripPassengersResponse(**response_data)
    assert validated.trip_id == "test-trip-id"
    assert len(validated.passengers) == 1

@pytest.mark.asyncio
async def test_privacy_settings_request_schema():
    """Verify UpdatePrivacySettingsRequest accepts partial updates"""
    # Only bio provided
    request_data = {"bio": "New bio"}
    validated = UpdatePrivacySettingsRequest(**request_data)
    assert validated.bio == "New bio"
    assert validated.show_email_to_fellow_travelers is None

    # All fields provided
    request_data = {
        "show_email_to_fellow_travelers": True,
        "show_phone_to_fellow_travelers": False,
        "profile_photo_url": "https://example.com/photo.jpg",
        "bio": "Full update"
    }
    validated = UpdatePrivacySettingsRequest(**request_data)
    assert validated.show_email_to_fellow_travelers is True
```

### Test Database Strategy

**Use SQLite in-memory for tests**:
```python
# tests/conftest.py

@pytest.fixture
async def test_db():
    """Creates in-memory SQLite database for tests"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    yield async_session

    await engine.dispose()
```

---

## Observability

### Logging

**Structured Logging Points**:

```python
# In PassengerVisibilityService

import logging
logger = logging.getLogger(__name__)

async def get_trip_passengers(self, trip_id: str, requesting_user_id: str):
    logger.info(
        "Fetching trip passengers",
        extra={
            "trip_id": trip_id,
            "requesting_user_id": requesting_user_id,
            "action": "get_trip_passengers"
        }
    )

    can_view = await self.can_view_passengers(trip_id, requesting_user_id)
    if not can_view:
        logger.warning(
            "Unauthorized passenger list access attempt",
            extra={
                "trip_id": trip_id,
                "requesting_user_id": requesting_user_id,
                "reason": "not_trip_participant"
            }
        )
        raise HTTPException(status_code=403, ...)

    # ... rest of implementation

    logger.info(
        "Trip passengers retrieved successfully",
        extra={
            "trip_id": trip_id,
            "passenger_count": len(passengers_responses)
        }
    )
```

**Log Levels**:
- `INFO`: Successful operations, passenger list retrieval, privacy updates
- `WARNING`: Permission denied attempts
- `ERROR`: Unexpected errors (trip not found shouldn't happen after permission check)

### Metrics

**Recommended Metrics** (if using Prometheus):

```python
# Endpoint metrics (automatic via FastAPI middleware)
http_requests_total{method="GET", endpoint="/trips/{trip_id}/passengers"}
http_request_duration_seconds{method="GET", endpoint="/trips/{trip_id}/passengers"}

# Custom business metrics
passenger_list_views_total{viewer_role="driver"}  # Counter
passenger_list_views_total{viewer_role="passenger"}  # Counter
privacy_settings_updates_total{field="email"}  # Counter
privacy_settings_updates_total{field="phone"}  # Counter
```

### Tracing

**Not Required for Bonus Feature** - Standard FastAPI request tracing sufficient.

If implementing OpenTelemetry in future:
- Trace `PassengerVisibilityService.get_trip_passengers()` span
- Add attributes: `trip_id`, `passenger_count`, `viewer_role`

---

## Open Questions

### 1. **Profile Photo Storage Strategy**
**Question**: Where are profile photos hosted? Are we storing URLs to external services (e.g., S3, Cloudinary) or handling uploads?

**Impact**:
- If handling uploads: Need file upload endpoint, storage service integration
- If external URLs: Just validate URL format

**Recommendation**: Store URLs only (no upload handling in this feature). Add upload endpoint in separate feature if needed.

---

### 2. **Pickup/Dropoff Location Granularity**
**Question**: What level of location detail is shown in passenger profiles? Full address or just city/area?

**Current Implementation**: Uses `booking.pickup_location` and `booking.dropoff_location` strings as-is.

**Privacy Consideration**: May want to show only city/neighborhood, not exact address.

**Recommendation**: If locations contain addresses, truncate to city level in `PassengerPublicProfileResponse`.

---

### 3. **Inactive/Cancelled Bookings**
**Question**: Should we show count of cancelled passengers? ("2 passengers cancelled")

**Current Implementation**: Only shows active confirmed bookings.

**Recommendation**: Keep current approach (confirmed only) to avoid confusion. Historical data not relevant for coordination.

---

### 4. **Real-time Updates**
**Question**: Do clients need real-time updates when passengers join/leave (WebSocket)?

**Current Implementation**: REST API only, clients must poll.

**Recommendation**: Acceptable for bonus feature. Add WebSocket notifications in future enhancement if needed.

---

## Implementation Checklist

### Phase 1: Domain & Database (30 min)
- [ ] Add privacy fields to `User` domain model (`apps/users/domain/models.py`)
  - [ ] `profile_photo_url: Optional[str]`
  - [ ] `show_email_to_fellow_travelers: bool`
  - [ ] `show_phone_to_fellow_travelers: bool`
  - [ ] `bio: Optional[str]`
- [ ] Implement `User.get_public_profile(is_fellow_traveler: bool)` method
- [ ] Add columns to `UserTable` SQLAlchemy model (`apps/users/infrastructure/persistence/sqlalchemy_models.py`)
- [ ] Generate Alembic migration: `alembic revision --autogenerate -m "add_user_privacy_fields"`
- [ ] Review and edit migration file
- [ ] Apply migration: `alembic upgrade head`
- [ ] Verify columns in SQLite: `.schema users`

### Phase 2: Application Layer (45 min)
- [ ] Create `apps/trips/api/versioning/v1/schemas/passenger_schemas.py`
  - [ ] `PassengerPublicProfileResponse` schema
  - [ ] `TripPassengersResponse` schema
- [ ] Create `apps/users/api/versioning/v1/schemas/privacy_schemas.py`
  - [ ] `UpdatePrivacySettingsRequest` schema
  - [ ] `PrivacySettingsResponse` schema
- [ ] Create `apps/trips/infrastructure/services/passenger_visibility_service.py`
  - [ ] `PassengerVisibilityService` class
  - [ ] `can_view_passengers()` method with permission logic
  - [ ] `get_trip_passengers()` method with privacy filtering
- [ ] Add dependency injection in `apps/trips/infrastructure/dependencies.py`
  - [ ] `get_passenger_visibility_service()` function

### Phase 3: HTTP Endpoints (30 min)
- [ ] Add passenger list endpoint in `apps/trips/api/versioning/v1/views.py`
  - [ ] `GET /trips/{trip_id}/passengers` endpoint
  - [ ] Wire up `PassengerVisibilityService` dependency
  - [ ] Add docstring with examples
- [ ] Add privacy endpoints in `apps/users/api/versioning/v1/views.py`
  - [ ] `PUT /users/me/privacy-settings` endpoint
  - [ ] `GET /users/me/privacy-settings` endpoint
  - [ ] Handle partial updates (only provided fields)

### Phase 4: Testing (45 min)
- [ ] Create `tests/test_trips/test_passenger_visibility.py`
  - [ ] Test: Driver can view passengers
  - [ ] Test: Confirmed passenger can view
  - [ ] Test: Pending passenger gets 403
  - [ ] Test: External user gets 403
  - [ ] Test: Email shown when privacy enabled
  - [ ] Test: Email hidden when privacy disabled
  - [ ] Test: Phone shown/hidden based on settings
  - [ ] Test: Only confirmed bookings returned
- [ ] Create `tests/test_users/test_privacy_settings.py`
  - [ ] Test: Update all privacy fields
  - [ ] Test: Partial update (only bio)
  - [ ] Test: Get current settings
  - [ ] Test: Invalid data rejected (422)
- [ ] Create test fixtures in `tests/conftest.py`
  - [ ] `trip_with_passengers` fixture
  - [ ] `user_with_privacy_settings` fixture
  - [ ] Auth token fixtures for different roles
- [ ] Run tests: `pytest tests/test_trips/test_passenger_visibility.py -v`
- [ ] Run tests: `pytest tests/test_users/test_privacy_settings.py -v`

### Phase 5: Documentation & Verification (15 min)
- [ ] Test endpoints manually via `/docs` (Swagger UI)
  - [ ] Create test trip with passengers
  - [ ] Test GET /trips/{id}/passengers as driver
  - [ ] Test GET /trips/{id}/passengers as passenger
  - [ ] Test GET /trips/{id}/passengers as external user (expect 403)
  - [ ] Test PUT /users/me/privacy-settings
  - [ ] Test GET /users/me/privacy-settings
- [ ] Verify OpenAPI schema in Swagger UI
  - [ ] Check request/response examples
  - [ ] Verify field descriptions
- [ ] Add structured logging to service methods
- [ ] Update `README.md` with new endpoints (if project has API docs)
- [ ] Mark feature as COMPLETE in requirements doc

### Phase 6: Code Review Checklist
- [ ] Domain layer has no FastAPI dependencies
- [ ] Privacy logic in domain model (`get_public_profile()`)
- [ ] Permission checks before data access
- [ ] Proper HTTP status codes (401, 403, 404, 422)
- [ ] All privacy fields optional in partial updates
- [ ] Email/phone excluded from response when privacy disabled
- [ ] Only confirmed bookings included in results
- [ ] Tests cover both happy path and error cases
- [ ] No N+1 queries (bulk fetch users for all passengers)
- [ ] Proper async/await usage throughout

---

## Verification Commands

### Manual Testing

```bash
# 1. Apply database migration
alembic upgrade head

# 2. Start FastAPI server
uvicorn main:app --reload

# 3. Create test users and trip (via /docs or curl)

# 4. Update privacy settings
curl -X PUT http://localhost:8000/api/v1/users/me/privacy-settings \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "show_email_to_fellow_travelers": true,
    "show_phone_to_fellow_travelers": false,
    "profile_photo_url": "https://example.com/photo.jpg",
    "bio": "Viajero frecuente, me encanta compartir historias"
  }'

# 5. Get current privacy settings
curl http://localhost:8000/api/v1/users/me/privacy-settings \
  -H "Authorization: Bearer YOUR_TOKEN"

# 6. View trip passengers (as driver or passenger)
curl http://localhost:8000/api/v1/trips/{TRIP_ID}/passengers \
  -H "Authorization: Bearer DRIVER_OR_PASSENGER_TOKEN"

# 7. Try to view as external user (should get 403)
curl http://localhost:8000/api/v1/trips/{TRIP_ID}/passengers \
  -H "Authorization: Bearer EXTERNAL_USER_TOKEN"
```

### Database Verification

```bash
# Check that new columns exist
sqlite3 app.db ".schema users"

# Verify privacy settings for a user
sqlite3 app.db "SELECT id, name, show_email_to_fellow_travelers, show_phone_to_fellow_travelers, bio FROM users LIMIT 1;"

# Check confirmed bookings for a trip
sqlite3 app.db "SELECT * FROM bookings WHERE trip_id='TRIP_ID' AND status='confirmed' AND is_active=1;"
```

### Automated Tests

```bash
# Run all passenger visibility tests
pytest tests/test_trips/test_passenger_visibility.py -v

# Run privacy settings tests
pytest tests/test_users/test_privacy_settings.py -v

# Run with coverage
pytest tests/test_trips/test_passenger_visibility.py --cov=apps/trips/infrastructure/services --cov-report=term-missing

# Run integration tests only
pytest tests/test_trips/test_passenger_visibility.py -m integration -v
```

---

## Success Criteria

### Functional Requirements
✅ **Driver can view all passengers**: Driver token returns 200 with all confirmed bookings
✅ **Confirmed passenger can view**: Passenger with `status="confirmed"` gets 200 response
✅ **Pending passenger denied**: Passenger with `status="pending"` gets 403 Forbidden
✅ **External user denied**: User without booking gets 403 Forbidden
✅ **Privacy settings honored**: Email/phone only in response when user enables sharing
✅ **Only confirmed bookings**: Response excludes pending/cancelled bookings
✅ **Profile info included**: Name, photo, bio always present in response
✅ **Partial updates work**: Can update single privacy field without affecting others

### Technical Requirements
✅ **Clean Architecture preserved**: Domain → Application → Adapters → HTTP layers respected
✅ **No domain pollution**: `User` model has no FastAPI imports
✅ **Repository abstraction**: Service depends on `IUserRepository`, not implementation
✅ **Async throughout**: All repository calls use `async/await`
✅ **Proper error handling**: HTTPException with correct status codes
✅ **Test coverage**: All scenarios covered in integration tests
✅ **Migration applied**: Alembic migration adds columns successfully
✅ **OpenAPI documented**: Endpoints visible in `/docs` with examples

### Non-Functional Requirements
✅ **Performance**: No N+1 queries (bulk fetch users)
✅ **Security**: Only trip participants can access passenger list
✅ **Privacy**: No sensitive data exposed without consent
✅ **Maintainability**: Service class encapsulates all business logic
✅ **Testability**: All components mockable via dependency injection

---

## Future Enhancements

### Discussed in Requirements Doc

1. **Real-time Updates** (RF-BONUS-004 dependency)
   - WebSocket notifications when passengers join/leave
   - Live passenger count updates

2. **Chat Integration** (RF-BONUS-004)
   - Private chat between trip participants
   - Group chat for all passengers

3. **Reputation System**
   - Star ratings for drivers and passengers
   - Verified user badges
   - "Frequent traveler" indicators

4. **Social Features**
   - Introduction messages ("Looking forward to the trip!")
   - Social media profile linking (verification)
   - Common interest matching

5. **Advanced Privacy Controls**
   - Granular visibility rules (show phone only to driver, not passengers)
   - Temporary visibility (share contact info only 1 hour before trip)
   - Location sharing during trip only

6. **Notification System**
   - Alert driver when new passenger books
   - Notify passengers when trip details change
   - Reminder notifications with passenger list 24h before trip

---

## Notes

### Architecture Decisions

**Why Application Service Layer?**
- Permission logic (`can_view_passengers`) is application-level, not domain-level
- Aggregating driver + passengers requires orchestrating multiple repositories
- Privacy filtering combines domain logic (`User.get_public_profile`) with application context

**Why Domain Method for Privacy?**
- `User.get_public_profile()` encapsulates privacy rules in domain model
- Keeps privacy logic DRY (reusable across application services)
- Domain model owns its data visibility rules

**Why No New Repositories?**
- Existing repositories provide all needed queries
- Filtering confirmed bookings can be done in service layer
- Avoids repository bloat with feature-specific methods

### Implementation Tips

1. **Start with Migration**: Database schema changes first, verify with `.schema users`
2. **Test Domain Method**: Unit test `User.get_public_profile()` before building service
3. **Mock Repositories**: Use mock repositories in service tests for fast feedback
4. **Test Privacy Extensively**: Create matrix of privacy combinations and verify each
5. **Use Fixtures**: Parameterized fixtures reduce test boilerplate significantly

### Common Pitfalls

❌ **N+1 Query Problem**: Don't fetch users one-by-one in loop
✅ **Solution**: Bulk fetch with `UserTable.id.in_(user_ids)`

❌ **Leaking Private Data**: Forgetting to check privacy flags
✅ **Solution**: Always use `User.get_public_profile()`, never access fields directly

❌ **Permission Bypass**: Checking driver only, forgetting confirmed passengers
✅ **Solution**: `can_view_passengers()` checks BOTH conditions

❌ **Including Inactive Bookings**: Showing cancelled passengers
✅ **Solution**: Filter `status="confirmed" AND is_active=True`

---

**Plan Status**: READY FOR IMPLEMENTATION
**Estimated Implementation Time**: 2-3 hours (as per requirements)
**Blocking Dependencies**: None (extends existing RF-003, RF-004)
**Next Steps**: Begin Phase 1 (Domain & Database changes)
