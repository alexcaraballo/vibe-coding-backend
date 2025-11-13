# FastAPI Implementation Plan: Initial Structure with SQLite3

**Status**: READY
**Version**: 1.0.0
**Last Updated**: 2025-11-13
**Related Docs**: `.claude/plans/00-initial-structure.md`

## Summary

This document provides a comprehensive FastAPI implementation plan for the carpooling system, adapted from the original MongoDB-based design to use SQLite3 with SQLAlchemy 2.0 async. The architecture maintains Clean Architecture (Hexagonal Architecture) principles with three distinct layers: Domain, Infrastructure, and API. The system is organized into four primary modules: users, trips, matching, and maps, each maintaining strict layer separation and dependency rules.

The implementation leverages SQLAlchemy's async capabilities with aiosqlite for non-blocking database operations, Alembic for schema migrations, and FastAPI's dependency injection system for managing database sessions and cross-cutting concerns. All domain logic remains pure Python, free from framework dependencies, while infrastructure adapters handle SQLAlchemy ORM mappings and persistence concerns.

## Architecture Mapping

### Domain → FastAPI Mapping

| Domain Concept | FastAPI Construct | Location | Notes |
|---------------|------------------|----------|-------|
| User Aggregate | SQLAlchemy Model + Repository | `apps/users/infrastructure/models.py` | User, Driver, Passenger entities |
| Trip Aggregate | SQLAlchemy Model + Repository | `apps/trips/infrastructure/models.py` | Trip, Booking, TravelRequest entities |
| Repository Interface | Abstract Base Class | `apps/*/domain/repositories/*.py` | Pure Python ABC, no ORM |
| Repository Implementation | SQLAlchemy Repository | `apps/*/infrastructure/repositories/*.py` | Implements domain interface |
| Domain Service | Pure Python Service | `apps/*/domain/services/*.py` | Business logic, no infrastructure |
| Infrastructure Service | Service with External Dependencies | `apps/*/infrastructure/services/*.py` | Maps API, Geocoding, etc. |
| Request DTO | Pydantic Model | `apps/*/api/versioning/v1/schemas/requests.py` | API input validation |
| Response DTO | Pydantic Model | `apps/*/api/versioning/v1/schemas/responses.py` | API output serialization |
| API Endpoint | FastAPI Router | `apps/*/api/versioning/v1/views.py` | HTTP handlers |
| Database Session | FastAPI Dependency | `config/database.py` | Async session factory |

### Layer Responsibilities

**Domain Layer** (`apps/*/domain/`):
- Define pure business entities and value objects (Python dataclasses or simple classes)
- Specify repository interfaces (ABCs) without implementation details
- Implement business rules and domain services
- Raise domain-specific exceptions
- **Zero dependencies on FastAPI, SQLAlchemy, or any framework**

**Infrastructure Layer** (`apps/*/infrastructure/`):
- Implement repository interfaces using SQLAlchemy async sessions
- Define SQLAlchemy declarative models (ORM mappings)
- Integrate with external services (maps APIs, geocoding)
- Handle database transactions and session management
- Map between domain entities and SQLAlchemy models

**API Layer** (`apps/*/api/`):
- Define FastAPI routers and endpoint handlers
- Specify Pydantic request/response schemas
- Handle HTTP-specific concerns (status codes, headers)
- Inject dependencies (database sessions, repositories, services)
- Map between HTTP DTOs and domain entities
- Handle API-level error responses

### Clean Architecture Dependency Rules

```
API Layer (entrypoints/http)
    ↓ depends on
Infrastructure Layer (adapters)
    ↓ depends on
Domain Layer (core business logic)
```

**Critical Rules:**
- Domain NEVER imports from Infrastructure or API
- Infrastructure MAY import from Domain (implements interfaces)
- API MAY import from Infrastructure and Domain
- All cross-layer communication through interfaces

## Project Structure

```
vibe-coding-backend/
├── apps/
│   ├── users/                          # User Management Module
│   │   ├── __init__.py
│   │   ├── domain/
│   │   │   ├── __init__.py
│   │   │   ├── entities.py            # User, Driver, Passenger (pure Python)
│   │   │   ├── value_objects.py       # Email, PhoneNumber, etc.
│   │   │   └── repositories/
│   │   │       ├── __init__.py
│   │   │       └── user_repository.py # Abstract repository interface
│   │   ├── infrastructure/
│   │   │   ├── __init__.py
│   │   │   ├── models.py              # SQLAlchemy ORM models
│   │   │   ├── dependencies.py        # FastAPI dependencies for this module
│   │   │   └── repositories/
│   │   │       ├── __init__.py
│   │   │       └── user_repository.py # SQLAlchemy implementation
│   │   └── api/
│   │       ├── __init__.py
│   │       ├── urls.py                # Router registration
│   │       └── versioning/
│   │           └── v1/
│   │               ├── __init__.py
│   │               ├── views.py       # FastAPI endpoint handlers
│   │               └── schemas/
│   │                   ├── __init__.py
│   │                   ├── requests.py  # Pydantic request models
│   │                   └── responses.py # Pydantic response models
│   │
│   ├── trips/                          # Trip Management Module
│   │   ├── __init__.py
│   │   ├── domain/
│   │   │   ├── __init__.py
│   │   │   ├── entities.py            # Trip, Booking, TravelRequest
│   │   │   ├── value_objects.py       # TripStatus, BookingStatus, etc.
│   │   │   └── repositories/
│   │   │       ├── __init__.py
│   │   │       ├── trip_repository.py
│   │   │       ├── booking_repository.py
│   │   │       └── travel_request_repository.py
│   │   ├── infrastructure/
│   │   │   ├── __init__.py
│   │   │   ├── models.py              # SQLAlchemy models for Trip, Booking, etc.
│   │   │   ├── dependencies.py
│   │   │   └── repositories/
│   │   │       ├── __init__.py
│   │   │       ├── trip_repository.py
│   │   │       ├── booking_repository.py
│   │   │       └── travel_request_repository.py
│   │   └── api/
│   │       ├── __init__.py
│   │       ├── urls.py
│   │       └── versioning/
│   │           └── v1/
│   │               ├── __init__.py
│   │               ├── views.py
│   │               └── schemas/
│   │                   ├── __init__.py
│   │                   ├── requests.py
│   │                   └── responses.py
│   │
│   ├── matching/                       # Matching Engine Module
│   │   ├── __init__.py
│   │   ├── domain/
│   │   │   ├── __init__.py
│   │   │   ├── entities.py            # MatchResult, MatchScore
│   │   │   └── services/
│   │   │       ├── __init__.py
│   │   │       └── matching_service.py # Abstract matching interface
│   │   ├── infrastructure/
│   │   │   ├── __init__.py
│   │   │   ├── dependencies.py
│   │   │   └── services/
│   │   │       ├── __init__.py
│   │   │       ├── matching_service.py    # Concrete implementation
│   │   │       └── geocoding_service.py   # External API integration
│   │   └── api/
│   │       ├── __init__.py
│   │       ├── urls.py
│   │       └── versioning/
│   │           └── v1/
│   │               ├── __init__.py
│   │               ├── views.py
│   │               └── schemas/
│   │                   ├── __init__.py
│   │                   ├── requests.py
│   │                   └── responses.py
│   │
│   └── maps/                           # Maps Integration Module
│       ├── __init__.py
│       ├── domain/
│       │   ├── __init__.py
│       │   ├── entities.py            # Route, Coordinates
│       │   └── services/
│       │       ├── __init__.py
│       │       └── map_service.py     # Abstract map service
│       ├── infrastructure/
│       │   ├── __init__.py
│       │   ├── dependencies.py
│       │   └── services/
│       │       ├── __init__.py
│       │       └── map_service.py     # OpenStreetMap/Mapbox impl
│       └── api/
│           ├── __init__.py
│           ├── urls.py
│           └── versioning/
│               └── v1/
│                   ├── __init__.py
│                   ├── views.py
│                   └── schemas/
│                       ├── __init__.py
│                       ├── requests.py
│                       └── responses.py
│
├── config/
│   ├── __init__.py
│   ├── settings.py                    # Pydantic Settings for env vars
│   └── database.py                    # SQLAlchemy async engine & session factory
│
├── shared/                            # Cross-cutting concerns
│   ├── __init__.py
│   ├── exceptions.py                  # Domain exceptions
│   ├── validators.py                  # Common validators
│   └── utils.py                       # Utility functions
│
├── migrations/                        # Alembic migrations
│   ├── versions/                      # Migration version files
│   ├── env.py                        # Alembic environment config
│   ├── script.py.mako                # Migration template
│   └── alembic.ini                   # Alembic configuration
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                   # Pytest fixtures (in-memory SQLite)
│   ├── test_users/
│   │   ├── __init__.py
│   │   ├── test_domain/              # Domain logic tests
│   │   ├── test_repositories/        # Repository tests
│   │   └── test_api/                 # API integration tests
│   ├── test_trips/
│   ├── test_matching/
│   └── test_maps/
│
├── main.py                           # FastAPI application entry point
├── alembic.ini                       # Alembic configuration (root level)
├── pyproject.toml                    # Poetry dependencies
├── .env.example                      # Environment variables template
├── .env                             # Local environment (not in git)
├── README.md
└── .gitignore
```

## File Actions

### Create New Files

#### Core Configuration

**`config/database.py`** - SQLAlchemy async engine and session management
```python
# Purpose: Configure SQLAlchemy async engine, session factory, and Base class
# Key components:
# - async_engine: AsyncEngine with aiosqlite
# - async_session_maker: AsyncSession factory
# - Base: declarative_base for ORM models
# - get_async_session(): FastAPI dependency yielding sessions
# - init_db(): Create all tables (for development)
```

**`config/settings.py`** - Pydantic Settings for environment configuration
```python
# Purpose: Centralized configuration using pydantic-settings
# Key settings:
# - DATABASE_URL: SQLite connection string
# - SECRET_KEY, ALGORITHM: JWT authentication
# - MAPS_API_KEY, GEOCODING_API_KEY: External services
# - DEFAULT_MAX_DETOUR_MINUTES, DEFAULT_PROXIMITY_RADIUS_KM: Matching params
# - CORS_ORIGINS: CORS configuration
```

**`alembic.ini`** - Alembic migration configuration
```ini
# Purpose: Configure Alembic for database migrations
# Key settings:
# - sqlalchemy.url: Read from env or config
# - script_location: migrations/
# - file_template: %%(year)d_%%(month).2d_%%(day).2d_%%(hour).2d%%(minute).2d-%%(rev)s_%%(slug)s
```

**`migrations/env.py`** - Alembic environment setup
```python
# Purpose: Configure Alembic to work with async SQLAlchemy
# Key components:
# - Import all SQLAlchemy models for auto-generation
# - Configure async engine for migrations
# - Set target_metadata = Base.metadata
```

#### Domain Layer (Example: Users Module)

**`apps/users/domain/entities.py`** - Pure domain entities
```python
# Purpose: Define User, Driver, Passenger as pure Python classes
# No SQLAlchemy, no framework dependencies
# Use dataclasses or simple classes with business logic
```

**`apps/users/domain/value_objects.py`** - Value objects
```python
# Purpose: Immutable value objects like Email, PhoneNumber
# Enforce validation rules at construction
```

**`apps/users/domain/repositories/user_repository.py`** - Abstract repository
```python
# Purpose: Define repository interface (ABC)
# Methods: create(), get_by_id(), update(), delete(), find_by_email()
# Returns domain entities, not ORM models
```

#### Infrastructure Layer (Example: Users Module)

**`apps/users/infrastructure/models.py`** - SQLAlchemy ORM models
```python
# Purpose: Map domain entities to database tables
# Define User, Driver, Passenger tables
# Use SQLAlchemy 2.0 declarative syntax
# Relationships, indexes, constraints
```

**`apps/users/infrastructure/repositories/user_repository.py`** - Repository implementation
```python
# Purpose: Implement UserRepository interface using SQLAlchemy
# Constructor receives AsyncSession
# Methods use SQLAlchemy async queries (select(), execute())
# Map ORM models to domain entities and vice versa
```

**`apps/users/infrastructure/dependencies.py`** - Module-specific dependencies
```python
# Purpose: FastAPI dependencies for users module
# Example: get_user_repository(session: AsyncSession)
# Example: get_current_user(token: str)
```

#### API Layer (Example: Users Module)

**`apps/users/api/versioning/v1/schemas/requests.py`** - Pydantic request models
```python
# Purpose: Define API request schemas
# CreateUserRequest, UpdateUserRequest, LoginRequest
# Validation rules, field constraints
```

**`apps/users/api/versioning/v1/schemas/responses.py`** - Pydantic response models
```python
# Purpose: Define API response schemas
# UserResponse, TokenResponse, ErrorResponse
# from_entity() methods to convert domain entities
```

**`apps/users/api/versioning/v1/views.py`** - FastAPI endpoint handlers
```python
# Purpose: Define HTTP endpoints (routers)
# POST /users, GET /users/{id}, PUT /users/{id}, DELETE /users/{id}
# Inject dependencies (session, repositories)
# Call domain/infrastructure services
# Return Pydantic response models
```

**`apps/users/api/urls.py`** - Router registration
```python
# Purpose: Create APIRouter and include versioned routers
# router = APIRouter()
# router.include_router(v1_router, prefix="/v1")
```

#### Main Application

**`main.py`** - FastAPI application setup
```python
# Purpose: Create FastAPI app, configure middleware, register routers
# Lifespan events: init_db() on startup, close connections on shutdown
# Include routers from all modules
# CORS, exception handlers, health check endpoint
```

#### Testing Infrastructure

**`tests/conftest.py`** - Pytest fixtures
```python
# Purpose: Shared test fixtures
# async_client: httpx.AsyncClient for API tests
# async_session: In-memory SQLite AsyncSession
# test_db: Setup/teardown test database
```

### Modify Existing Files

**`pyproject.toml`** - Add SQLAlchemy dependencies, remove MongoDB
```toml
# Remove: motor, pymongo
# Add: sqlalchemy[asyncio], aiosqlite, alembic
# Add: pytest-asyncio for async test support
```

**`.gitignore`** - Add SQLite database files
```
# Add:
*.db
*.sqlite
*.sqlite3
```

## Dependencies

### Required Packages

```toml
[tool.poetry]
name = "vibe-coding-backend"
version = "0.1.0"
description = "Sistema de Carpooling - MVP Hackathon (SQLite3)"
authors = ["Team <team@example.com>"]
python = "^3.11"

[tool.poetry.dependencies]
# Core Framework
fastapi = "^0.109.0"
uvicorn = {extras = ["standard"], version = "^0.27.0"}
pydantic = "^2.5.0"
pydantic-settings = "^2.1.0"

# Database (SQLite3 + SQLAlchemy)
sqlalchemy = {extras = ["asyncio"], version = "^2.0.25"}
aiosqlite = "^0.19.0"
alembic = "^1.13.1"

# Authentication & Security
python-jose = {extras = ["cryptography"], version = "^3.3.0"}
passlib = {extras = ["bcrypt"], version = "^1.7.4"}

# HTTP & Forms
python-multipart = "^0.0.6"
httpx = "^0.26.0"

# Environment
python-dotenv = "^1.0.0"

[tool.poetry.group.dev.dependencies]
# Testing
pytest = "^7.4.3"
pytest-asyncio = "^0.21.1"
pytest-cov = "^4.1.0"

# Code Quality
ruff = "^0.1.9"
mypy = "^1.8.0"
black = "^23.12.1"

[tool.poetry.group.test.dependencies]
# Test-specific dependencies
faker = "^22.0.0"  # For generating test data

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

### Dependency Rationale

**SQLAlchemy 2.0 with asyncio extra:**
- Provides async ORM capabilities
- Modern 2.0 query syntax (select(), execute())
- Type hints and better IDE support

**aiosqlite:**
- Async SQLite driver required by SQLAlchemy async engine
- Non-blocking database operations
- Compatible with asyncio event loop

**alembic:**
- Industry-standard database migration tool
- Supports auto-generation from SQLAlchemy models
- Version control for database schema

**python-jose & passlib:**
- JWT token generation and validation
- Password hashing with bcrypt
- Required for authentication

**pytest-asyncio:**
- Enables async test functions
- Essential for testing async FastAPI endpoints

### Dependency Injection Hierarchy

```
FastAPI Request
    ↓
[Middleware Layer]
    ↓
get_async_session() → AsyncSession
    ↓
get_user_repository(session) → UserRepository
    ↓
get_current_user(token, repo) → User
    ↓
[Endpoint Handler]
```

**Key Dependencies:**

1. **Database Session** (`config/database.py`)
   - `get_async_session()`: Yields AsyncSession, handles commit/rollback
   - Used by all repository dependencies

2. **Repository Dependencies** (per module, e.g., `apps/users/infrastructure/dependencies.py`)
   - `get_user_repository(session: AsyncSession)`: Returns UserRepository instance
   - Injects session, returns configured repository

3. **Authentication Dependencies** (e.g., `apps/users/infrastructure/dependencies.py`)
   - `get_current_user(token: str, repo: UserRepository)`: Validates JWT, returns User
   - Used to protect endpoints requiring authentication

4. **Service Dependencies** (e.g., `apps/matching/infrastructure/dependencies.py`)
   - `get_matching_service(...)`: Returns configured matching service
   - May depend on multiple repositories and external services

## Data Persistence

### Repository Interfaces (Domain Layer)

Example: `apps/users/domain/repositories/user_repository.py`

```python
from abc import ABC, abstractmethod
from typing import Optional
from apps.users.domain.entities import User

class UserRepository(ABC):
    """Abstract repository for User aggregate"""

    @abstractmethod
    async def create(self, user: User) -> User:
        """Persist a new user"""
        pass

    @abstractmethod
    async def get_by_id(self, user_id: str) -> Optional[User]:
        """Retrieve user by ID"""
        pass

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        """Retrieve user by email"""
        pass

    @abstractmethod
    async def update(self, user: User) -> User:
        """Update existing user"""
        pass

    @abstractmethod
    async def delete(self, user_id: str) -> bool:
        """Delete user by ID"""
        pass

    @abstractmethod
    async def list_all(self, skip: int = 0, limit: int = 100) -> list[User]:
        """List all users with pagination"""
        pass
```

### SQLAlchemy Models (Infrastructure Layer)

Example: `apps/users/infrastructure/models.py`

```python
from sqlalchemy import String, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from config.database import Base

class UserModel(Base):
    """SQLAlchemy model for User entity"""
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    trips_as_driver = relationship("TripModel", back_populates="driver", foreign_keys="TripModel.driver_id")
    bookings_as_passenger = relationship("BookingModel", back_populates="passenger")

class DriverModel(Base):
    """SQLAlchemy model for Driver profile"""
    __tablename__ = "drivers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), unique=True)
    vehicle_make: Mapped[str] = mapped_column(String(100))
    vehicle_model: Mapped[str] = mapped_column(String(100))
    vehicle_plate: Mapped[str] = mapped_column(String(20), unique=True)
    vehicle_color: Mapped[str] = mapped_column(String(50), nullable=True)
    total_seats: Mapped[int] = mapped_column(Integer, default=4)
    rating: Mapped[float] = mapped_column(Float, default=0.0)
    total_trips: Mapped[int] = mapped_column(Integer, default=0)

    # Relationship
    user = relationship("UserModel", backref="driver_profile")
```

**Key SQLAlchemy 2.0 Patterns:**
- Use `Mapped[type]` for type hints
- Use `mapped_column()` instead of `Column()`
- Specify `ForeignKey()` in `mapped_column()`
- Use `relationship()` for associations

### Repository Implementation (Infrastructure Layer)

Example: `apps/users/infrastructure/repositories/user_repository.py`

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from apps.users.domain.repositories.user_repository import UserRepository
from apps.users.domain.entities import User
from apps.users.infrastructure.models import UserModel

class SQLAlchemyUserRepository(UserRepository):
    """SQLAlchemy implementation of UserRepository"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user: User) -> User:
        """Create new user"""
        user_model = self._to_model(user)
        self.session.add(user_model)
        await self.session.flush()  # Get generated IDs
        return self._to_entity(user_model)

    async def get_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        stmt = select(UserModel).where(UserModel.id == user_id)
        result = await self.session.execute(stmt)
        user_model = result.scalar_one_or_none()
        return self._to_entity(user_model) if user_model else None

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        stmt = select(UserModel).where(UserModel.email == email)
        result = await self.session.execute(stmt)
        user_model = result.scalar_one_or_none()
        return self._to_entity(user_model) if user_model else None

    async def update(self, user: User) -> User:
        """Update existing user"""
        stmt = select(UserModel).where(UserModel.id == user.id)
        result = await self.session.execute(stmt)
        user_model = result.scalar_one_or_none()
        if not user_model:
            raise EntityNotFound("User", user.id)

        # Update fields
        user_model.email = user.email
        user_model.full_name = user.full_name
        user_model.phone = user.phone
        # ... other fields

        await self.session.flush()
        return self._to_entity(user_model)

    async def delete(self, user_id: str) -> bool:
        """Delete user"""
        stmt = select(UserModel).where(UserModel.id == user_id)
        result = await self.session.execute(stmt)
        user_model = result.scalar_one_or_none()
        if user_model:
            await self.session.delete(user_model)
            return True
        return False

    async def list_all(self, skip: int = 0, limit: int = 100) -> list[User]:
        """List users with pagination"""
        stmt = select(UserModel).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        user_models = result.scalars().all()
        return [self._to_entity(model) for model in user_models]

    def _to_entity(self, model: UserModel) -> User:
        """Convert ORM model to domain entity"""
        return User(
            id=model.id,
            email=model.email,
            full_name=model.full_name,
            phone=model.phone,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at
        )

    def _to_model(self, entity: User) -> UserModel:
        """Convert domain entity to ORM model"""
        return UserModel(
            id=entity.id,
            email=entity.email,
            hashed_password=entity.hashed_password,
            full_name=entity.full_name,
            phone=entity.phone,
            is_active=entity.is_active
        )
```

**Key Patterns:**
- Constructor receives `AsyncSession`
- Use `select()` for queries (SQLAlchemy 2.0 style)
- Use `await session.execute(stmt)` for async queries
- Use `scalar_one_or_none()`, `scalars().all()` for results
- Separate `_to_entity()` and `_to_model()` mappers
- Domain entities never exposed to API layer directly

### Migration Strategy with Alembic

#### Initial Setup

**Step 1: Initialize Alembic**
```bash
alembic init migrations
```

**Step 2: Configure `alembic.ini`**
```ini
[alembic]
script_location = migrations
file_template = %%(year)d_%%(month).2d_%%(day).2d_%%(hour).2d%%(minute).2d-%%(rev)s_%%(slug)s

# SQLite URL (can be overridden in env.py)
sqlalchemy.url = sqlite+aiosqlite:///./carpooling.db
```

**Step 3: Configure `migrations/env.py`**
```python
import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context
from config.database import Base
from config.settings import settings

# Import all models for auto-detection
from apps.users.infrastructure.models import UserModel, DriverModel
from apps.trips.infrastructure.models import TripModel, BookingModel, TravelRequestModel

config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

#### Creating Migrations

**Auto-generate migration from models:**
```bash
alembic revision --autogenerate -m "create initial tables"
```

**Review generated migration** in `migrations/versions/YYYY_MM_DD_HHMM-<rev>_create_initial_tables.py`

**Apply migrations:**
```bash
alembic upgrade head
```

**Rollback migrations:**
```bash
alembic downgrade -1  # Rollback one version
alembic downgrade base  # Rollback all
```

#### Migration Best Practices

1. **Always review auto-generated migrations** before applying
2. **Test migrations in development** before production
3. **Create separate migrations** for structure changes vs data migrations
4. **Use meaningful migration messages**: `alembic revision -m "add user preferences table"`
5. **Keep migrations small and focused**: One logical change per migration
6. **Never edit applied migrations**: Create new migrations for fixes

### Database Configuration

**`config/database.py`** - Complete implementation:

```python
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from typing import AsyncGenerator
from config.settings import settings

# Create async engine
async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,  # Log SQL queries in debug mode
    future=True,
    pool_pre_ping=True,  # Verify connections before using
)

# Create async session factory
async_session_maker = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Prevent lazy loading issues
    autocommit=False,
    autoflush=False,
)

# Base class for declarative models
Base = declarative_base()

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides an async database session.
    Handles commit/rollback and ensures session is closed.
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def init_db() -> None:
    """
    Initialize database by creating all tables.
    Use only in development - in production use Alembic migrations.
    """
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def close_db() -> None:
    """Close database connections"""
    await async_engine.dispose()
```

**`config/settings.py`** - Updated for SQLite:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    """Application configuration"""

    # App
    APP_NAME: str = "Vibe Coding Carpooling API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # Database (SQLite)
    DATABASE_URL: str = "sqlite+aiosqlite:///./carpooling.db"
    # For testing: "sqlite+aiosqlite:///:memory:"

    # Auth
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # External Services
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

settings = Settings()
```

## API Endpoints

### Users Module

| Method | Path | Request Model | Response Model | Use Case | Auth |
|--------|------|--------------|----------------|----------|------|
| POST | /api/v1/users | CreateUserRequest | UserResponse | Register new user | No |
| POST | /api/v1/users/login | LoginRequest | TokenResponse | User authentication | No |
| GET | /api/v1/users/me | - | UserResponse | Get current user | Yes |
| GET | /api/v1/users/{id} | - | UserResponse | Get user by ID | Yes |
| PUT | /api/v1/users/{id} | UpdateUserRequest | UserResponse | Update user | Yes (owner) |
| DELETE | /api/v1/users/{id} | - | MessageResponse | Delete user | Yes (owner) |
| POST | /api/v1/drivers | CreateDriverRequest | DriverResponse | Register driver profile | Yes |
| GET | /api/v1/drivers/{id} | - | DriverResponse | Get driver profile | Yes |

### Trips Module

| Method | Path | Request Model | Response Model | Use Case | Auth |
|--------|------|--------------|----------------|----------|------|
| POST | /api/v1/trips | CreateTripRequest | TripResponse | Publish new trip | Yes (driver) |
| GET | /api/v1/trips | TripSearchQuery | List[TripResponse] | Search available trips | No |
| GET | /api/v1/trips/{id} | - | TripResponse | Get trip details | No |
| PUT | /api/v1/trips/{id} | UpdateTripRequest | TripResponse | Update trip | Yes (owner) |
| DELETE | /api/v1/trips/{id} | - | MessageResponse | Cancel trip | Yes (owner) |
| POST | /api/v1/bookings | CreateBookingRequest | BookingResponse | Book a seat | Yes (passenger) |
| GET | /api/v1/bookings | - | List[BookingResponse] | List user bookings | Yes |
| DELETE | /api/v1/bookings/{id} | - | MessageResponse | Cancel booking | Yes (owner) |
| POST | /api/v1/travel-requests | CreateTravelRequestRequest | TravelRequestResponse | Create travel request | Yes (passenger) |

### Matching Module

| Method | Path | Request Model | Response Model | Use Case | Auth |
|--------|------|--------------|----------------|----------|------|
| POST | /api/v1/matching/find-trips | MatchingRequest | List[MatchResultResponse] | Find compatible trips | Yes |
| POST | /api/v1/matching/find-passengers | MatchingRequest | List[MatchResultResponse] | Find compatible passengers | Yes (driver) |
| GET | /api/v1/matching/score/{trip_id}/{request_id} | - | MatchScoreResponse | Calculate match score | Yes |

### Maps Module

| Method | Path | Request Model | Response Model | Use Case | Auth |
|--------|------|--------------|----------------|----------|------|
| GET | /api/v1/maps/route | RouteRequest | RouteResponse | Calculate route | No |
| POST | /api/v1/maps/geocode | GeocodeRequest | CoordinatesResponse | Convert address to coords | No |
| POST | /api/v1/maps/reverse-geocode | ReverseGeocodeRequest | AddressResponse | Convert coords to address | No |

## Main Application Setup

**`main.py`** - Complete FastAPI application:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from config.settings import settings
from config.database import init_db, close_db

# Import routers (uncomment as implemented)
# from apps.users.api.urls import router as users_router
# from apps.trips.api.urls import router as trips_router
# from apps.matching.api.urls import router as matching_router
# from apps.maps.api.urls import router as maps_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle events"""
    # Startup
    print(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    if settings.DEBUG:
        print("⚠️ Running in DEBUG mode")
        await init_db()  # Auto-create tables in development
    print("✅ Database initialized")

    yield

    # Shutdown
    print("👋 Shutting down application...")
    await close_db()
    print("✅ Database connections closed")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "database": "sqlite"
    }

# Include routers (uncomment as modules are implemented)
# app.include_router(users_router, prefix="/api/v1", tags=["Users"])
# app.include_router(trips_router, prefix="/api/v1", tags=["Trips"])
# app.include_router(matching_router, prefix="/api/v1", tags=["Matching"])
# app.include_router(maps_router, prefix="/api/v1", tags=["Maps"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )
```

## Error Handling

### Domain Error Mapping

| Domain Error | HTTP Status | Response Format |
|--------------|-------------|----------------|
| `EntityNotFound` | 404 Not Found | `{"detail": "User with id '123' not found", "code": "ENTITY_NOT_FOUND"}` |
| `ValidationError` | 400 Bad Request | `{"detail": "Invalid email format", "code": "VALIDATION_ERROR"}` |
| `InsufficientSeats` | 409 Conflict | `{"detail": "No hay plazas disponibles", "code": "INSUFFICIENT_SEATS"}` |
| `MaxDetourExceeded` | 400 Bad Request | `{"detail": "Desvío excedido: 45 > 30 minutos", "code": "MAX_DETOUR_EXCEEDED"}` |
| `Unauthorized` | 401 Unauthorized | `{"detail": "Invalid credentials", "code": "UNAUTHORIZED"}` |
| `Forbidden` | 403 Forbidden | `{"detail": "Insufficient permissions", "code": "FORBIDDEN"}` |

### Exception Handlers

Add to `main.py`:

```python
from fastapi import Request, status
from fastapi.responses import JSONResponse
from shared.exceptions import DomainException, EntityNotFound, ValidationError

@app.exception_handler(EntityNotFound)
async def entity_not_found_handler(request: Request, exc: EntityNotFound):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": exc.message, "code": exc.code}
    )

@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": exc.message, "code": exc.code}
    )

@app.exception_handler(DomainException)
async def domain_exception_handler(request: Request, exc: DomainException):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": exc.message, "code": exc.code}
    )
```

## Testing Strategy

### Integration Tests

**Test Scenarios:**

1. **User Management:**
   - Create user → Verify in database
   - Login → Receive valid JWT token
   - Update user → Verify changes persisted
   - Delete user → Verify cascade deletion

2. **Trip Management:**
   - Create trip → Verify available seats
   - Search trips → Filter by origin/destination
   - Book trip → Decrease available seats
   - Cancel booking → Restore available seats

3. **Matching Engine:**
   - Find compatible trips → Verify score calculation
   - Filter by proximity → Verify distance calculations
   - Filter by detour → Verify route compatibility

4. **End-to-End Flows:**
   - Complete booking flow: Register → Create trip → Search → Book → Confirm
   - Matching flow: Create request → Find matches → Book best match

### Contract Tests

**Purpose:** Validate API responses match Pydantic schemas

**Approach:**
- For each endpoint, test request/response schema compliance
- Verify required fields are present
- Verify data types match schema definitions
- Test validation error responses

### Test Fixtures

**`tests/conftest.py`** - Complete test configuration:

```python
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
    """Sample user data for tests"""
    return {
        "email": "test@example.com",
        "password": "SecurePassword123!",
        "full_name": "Test User",
        "phone": "+34612345678"
    }

@pytest.fixture
def sample_trip_data():
    """Sample trip data for tests"""
    return {
        "origin": {"lat": 40.4168, "lng": -3.7038},  # Madrid
        "destination": {"lat": 41.3851, "lng": 2.1734},  # Barcelona
        "departure_datetime": "2025-11-20T10:00:00",
        "available_seats": 3,
        "price_per_seat": 25.0,
        "preferences": {
            "smoking_allowed": False,
            "pets_allowed": False,
            "music_preferences": "No preference"
        }
    }
```

### Example Test: User Registration

**`tests/test_users/test_api/test_registration.py`**:

```python
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.mark.asyncio
async def test_register_user_success(async_client: AsyncClient, sample_user_data):
    """Test successful user registration"""
    response = await async_client.post("/api/v1/users", json=sample_user_data)

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == sample_user_data["email"]
    assert data["full_name"] == sample_user_data["full_name"]
    assert "id" in data
    assert "password" not in data  # Password should not be returned

@pytest.mark.asyncio
async def test_register_user_duplicate_email(async_client: AsyncClient, sample_user_data):
    """Test registration fails with duplicate email"""
    # First registration
    await async_client.post("/api/v1/users", json=sample_user_data)

    # Second registration with same email
    response = await async_client.post("/api/v1/users", json=sample_user_data)

    assert response.status_code == 400
    assert "already exists" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_register_user_invalid_email(async_client: AsyncClient, sample_user_data):
    """Test registration fails with invalid email"""
    sample_user_data["email"] = "invalid-email"
    response = await async_client.post("/api/v1/users", json=sample_user_data)

    assert response.status_code == 422  # Pydantic validation error
```

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=apps --cov-report=html

# Run specific module
poetry run pytest tests/test_users/

# Run with verbose output
poetry run pytest -v

# Run specific test
poetry run pytest tests/test_users/test_api/test_registration.py::test_register_user_success
```

## Observability

### Logging

**Structured Logging Setup:**

Create `shared/logging_config.py`:

```python
import logging
import sys
from config.settings import settings

def setup_logging():
    """Configure structured logging"""
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO

    logging.basicConfig(
        level=log_level,
        format='{"time": "%(asctime)s", "level": "%(levelname)s", "module": "%(name)s", "message": "%(message)s"}',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Silence noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

logger = logging.getLogger("carpooling")
```

**Usage in modules:**

```python
from shared.logging_config import logger

logger.info("User created", extra={"user_id": user.id, "email": user.email})
logger.error("Failed to create booking", extra={"trip_id": trip_id, "error": str(e)})
```

### Metrics

**Prometheus Integration (Optional):**

Add to `pyproject.toml`:
```toml
prometheus-fastapi-instrumentator = "^6.1.0"
```

Add to `main.py`:
```python
from prometheus_fastapi_instrumentator import Instrumentator

instrumentator = Instrumentator()
instrumentator.instrument(app).expose(app)
```

Access metrics at `/metrics`

### Tracing

**OpenTelemetry Integration (Optional):**

For distributed tracing, add:
```toml
opentelemetry-api = "^1.21.0"
opentelemetry-sdk = "^1.21.0"
opentelemetry-instrumentation-fastapi = "^0.42b0"
opentelemetry-instrumentation-sqlalchemy = "^0.42b0"
```

## Environment Configuration

**`.env.example`**:

```bash
# Application
APP_NAME="Vibe Coding Carpooling API"
APP_VERSION="0.1.0"
DEBUG=true

# Database
DATABASE_URL=sqlite+aiosqlite:///./carpooling.db
# For in-memory: sqlite+aiosqlite:///:memory:
# For specific path: sqlite+aiosqlite:///./data/carpooling.db

# Auth
SECRET_KEY=your-secret-key-change-this-in-production-use-openssl-rand-hex-32
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# External Services (opcional para MVP)
MAPS_API_KEY=
MAPS_PROVIDER=openstreetmap
GEOCODING_API_KEY=

# Matching Engine
DEFAULT_MAX_DETOUR_MINUTES=30
DEFAULT_PROXIMITY_RADIUS_KM=10.0

# CORS
CORS_ORIGINS=["http://localhost:3000","http://localhost:8000"]
```

## Open Questions

1. **User Authentication Strategy:**
   - Should we implement OAuth2 (Google, Facebook) in addition to email/password?
   - Do we need email verification for new users?
   - Should we implement refresh tokens or just access tokens?

2. **Trip Availability Management:**
   - How should we handle concurrent booking attempts for the last available seat?
   - Should we implement optimistic locking or pessimistic locking?
   - Do we need a reservation timeout (e.g., seat held for 5 minutes)?

3. **Matching Algorithm Complexity:**
   - What is the maximum acceptable response time for matching calculations?
   - Should matching be synchronous or background task?
   - Do we need to cache matching results?

4. **External Services:**
   - Which map provider should we prioritize (OpenStreetMap, Mapbox, Google)?
   - Do we need API key for production?
   - Should we implement fallback providers?

5. **Data Retention:**
   - How long should we keep completed trip data?
   - Should we soft-delete or hard-delete cancelled trips/bookings?
   - Do we need audit logs for sensitive operations?

6. **SQLite Limitations:**
   - SQLite is excellent for MVP but has limitations (no concurrent writes, single file)
   - Should we plan for PostgreSQL migration path in production?
   - Do we need connection pooling strategy?

## Implementation Checklist

### Phase 1: Project Setup
- [ ] Initialize Poetry project with dependencies
- [ ] Create directory structure (apps, config, shared, tests, migrations)
- [ ] Set up `config/settings.py` with Pydantic Settings
- [ ] Set up `config/database.py` with SQLAlchemy async engine
- [ ] Create `.env` and `.env.example` files
- [ ] Update `.gitignore` for SQLite files
- [ ] Initialize Alembic for migrations
- [ ] Create `main.py` with FastAPI app skeleton
- [ ] Set up `tests/conftest.py` with in-memory SQLite

### Phase 2: Shared Components
- [ ] Implement `shared/exceptions.py` with domain exceptions
- [ ] Implement `shared/validators.py` with common validators
- [ ] Implement `shared/logging_config.py` for structured logging
- [ ] Add exception handlers to `main.py`

### Phase 3: Users Module
- [ ] Define domain entities (`apps/users/domain/entities.py`)
- [ ] Define repository interface (`apps/users/domain/repositories/user_repository.py`)
- [ ] Create SQLAlchemy models (`apps/users/infrastructure/models.py`)
- [ ] Implement repository (`apps/users/infrastructure/repositories/user_repository.py`)
- [ ] Create Pydantic schemas (requests/responses)
- [ ] Implement API endpoints (`apps/users/api/versioning/v1/views.py`)
- [ ] Set up dependencies (`apps/users/infrastructure/dependencies.py`)
- [ ] Create and apply Alembic migration
- [ ] Write integration tests
- [ ] Register router in `main.py`

### Phase 4: Trips Module
- [ ] Define domain entities (Trip, Booking, TravelRequest)
- [ ] Define repository interfaces
- [ ] Create SQLAlchemy models with relationships
- [ ] Implement repositories
- [ ] Create Pydantic schemas
- [ ] Implement API endpoints
- [ ] Set up dependencies
- [ ] Create and apply Alembic migration
- [ ] Write integration tests
- [ ] Register router in `main.py`

### Phase 5: Matching Module
- [ ] Define domain entities (MatchResult, MatchScore)
- [ ] Define matching service interface
- [ ] Implement matching algorithm
- [ ] Implement geocoding service
- [ ] Create Pydantic schemas
- [ ] Implement API endpoints
- [ ] Set up dependencies
- [ ] Write integration tests
- [ ] Register router in `main.py`

### Phase 6: Maps Module
- [ ] Define domain entities (Route, Coordinates)
- [ ] Define map service interface
- [ ] Implement OpenStreetMap integration
- [ ] Create Pydantic schemas
- [ ] Implement API endpoints
- [ ] Set up dependencies
- [ ] Write integration tests
- [ ] Register router in `main.py`

### Phase 7: Testing & Documentation
- [ ] Achieve 80%+ test coverage
- [ ] Write API documentation in docstrings
- [ ] Verify all endpoints in Swagger UI
- [ ] Create README.md with setup instructions
- [ ] Document environment variables
- [ ] Create sample requests for all endpoints

### Phase 8: Deployment Preparation
- [ ] Review all TODO comments
- [ ] Test with production-like data volume
- [ ] Verify all Alembic migrations
- [ ] Set up logging in production mode
- [ ] Configure CORS for production origins
- [ ] Generate secure SECRET_KEY
- [ ] Create deployment checklist

## Implementation Notes

### SQLite vs PostgreSQL

**SQLite Advantages (Good for MVP):**
- Zero configuration, no separate server
- Single file database, easy to backup
- Perfect for development and prototyping
- Sufficient for low-to-medium traffic

**SQLite Limitations:**
- No concurrent writes (writers block)
- Limited to single server (no horizontal scaling)
- Less powerful full-text search
- Weaker concurrency control

**Migration Path to PostgreSQL:**

Thanks to SQLAlchemy abstraction, migration is straightforward:

1. Install PostgreSQL driver: `asyncpg`
2. Update `DATABASE_URL` to PostgreSQL format
3. Adjust Alembic migrations if needed (most are portable)
4. Test thoroughly (especially concurrent operations)

No code changes required in repositories or domain logic.

### Async Best Practices

1. **Always use async repositories:**
   - All database operations should be async
   - Use `await` for all queries
   - Don't mix sync and async code

2. **Session management:**
   - Sessions are provided via FastAPI dependency injection
   - Never create sessions manually in endpoints
   - Sessions are automatically committed/rolled back

3. **Avoid blocking calls:**
   - Don't use `time.sleep()`, use `asyncio.sleep()`
   - Don't use sync HTTP libraries, use `httpx` async
   - Don't use sync file I/O in async handlers

### Security Considerations

1. **Password Hashing:**
   - Use `passlib` with bcrypt
   - Never store plain text passwords
   - Implement in user repository

2. **JWT Tokens:**
   - Use `python-jose` for token generation
   - Set reasonable expiration times
   - Validate tokens on protected endpoints

3. **SQL Injection:**
   - SQLAlchemy ORM provides protection
   - Never use raw SQL with user input
   - Use parameterized queries if raw SQL needed

4. **Input Validation:**
   - Pydantic provides automatic validation
   - Add custom validators for complex rules
   - Sanitize all user input

### Performance Optimization

1. **Database Indexes:**
   - Add indexes on foreign keys
   - Add indexes on frequently queried columns
   - Use `index=True` in SQLAlchemy models

2. **Query Optimization:**
   - Use `joinedload()` for eager loading relationships
   - Avoid N+1 queries
   - Use pagination for large result sets

3. **Caching:**
   - Consider Redis for frequently accessed data
   - Cache matching results temporarily
   - Cache geocoding results

---

**End of FastAPI Implementation Plan**

This plan provides a complete roadmap for implementing the carpooling system with FastAPI and SQLite3 while maintaining Clean Architecture principles. All domain logic remains pure and testable, infrastructure adapters handle SQLAlchemy concerns, and the API layer provides a clean HTTP interface.
