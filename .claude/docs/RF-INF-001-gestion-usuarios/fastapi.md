# FastAPI Implementation Plan: RF-INF-001 - User Management System

**Status**: READY
**Version**: 1.0.0
**Last Updated**: 2025-11-13
**Related Docs**: `.claude/plans/01-RF-INF-001-gestion-usuarios.md`

---

## Summary

This implementation plan provides comprehensive guidance for building a user management system with JWT authentication using FastAPI, SQLAlchemy async, and SQLite3. The system follows Clean Architecture principles with strict layer separation: Domain (pure business logic), Infrastructure (database/auth implementations), and API (HTTP entrypoints).

**Key Features:**
- User registration with email uniqueness validation
- JWT-based authentication with bcrypt password hashing
- Role-based user system (driver/passenger/both)
- Profile management (get/update current user)
- SQLAlchemy async with SQLite backend
- Repository pattern with interface abstraction
- Comprehensive testing strategy with in-memory SQLite

**Technology Stack:**
- **Framework**: FastAPI 0.104+
- **ORM**: SQLAlchemy 2.0+ (async)
- **Database**: SQLite3 (dev/test), PostgreSQL-ready for production
- **Auth**: python-jose (JWT), passlib[bcrypt] (password hashing)
- **Migrations**: Alembic
- **Testing**: pytest, pytest-asyncio, httpx

---

## Architecture Mapping

### Domain → FastAPI Mapping

| Domain Concept | FastAPI Construct | Location | Notes |
|---------------|------------------|----------|-------|
| User Entity | Pure Python dataclass | `domain/models.py` | No framework dependencies |
| User ORM Model | SQLAlchemy Table | `infrastructure/persistence/models.py` | Database schema |
| IUserRepository | ABC Interface | `domain/repositories/user_repository.py` | Contract definition |
| UserRepository | Concrete Implementation | `infrastructure/repositories/user_repository.py` | SQLAlchemy queries |
| RegisterUser Command | POST endpoint | `api/v1/views.py::register()` | Creates user + returns token |
| LoginUser Command | POST endpoint | `api/v1/views.py::login()` | Validates credentials + returns token |
| GetProfile Query | GET endpoint | `api/v1/views.py::get_current_user_profile()` | Returns authenticated user |
| UpdateProfile Command | PUT endpoint | `api/v1/views.py::update_current_user_profile()` | Updates user fields |
| Password Hashing | Utility Functions | `infrastructure/auth/password.py` | bcrypt via passlib |
| JWT Generation | Utility Functions | `infrastructure/auth/jwt.py` | python-jose |
| Get Current User | Dependency | `infrastructure/dependencies.py` | Extracts user from JWT |

### Layer Responsibilities

**Domain Layer** (`apps/users/domain/`)
- Define pure Python User entity (dataclass or Pydantic BaseModel)
- Define UserRole enum
- Define IUserRepository interface (ABC)
- **ZERO dependencies on FastAPI, SQLAlchemy, or any framework**
- Represents the business language and rules

**Infrastructure Layer** (`apps/users/infrastructure/`)
- Implement UserRepository using SQLAlchemy AsyncSession
- Define SQLAlchemy ORM models (UserORM)
- Implement password hashing (passlib + bcrypt)
- Implement JWT token creation/validation (python-jose)
- Define dependency injection functions
- **Depends on**: Domain layer, SQLAlchemy, FastAPI dependencies

**API Layer** (`apps/users/api/`)
- Define Pydantic request/response schemas
- Implement FastAPI endpoints (routers)
- Handle HTTP concerns (status codes, headers)
- Translate between HTTP DTOs and domain entities
- **Depends on**: Domain layer, Infrastructure layer

### Dependency Flow (Clean Architecture)

```
API Layer (FastAPI routers)
    ↓ depends on
Infrastructure Layer (Repositories, Auth, DB)
    ↓ depends on
Domain Layer (Entities, Interfaces)
    ↓ depends on
Nothing (pure Python)
```

**Critical Rule**: Domain layer NEVER imports from Infrastructure or API layers.

---

## File Actions

### Create New Files

#### Domain Layer
- `apps/users/domain/__init__.py` - Package marker
- `apps/users/domain/models.py` - User entity (pure Python), UserRole enum
- `apps/users/domain/repositories/__init__.py` - Package marker
- `apps/users/domain/repositories/user_repository.py` - IUserRepository interface (ABC)

#### Infrastructure Layer
- `apps/users/infrastructure/__init__.py` - Package marker
- `apps/users/infrastructure/persistence/__init__.py` - Package marker
- `apps/users/infrastructure/persistence/models.py` - SQLAlchemy UserORM model
- `apps/users/infrastructure/repositories/__init__.py` - Package marker
- `apps/users/infrastructure/repositories/user_repository.py` - UserRepository implementation (SQLAlchemy)
- `apps/users/infrastructure/auth/__init__.py` - Package marker
- `apps/users/infrastructure/auth/password.py` - Password hashing utilities
- `apps/users/infrastructure/auth/jwt.py` - JWT token utilities
- `apps/users/infrastructure/dependencies.py` - FastAPI dependency injection

#### API Layer
- `apps/users/api/__init__.py` - Package marker
- `apps/users/api/versioning/__init__.py` - Package marker
- `apps/users/api/versioning/v1/__init__.py` - Package marker
- `apps/users/api/versioning/v1/schemas/__init__.py` - Package marker
- `apps/users/api/versioning/v1/schemas/requests.py` - Pydantic request models
- `apps/users/api/versioning/v1/schemas/responses.py` - Pydantic response models
- `apps/users/api/versioning/v1/views.py` - FastAPI router with endpoints
- `apps/users/api/urls.py` - Router aggregator

#### Migrations
- `alembic/versions/{timestamp}_create_users_table.py` - Alembic migration

#### Tests
- `tests/test_users/__init__.py` - Package marker
- `tests/test_users/conftest.py` - Pytest fixtures (test DB, async client)
- `tests/test_users/test_auth.py` - Registration and login tests
- `tests/test_users/test_profile.py` - Profile management tests
- `tests/test_users/test_repository.py` - Repository unit tests

### Modify Existing Files
- `main.py` - Register users router
- `config/settings.py` - Add JWT settings (SECRET_KEY, ALGORITHM, TOKEN_EXPIRE)
- `config/database.py` - Ensure `get_async_session()` dependency exists
- `pyproject.toml` - Add dependencies (passlib, python-jose, etc.)

---

## API Endpoints

| Method | Path | Request Model | Response Model | Use Case | Auth Required |
|--------|------|--------------|----------------|----------|---------------|
| POST | `/api/v1/auth/register` | `RegisterRequest` | `TokenResponse` | Register new user | No |
| POST | `/api/v1/auth/login` | `OAuth2PasswordRequestForm` | `TokenResponse` | Login (get JWT) | No |
| GET | `/api/v1/users/me` | - | `UserResponse` | Get current user profile | Yes |
| PUT | `/api/v1/users/me` | `UpdateProfileRequest` | `UserResponse` | Update current user profile | Yes |
| GET | `/api/v1/users/{user_id}` | - | `UserResponse` | Get public user profile | Yes |

### Endpoint Details

#### POST /api/v1/auth/register
**Purpose**: Create new user account and return JWT token
**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123",
  "name": "Juan Pérez",
  "phone": "+34600000000",
  "role": "passenger"
}
```
**Response (201 Created)**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "1",
    "email": "user@example.com",
    "name": "Juan Pérez",
    "phone": "+34600000000",
    "role": "passenger",
    "is_active": true,
    "is_verified": false,
    "created_at": "2025-11-13T10:00:00Z",
    "vehicle_model": null,
    "vehicle_plate": null,
    "license_number": null
  }
}
```
**Errors**:
- 400: Email already registered
- 422: Validation error (invalid email, password too short, etc.)

#### POST /api/v1/auth/login
**Purpose**: Authenticate user and return JWT token
**Request Body**: Uses `OAuth2PasswordRequestForm` (form-data)
- `username`: Email address (OAuth2 standard uses "username")
- `password`: Plain password

**Response (200 OK)**: Same as register (TokenResponse)
**Errors**:
- 401: Incorrect email or password
- 403: User account is inactive

#### GET /api/v1/users/me
**Purpose**: Get authenticated user's profile
**Headers**: `Authorization: Bearer {token}`
**Response (200 OK)**: `UserResponse` object
**Errors**:
- 401: Invalid or missing token

#### PUT /api/v1/users/me
**Purpose**: Update authenticated user's profile (partial update)
**Headers**: `Authorization: Bearer {token}`
**Request Body** (all fields optional):
```json
{
  "name": "Juan Pérez Updated",
  "phone": "+34600000001",
  "vehicle_model": "Toyota Corolla",
  "vehicle_plate": "ABC-1234",
  "license_number": "B-12345678"
}
```
**Response (200 OK)**: Updated `UserResponse` object
**Errors**:
- 401: Invalid or missing token
- 422: Validation error

#### GET /api/v1/users/{user_id}
**Purpose**: Get public profile of another user (e.g., for viewing driver/passenger info)
**Headers**: `Authorization: Bearer {token}`
**Response (200 OK)**: `UserResponse` object
**Errors**:
- 401: Invalid or missing token
- 404: User not found

---

## Dependencies

### Required Packages

Add to `pyproject.toml`:

```toml
[tool.poetry.dependencies]
python = "^3.11"

# Core Framework
fastapi = "^0.104.0"
uvicorn = {extras = ["standard"], version = "^0.24.0"}

# Database
sqlalchemy = {extras = ["asyncio"], version = "^2.0.23"}
aiosqlite = "^0.19.0"  # Async SQLite driver
alembic = "^1.12.0"

# Validation & Serialization
pydantic = {extras = ["email"], version = "^2.5.0"}
pydantic-settings = "^2.1.0"

# Authentication
python-jose = {extras = ["cryptography"], version = "^3.3.0"}  # JWT
passlib = {extras = ["bcrypt"], version = "^1.7.4"}  # Password hashing

[tool.poetry.group.dev.dependencies]
# Testing
pytest = "^7.4.0"
pytest-asyncio = "^0.21.0"
httpx = "^0.25.0"  # Async HTTP client for testing

# Code Quality
black = "^23.11.0"
ruff = "^0.1.6"
mypy = "^1.7.0"
```

**Install Command**:
```bash
poetry add sqlalchemy[asyncio] aiosqlite alembic pydantic[email] python-jose[cryptography] passlib[bcrypt]
poetry add --group dev pytest pytest-asyncio httpx
```

### Dependency Injection Hierarchy

```
FastAPI Request
    ↓
get_async_session() → AsyncSession (from config/database.py)
    ↓
get_user_repository(session) → IUserRepository (concrete: UserRepository)
    ↓
Endpoint Handler Function
    ↓ (for protected endpoints)
get_current_user(token, repo) → User
    ↓
Endpoint Handler Logic
```

**Key Dependencies**:
1. `get_async_session`: Provides SQLAlchemy async session (DB connection)
2. `get_user_repository`: Creates UserRepository instance with session
3. `oauth2_scheme`: Extracts Bearer token from Authorization header
4. `get_current_user`: Validates JWT, fetches user from DB, returns User entity

---

## Domain Layer Implementation

### 1. User Entity (Pure Python)

**File**: `apps/users/domain/models.py`

```python
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class UserRole(str, Enum):
    """User roles in the system"""
    DRIVER = "driver"
    PASSENGER = "passenger"
    BOTH = "both"


@dataclass
class User:
    """
    User domain entity (pure Python, no framework dependencies)

    This is the core business representation of a User.
    It should contain only business logic and data.
    """
    email: str
    password_hash: str  # NEVER store plain passwords
    name: str
    role: UserRole

    # Optional fields
    id: Optional[int] = None
    phone: Optional[str] = None
    is_active: bool = True
    is_verified: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    # Driver-specific fields (only used when role is DRIVER or BOTH)
    vehicle_model: Optional[str] = None
    vehicle_plate: Optional[str] = None
    license_number: Optional[str] = None

    def __post_init__(self):
        """Validate business rules"""
        if not self.email or "@" not in self.email:
            raise ValueError("Invalid email address")
        if len(self.name) < 2:
            raise ValueError("Name must be at least 2 characters")
        if not self.password_hash:
            raise ValueError("Password hash is required")

    def is_driver(self) -> bool:
        """Check if user can act as driver"""
        return self.role in (UserRole.DRIVER, UserRole.BOTH)

    def is_passenger(self) -> bool:
        """Check if user can act as passenger"""
        return self.role in (UserRole.PASSENGER, UserRole.BOTH)
```

**Design Notes**:
- Uses Python `dataclass` for simplicity (could also use plain class)
- NO Pydantic here (that's for API layer)
- NO SQLAlchemy imports (that's for infrastructure layer)
- Contains only business logic (validation, role checks)
- `password_hash` field emphasizes we never store plain passwords

### 2. Repository Interface

**File**: `apps/users/domain/repositories/user_repository.py`

```python
from abc import ABC, abstractmethod
from typing import Optional, List

from apps.users.domain.models import User


class IUserRepository(ABC):
    """
    Repository contract for User persistence

    This interface defines what operations are available for User entities.
    Implementations can use any persistence technology (SQLAlchemy, MongoDB, etc.)
    """

    @abstractmethod
    async def create(self, user: User) -> User:
        """
        Create a new user in the database.

        Args:
            user: User entity (without id)

        Returns:
            User entity with assigned id

        Raises:
            Exception: If email already exists or other constraint violation
        """
        pass

    @abstractmethod
    async def get_by_id(self, user_id: int) -> Optional[User]:
        """
        Retrieve user by ID.

        Args:
            user_id: User's primary key

        Returns:
            User entity if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Retrieve user by email address (for login).

        Args:
            email: User's email address

        Returns:
            User entity if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_all(self, skip: int = 0, limit: int = 100) -> List[User]:
        """
        List users with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of User entities
        """
        pass

    @abstractmethod
    async def update(self, user_id: int, user: User) -> bool:
        """
        Update existing user.

        Args:
            user_id: User's primary key
            user: User entity with updated data

        Returns:
            True if user was updated, False if not found
        """
        pass

    @abstractmethod
    async def delete(self, user_id: int) -> bool:
        """
        Soft delete user (mark as inactive).

        Args:
            user_id: User's primary key

        Returns:
            True if user was deleted, False if not found
        """
        pass

    @abstractmethod
    async def email_exists(self, email: str) -> bool:
        """
        Check if email is already registered.

        Args:
            email: Email address to check

        Returns:
            True if email exists, False otherwise
        """
        pass
```

**Design Notes**:
- All methods are `async` (repository operations are I/O bound)
- Returns domain entities (`User`), not ORM models
- Uses `Optional[User]` for get operations (explicit None handling)
- Abstract base class enforces contract for all implementations

---

## Infrastructure Layer Implementation

### 1. SQLAlchemy ORM Model

**File**: `apps/users/infrastructure/persistence/models.py`

```python
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from config.database import Base
from apps.users.domain.models import UserRole


class UserORM(Base):
    """
    SQLAlchemy ORM model for User table

    This is the database representation, separate from domain entity.
    Uses SQLAlchemy 2.0 mapped_column syntax.
    """
    __tablename__ = "users"

    # Primary Key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Required Fields
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(
        Enum(UserRole, native_enum=False, length=20),
        nullable=False,
        default=UserRole.PASSENGER.value
    )

    # Optional Fields
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Status Fields
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        onupdate=datetime.utcnow,
        nullable=True
    )

    # Driver-specific fields
    vehicle_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    vehicle_plate: Mapped[str | None] = mapped_column(String(20), nullable=True)
    license_number: Mapped[str | None] = mapped_column(String(50), nullable=True)

    def to_domain(self) -> "User":
        """
        Convert ORM model to domain entity

        This is the bridge between infrastructure and domain layers.
        """
        from apps.users.domain.models import User

        return User(
            id=self.id,
            email=self.email,
            password_hash=self.password_hash,
            name=self.name,
            phone=self.phone,
            role=UserRole(self.role),
            is_active=self.is_active,
            is_verified=self.is_verified,
            created_at=self.created_at,
            updated_at=self.updated_at,
            vehicle_model=self.vehicle_model,
            vehicle_plate=self.vehicle_plate,
            license_number=self.license_number,
        )

    @staticmethod
    def from_domain(user: "User") -> "UserORM":
        """
        Convert domain entity to ORM model

        Used when creating/updating database records.
        """
        return UserORM(
            id=user.id,
            email=user.email,
            password_hash=user.password_hash,
            name=user.name,
            phone=user.phone,
            role=user.role.value,
            is_active=user.is_active,
            is_verified=user.is_verified,
            created_at=user.created_at,
            updated_at=user.updated_at,
            vehicle_model=user.vehicle_model,
            vehicle_plate=user.vehicle_plate,
            license_number=user.license_number,
        )

    def __repr__(self) -> str:
        return f"<UserORM(id={self.id}, email={self.email}, role={self.role})>"
```

**Design Notes**:
- SQLAlchemy 2.0 style with `Mapped` type hints
- Separate from domain entity (different concerns)
- `to_domain()` and `from_domain()` methods for conversion
- Indexes on `email` for fast lookups
- Uses `Enum` storage as string for readability in DB

### 2. Repository Implementation

**File**: `apps/users/infrastructure/repositories/user_repository.py`

```python
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.users.domain.models import User
from apps.users.domain.repositories.user_repository import IUserRepository
from apps.users.infrastructure.persistence.models import UserORM


class UserRepository(IUserRepository):
    """
    SQLAlchemy implementation of IUserRepository

    Uses async SQLAlchemy session for all database operations.
    Converts between ORM models (UserORM) and domain entities (User).
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize repository with async session

        Args:
            session: SQLAlchemy async session (injected by FastAPI)
        """
        self._session = session

    async def create(self, user: User) -> User:
        """Create new user in database"""
        user_orm = UserORM.from_domain(user)

        self._session.add(user_orm)
        await self._session.commit()
        await self._session.refresh(user_orm)

        return user_orm.to_domain()

    async def get_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        stmt = select(UserORM).where(UserORM.id == user_id)
        result = await self._session.execute(stmt)
        user_orm = result.scalar_one_or_none()

        return user_orm.to_domain() if user_orm else None

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email (case-insensitive)"""
        stmt = select(UserORM).where(UserORM.email == email.lower())
        result = await self._session.execute(stmt)
        user_orm = result.scalar_one_or_none()

        return user_orm.to_domain() if user_orm else None

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[User]:
        """List users with pagination"""
        stmt = select(UserORM).offset(skip).limit(limit).order_by(UserORM.created_at.desc())
        result = await self._session.execute(stmt)
        user_orms = result.scalars().all()

        return [user_orm.to_domain() for user_orm in user_orms]

    async def update(self, user_id: int, user: User) -> bool:
        """Update existing user"""
        stmt = select(UserORM).where(UserORM.id == user_id)
        result = await self._session.execute(stmt)
        user_orm = result.scalar_one_or_none()

        if not user_orm:
            return False

        # Update fields
        user_orm.name = user.name
        user_orm.phone = user.phone
        user_orm.role = user.role.value
        user_orm.is_active = user.is_active
        user_orm.is_verified = user.is_verified
        user_orm.vehicle_model = user.vehicle_model
        user_orm.vehicle_plate = user.vehicle_plate
        user_orm.license_number = user.license_number
        user_orm.updated_at = datetime.utcnow()

        await self._session.commit()
        return True

    async def delete(self, user_id: int) -> bool:
        """Soft delete user (mark as inactive)"""
        stmt = select(UserORM).where(UserORM.id == user_id)
        result = await self._session.execute(stmt)
        user_orm = result.scalar_one_or_none()

        if not user_orm:
            return False

        user_orm.is_active = False
        user_orm.updated_at = datetime.utcnow()

        await self._session.commit()
        return True

    async def email_exists(self, email: str) -> bool:
        """Check if email already exists"""
        stmt = select(UserORM.id).where(UserORM.email == email.lower())
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None
```

**Design Notes**:
- All database operations use SQLAlchemy 2.0 `select()` syntax
- Always converts ORM models to domain entities before returning
- Email searches are case-insensitive (`.lower()`)
- Soft delete implementation (sets `is_active=False`)
- Uses `commit()` + `refresh()` pattern for create operations

### 3. Password Hashing Utilities

**File**: `apps/users/infrastructure/auth/password.py`

```python
from passlib.context import CryptContext

# Configure bcrypt password hashing context
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12  # Cost factor (higher = slower but more secure)
)


def hash_password(plain_password: str) -> str:
    """
    Hash a plain password using bcrypt

    Args:
        plain_password: Password in plain text

    Returns:
        Hashed password string (safe to store in database)
    """
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password

    Args:
        plain_password: Password to verify
        hashed_password: Stored password hash

    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)
```

**Design Notes**:
- Uses passlib with bcrypt backend (industry standard)
- Bcrypt rounds=12 balances security and performance
- Functions are pure (no state, no dependencies)
- Can be used anywhere in application (framework-agnostic)

### 4. JWT Utilities

**File**: `apps/users/infrastructure/auth/jwt.py`

```python
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt

from config.settings import settings


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token

    Args:
        data: Payload data (typically {"sub": user_id})
        expires_delta: Custom expiration time (optional)

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decode and validate JWT token

    Args:
        token: JWT token string

    Returns:
        Decoded payload if valid, None if invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None
```

**Design Notes**:
- Uses python-jose for JWT operations
- Token expiration configurable via settings
- Returns `None` on decode failure (explicit error handling)
- Payload typically contains `{"sub": user_id, "exp": timestamp}`

### 5. Dependency Injection

**File**: `apps/users/infrastructure/dependencies.py`

```python
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_async_session
from apps.users.domain.models import User
from apps.users.domain.repositories.user_repository import IUserRepository
from apps.users.infrastructure.repositories.user_repository import UserRepository
from apps.users.infrastructure.auth.jwt import decode_access_token

# OAuth2 scheme for token extraction from Authorization header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_user_repository(
    session: Annotated[AsyncSession, Depends(get_async_session)]
) -> IUserRepository:
    """
    Dependency that provides UserRepository instance

    Args:
        session: SQLAlchemy async session (injected)

    Returns:
        IUserRepository implementation (UserRepository)
    """
    return UserRepository(session)


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    repo: Annotated[IUserRepository, Depends(get_user_repository)]
) -> User:
    """
    Dependency that extracts and validates current user from JWT token

    Args:
        token: JWT token from Authorization header
        repo: User repository for database lookup

    Returns:
        Current User entity

    Raises:
        HTTPException 401: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Decode token
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    # Extract user ID from token payload
    user_id_str: str = payload.get("sub")
    if user_id_str is None:
        raise credentials_exception

    try:
        user_id = int(user_id_str)
    except ValueError:
        raise credentials_exception

    # Fetch user from database
    user = await repo.get_by_id(user_id)
    if user is None:
        raise credentials_exception

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    return user
```

**Design Notes**:
- `oauth2_scheme` extracts token from `Authorization: Bearer {token}` header
- `get_user_repository` creates repository with injected session
- `get_current_user` validates token and fetches user (used for protected endpoints)
- Raises proper HTTP exceptions (401 for auth failure, 403 for inactive user)

---

## API Layer Implementation

### 1. Request Schemas

**File**: `apps/users/api/versioning/v1/schemas/requests.py`

```python
from pydantic import BaseModel, EmailStr, Field, field_validator

from apps.users.domain.models import UserRole


class RegisterRequest(BaseModel):
    """Schema for user registration request"""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., pattern=r"^\+?[1-9]\d{1,14}$")
    role: UserRole = Field(default=UserRole.PASSENGER)

    @field_validator("email")
    @classmethod
    def email_to_lowercase(cls, v: str) -> str:
        """Normalize email to lowercase"""
        return v.lower()

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "juan@example.com",
                "password": "SecurePassword123",
                "name": "Juan Pérez",
                "phone": "+34600000000",
                "role": "passenger"
            }
        }
    }


class LoginRequest(BaseModel):
    """Schema for login request (alternative to OAuth2PasswordRequestForm)"""

    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def email_to_lowercase(cls, v: str) -> str:
        """Normalize email to lowercase"""
        return v.lower()


class UpdateProfileRequest(BaseModel):
    """Schema for updating user profile (partial update)"""

    name: str | None = Field(None, min_length=2, max_length=100)
    phone: str | None = Field(None, pattern=r"^\+?[1-9]\d{1,14}$")
    vehicle_model: str | None = Field(None, max_length=100)
    vehicle_plate: str | None = Field(None, max_length=20)
    license_number: str | None = Field(None, max_length=50)

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Juan Pérez Updated",
                "phone": "+34600000001",
                "vehicle_model": "Toyota Corolla",
                "vehicle_plate": "ABC-1234",
                "license_number": "B-12345678"
            }
        }
    }
```

**Design Notes**:
- Pydantic v2 syntax (`model_config` instead of `Config`)
- Email validation with `EmailStr`
- Phone regex pattern (E.164 format)
- Password minimum 8 characters (OWASP recommendation)
- All fields optional in `UpdateProfileRequest` (partial update)

### 2. Response Schemas

**File**: `apps/users/api/versioning/v1/schemas/responses.py`

```python
from datetime import datetime
from pydantic import BaseModel, EmailStr

from apps.users.domain.models import UserRole


class UserResponse(BaseModel):
    """Schema for user data in API responses"""

    id: int
    email: EmailStr
    name: str
    phone: str | None
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime

    # Driver-specific fields
    vehicle_model: str | None = None
    vehicle_plate: str | None = None
    license_number: str | None = None

    model_config = {
        "from_attributes": True,  # Enable ORM mode for SQLAlchemy models
        "json_schema_extra": {
            "example": {
                "id": 1,
                "email": "juan@example.com",
                "name": "Juan Pérez",
                "phone": "+34600000000",
                "role": "passenger",
                "is_active": True,
                "is_verified": False,
                "created_at": "2025-11-13T10:00:00Z",
                "vehicle_model": None,
                "vehicle_plate": None,
                "license_number": None
            }
        }
    }


class TokenResponse(BaseModel):
    """Schema for authentication response (login/register)"""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse

    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "user": {
                    "id": 1,
                    "email": "juan@example.com",
                    "name": "Juan Pérez",
                    "phone": "+34600000000",
                    "role": "passenger",
                    "is_active": True,
                    "is_verified": False,
                    "created_at": "2025-11-13T10:00:00Z"
                }
            }
        }
    }
```

**Design Notes**:
- `from_attributes=True` enables ORM mode (can create from SQLAlchemy models)
- Does NOT expose `password_hash` or `updated_at` (security/unnecessary)
- `TokenResponse` combines token and user data for convenience

### 3. FastAPI Endpoints

**File**: `apps/users/api/versioning/v1/views.py`

```python
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from apps.users.domain.models import User
from apps.users.domain.repositories.user_repository import IUserRepository
from apps.users.infrastructure.dependencies import get_user_repository, get_current_user
from apps.users.infrastructure.auth.password import hash_password, verify_password
from apps.users.infrastructure.auth.jwt import create_access_token
from apps.users.api.versioning.v1.schemas.requests import (
    RegisterRequest,
    UpdateProfileRequest
)
from apps.users.api.versioning.v1.schemas.responses import (
    UserResponse,
    TokenResponse
)

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    repo: Annotated[IUserRepository, Depends(get_user_repository)]
):
    """
    Register new user account

    Creates a new user with hashed password and returns JWT token.
    """
    # Check if email already exists
    if await repo.email_exists(payload.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create user entity
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        name=payload.name,
        phone=payload.phone,
        role=payload.role
    )

    # Persist to database
    created_user = await repo.create(user)

    # Generate JWT token
    access_token = create_access_token(data={"sub": str(created_user.id)})

    return TokenResponse(
        access_token=access_token,
        user=UserResponse.model_validate(created_user)
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    repo: Annotated[IUserRepository, Depends(get_user_repository)]
):
    """
    Authenticate user and return JWT token

    Uses OAuth2PasswordRequestForm (form-data with username/password).
    Note: 'username' field contains email address.
    """
    # Find user by email (OAuth2 uses 'username' field)
    user = await repo.get_by_email(form_data.username)

    # Verify credentials
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    # Generate JWT token
    access_token = create_access_token(data={"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user)
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: Annotated[User, Depends(get_current_user)]
):
    """
    Get authenticated user's profile

    Requires valid JWT token in Authorization header.
    """
    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse)
async def update_current_user_profile(
    payload: UpdateProfileRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    repo: Annotated[IUserRepository, Depends(get_user_repository)]
):
    """
    Update authenticated user's profile

    Supports partial updates (only provided fields are updated).
    Requires valid JWT token in Authorization header.
    """
    # Update only provided fields
    if payload.name is not None:
        current_user.name = payload.name
    if payload.phone is not None:
        current_user.phone = payload.phone
    if payload.vehicle_model is not None:
        current_user.vehicle_model = payload.vehicle_model
    if payload.vehicle_plate is not None:
        current_user.vehicle_plate = payload.vehicle_plate
    if payload.license_number is not None:
        current_user.license_number = payload.license_number

    # Persist changes
    success = await repo.update(current_user.id, current_user)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile"
        )

    return UserResponse.model_validate(current_user)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: int,
    repo: Annotated[IUserRepository, Depends(get_user_repository)],
    _: Annotated[User, Depends(get_current_user)]  # Requires authentication
):
    """
    Get public profile of another user by ID

    Useful for viewing driver/passenger profiles in trip matching.
    Requires valid JWT token in Authorization header.
    """
    user = await repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return UserResponse.model_validate(user)
```

**Design Notes**:
- Uses `Annotated[Type, Depends(dependency)]` for dependency injection
- `OAuth2PasswordRequestForm` for `/login` (standard OAuth2 form)
- All protected endpoints use `Depends(get_current_user)`
- Proper HTTP status codes (201 for creation, 401 for auth failure, etc.)
- Email used in `form_data.username` field (OAuth2 convention)

### 4. Router Registration

**File**: `apps/users/api/urls.py`

```python
from fastapi import APIRouter

from apps.users.api.versioning.v1.views import router as v1_router

router = APIRouter()
router.include_router(v1_router, tags=["Users & Auth"])
```

**File**: `main.py` (modification)

```python
from fastapi import FastAPI
from apps.users.api.urls import router as users_router

app = FastAPI(
    title="Vibe Coding Backend",
    version="1.0.0"
)

# Register user management routers
app.include_router(users_router, prefix="/api/v1/auth")
app.include_router(users_router, prefix="/api/v1/users")

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

---

## Data Persistence

### Database Configuration

**File**: `config/database.py` (ensure this exists)

```python
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

from config.settings import settings

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,  # Log SQL queries in debug mode
    future=True
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# Base class for ORM models
Base = declarative_base()


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides async database session

    Usage:
        session: AsyncSession = Depends(get_async_session)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Create all tables (for development/testing)"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_db():
    """Drop all tables (for testing)"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
```

**File**: `config/settings.py` (add JWT settings)

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Vibe Coding Backend"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./vibe_coding.db"

    # JWT Authentication
    SECRET_KEY: str = "your-secret-key-change-in-production"  # MUST change in production
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    class Config:
        env_file = ".env"


settings = Settings()
```

**Important**: Generate secure `SECRET_KEY` for production:
```python
import secrets
print(secrets.token_urlsafe(32))
```

### Alembic Migration

**File**: `alembic/versions/{timestamp}_create_users_table.py`

Generate migration:
```bash
alembic revision --autogenerate -m "Create users table"
```

**Migration content**:
```python
"""Create users table

Revision ID: {revision_id}
Revises:
Create Date: 2025-11-13
"""
from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    """Create users table with all fields and indexes"""
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('vehicle_model', sa.String(length=100), nullable=True),
        sa.Column('vehicle_plate', sa.String(length=20), nullable=True),
        sa.Column('license_number', sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Create unique index on email
    op.create_index('ix_users_email', 'users', ['email'], unique=True)


def downgrade() -> None:
    """Drop users table"""
    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')
```

**Run migration**:
```bash
alembic upgrade head
```

---

## Error Handling

### Domain Error Mapping

| Domain Error | HTTP Status | Response Format | Example |
|--------------|-------------|----------------|---------|
| Email already exists | 400 BAD_REQUEST | `{"detail": "Email already registered"}` | Duplicate registration |
| Invalid credentials | 401 UNAUTHORIZED | `{"detail": "Incorrect email or password"}` | Wrong password |
| Invalid token | 401 UNAUTHORIZED | `{"detail": "Could not validate credentials"}` | Expired/malformed JWT |
| User inactive | 403 FORBIDDEN | `{"detail": "User account is inactive"}` | Soft-deleted user |
| User not found | 404 NOT_FOUND | `{"detail": "User not found"}` | Invalid user_id |
| Validation error | 422 UNPROCESSABLE_ENTITY | Pydantic validation details | Invalid email format |
| Server error | 500 INTERNAL_SERVER_ERROR | `{"detail": "Failed to update profile"}` | Database failure |

### Exception Handlers

FastAPI automatically handles:
- Pydantic validation errors → 422
- HTTPException → specified status code
- Uncaught exceptions → 500

For custom error handling, add to `main.py`:

```python
from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle domain validation errors"""
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)}
    )
```

---

## Testing Strategy

### Test Database Setup

**File**: `tests/conftest.py`

```python
import asyncio
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from config.database import Base, get_async_session
from main import app

# In-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    future=True
)

TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_db():
    """Create test database schema"""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
async def test_session(test_db):
    """Provide test database session"""
    async with TestSessionLocal() as session:
        yield session


@pytest.fixture(scope="function")
async def client(test_session):
    """Provide async HTTP client with test database"""
    async def override_get_async_session():
        yield test_session

    app.dependency_overrides[get_async_session] = override_get_async_session

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
```

### Integration Tests

**File**: `tests/test_users/test_auth.py`

```python
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    """Test successful user registration"""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "password123",
            "name": "Test User",
            "phone": "+34600000000",
            "role": "passenger"
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "test@example.com"
    assert data["user"]["role"] == "passenger"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    """Test registration with duplicate email"""
    user_data = {
        "email": "duplicate@example.com",
        "password": "password123",
        "name": "User 1",
        "phone": "+34600000001"
    }

    # First registration
    response1 = await client.post("/api/v1/auth/register", json=user_data)
    assert response1.status_code == 201

    # Second registration with same email
    response2 = await client.post("/api/v1/auth/register", json=user_data)
    assert response2.status_code == 400
    assert "already registered" in response2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_invalid_email(client: AsyncClient):
    """Test registration with invalid email"""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "not-an-email",
            "password": "password123",
            "name": "Test User",
            "phone": "+34600000000"
        }
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    """Test successful login"""
    # Register user first
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "login@example.com",
            "password": "password123",
            "name": "Login User",
            "phone": "+34600000000"
        }
    )

    # Login
    response = await client.post(
        "/api/v1/auth/login",
        data={  # OAuth2 uses form-data
            "username": "login@example.com",
            "password": "password123"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "login@example.com"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    """Test login with wrong password"""
    # Register user first
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "user@example.com",
            "password": "correctpassword",
            "name": "User",
            "phone": "+34600000000"
        }
    )

    # Login with wrong password
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "user@example.com",
            "password": "wrongpassword"
        }
    )

    assert response.status_code == 401
    assert "incorrect" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    """Test login with non-existent email"""
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "nonexistent@example.com",
            "password": "password123"
        }
    )

    assert response.status_code == 401
```

**File**: `tests/test_users/test_profile.py`

```python
import pytest
from httpx import AsyncClient


async def create_user_and_get_token(client: AsyncClient, email: str) -> str:
    """Helper function to register user and get token"""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "password123",
            "name": "Test User",
            "phone": "+34600000000"
        }
    )
    return response.json()["access_token"]


@pytest.mark.asyncio
async def test_get_current_user_profile(client: AsyncClient):
    """Test getting current user profile"""
    token = await create_user_and_get_token(client, "profile@example.com")

    response = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "profile@example.com"
    assert data["name"] == "Test User"


@pytest.mark.asyncio
async def test_get_profile_without_token(client: AsyncClient):
    """Test getting profile without authentication"""
    response = await client.get("/api/v1/users/me")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_profile(client: AsyncClient):
    """Test updating user profile"""
    token = await create_user_and_get_token(client, "update@example.com")

    response = await client.put(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Updated Name",
            "phone": "+34600000001",
            "vehicle_model": "Toyota Corolla"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["phone"] == "+34600000001"
    assert data["vehicle_model"] == "Toyota Corolla"


@pytest.mark.asyncio
async def test_get_user_by_id(client: AsyncClient):
    """Test getting another user's profile by ID"""
    # Create two users
    token1 = await create_user_and_get_token(client, "user1@example.com")

    response_register = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "user2@example.com",
            "password": "password123",
            "name": "User 2",
            "phone": "+34600000001"
        }
    )
    user2_id = response_register.json()["user"]["id"]

    # Get user2 profile using user1's token
    response = await client.get(
        f"/api/v1/users/{user2_id}",
        headers={"Authorization": f"Bearer {token1}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "user2@example.com"
    assert data["name"] == "User 2"
```

### Repository Unit Tests

**File**: `tests/test_users/test_repository.py`

```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from apps.users.domain.models import User, UserRole
from apps.users.infrastructure.repositories.user_repository import UserRepository


@pytest.mark.asyncio
async def test_create_user(test_session: AsyncSession):
    """Test creating a user"""
    repo = UserRepository(test_session)

    user = User(
        email="test@example.com",
        password_hash="hashed_password",
        name="Test User",
        role=UserRole.PASSENGER
    )

    created_user = await repo.create(user)

    assert created_user.id is not None
    assert created_user.email == "test@example.com"


@pytest.mark.asyncio
async def test_get_by_email(test_session: AsyncSession):
    """Test getting user by email"""
    repo = UserRepository(test_session)

    # Create user
    user = User(
        email="find@example.com",
        password_hash="hashed",
        name="Find Me",
        role=UserRole.DRIVER
    )
    created_user = await repo.create(user)

    # Find by email
    found_user = await repo.get_by_email("find@example.com")

    assert found_user is not None
    assert found_user.id == created_user.id
    assert found_user.email == "find@example.com"


@pytest.mark.asyncio
async def test_email_exists(test_session: AsyncSession):
    """Test checking if email exists"""
    repo = UserRepository(test_session)

    # Create user
    user = User(
        email="exists@example.com",
        password_hash="hashed",
        name="Exists User",
        role=UserRole.BOTH
    )
    await repo.create(user)

    # Check existence
    assert await repo.email_exists("exists@example.com") is True
    assert await repo.email_exists("nonexistent@example.com") is False
```

### Test Coverage Requirements

- **Domain Layer**: 90%+ (focus on business logic)
- **Infrastructure Layer**: 80%+ (repository operations)
- **API Layer**: 85%+ (endpoint behavior, error handling)

**Run tests with coverage**:
```bash
pytest --cov=apps/users --cov-report=html
open htmlcov/index.html
```

---

## Observability

### Logging

**File**: `config/logging.py`

```python
import logging
import sys
from config.settings import settings

def setup_logging():
    """Configure structured logging"""
    logging.basicConfig(
        level=logging.DEBUG if settings.DEBUG else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Silence noisy loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
```

Add to `main.py`:
```python
from config.logging import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_event():
    logger.info("Application starting up")
```

### Request Logging Middleware

Add to `main.py`:

```python
import time
from fastapi import Request

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()

    response = await call_next(request)

    process_time = time.time() - start_time
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Duration: {process_time:.3f}s"
    )

    return response
```

---

## Open Questions

1. **Password Policy**: Should we enforce additional password requirements (uppercase, numbers, special chars)?
   - **Recommendation**: Start with minimum 8 characters, add complexity later if needed

2. **Email Verification**: Should we implement email verification flow (send verification link)?
   - **Recommendation**: Keep `is_verified` field for future implementation

3. **Rate Limiting**: Should we add rate limiting for registration/login endpoints?
   - **Recommendation**: Use `slowapi` or similar for production

4. **Refresh Tokens**: Should we implement refresh token mechanism?
   - **Recommendation**: Start with access tokens only, add refresh tokens if needed

5. **Role Permissions**: Should we add granular permissions beyond roles?
   - **Recommendation**: Current role system (driver/passenger/both) is sufficient for MVP

6. **Profile Pictures**: Should we add profile picture upload support?
   - **Recommendation**: Add in next iteration with file storage integration

7. **Production Database**: When to migrate from SQLite to PostgreSQL?
   - **Recommendation**: SQLite for development, PostgreSQL for staging/production
   - **Migration Path**: Same SQLAlchemy code works, just change `DATABASE_URL`

---

## Implementation Checklist

### Phase 1: Foundation (Core Architecture)
- [ ] Set up project structure (`domain/`, `infrastructure/`, `api/`)
- [ ] Add dependencies to `pyproject.toml` (SQLAlchemy, passlib, python-jose)
- [ ] Configure settings with JWT parameters (`config/settings.py`)
- [ ] Set up database connection (`config/database.py`)
- [ ] Configure Alembic for migrations

### Phase 2: Domain Layer (Business Logic)
- [ ] Create `UserRole` enum in `domain/models.py`
- [ ] Create `User` entity (pure Python dataclass)
- [ ] Define `IUserRepository` interface in `domain/repositories/`
- [ ] Add domain validation to User entity

### Phase 3: Infrastructure Layer (Persistence & Auth)
- [ ] Create `UserORM` SQLAlchemy model in `infrastructure/persistence/models.py`
- [ ] Implement `UserRepository` with SQLAlchemy in `infrastructure/repositories/`
- [ ] Create password hashing utilities (`infrastructure/auth/password.py`)
- [ ] Create JWT utilities (`infrastructure/auth/jwt.py`)
- [ ] Set up dependency injection (`infrastructure/dependencies.py`)

### Phase 4: Database Migration
- [ ] Generate Alembic migration: `alembic revision --autogenerate -m "Create users table"`
- [ ] Review and edit migration file
- [ ] Run migration: `alembic upgrade head`
- [ ] Verify database schema with SQLite browser

### Phase 5: API Layer (HTTP Endpoints)
- [ ] Create request schemas (`api/v1/schemas/requests.py`)
- [ ] Create response schemas (`api/v1/schemas/responses.py`)
- [ ] Implement `/register` endpoint in `api/v1/views.py`
- [ ] Implement `/login` endpoint in `api/v1/views.py`
- [ ] Implement `/me` GET endpoint (get profile)
- [ ] Implement `/me` PUT endpoint (update profile)
- [ ] Implement `/{user_id}` GET endpoint (get other user)
- [ ] Register routers in `main.py`

### Phase 6: Testing
- [ ] Set up test database configuration (`tests/conftest.py`)
- [ ] Write registration tests (`tests/test_users/test_auth.py`)
- [ ] Write login tests (success, wrong password, non-existent user)
- [ ] Write profile tests (get, update, get by ID)
- [ ] Write repository unit tests
- [ ] Run test coverage analysis: `pytest --cov=apps/users`
- [ ] Ensure 80%+ coverage

### Phase 7: Documentation & Validation
- [ ] Test all endpoints in Swagger UI (`/docs`)
- [ ] Verify JWT token generation and validation
- [ ] Test email uniqueness constraint
- [ ] Test password hashing (cannot reverse)
- [ ] Verify error responses (400, 401, 403, 404)
- [ ] Document API in OpenAPI/Swagger annotations

### Phase 8: Security Review
- [ ] Verify passwords are never logged or exposed in responses
- [ ] Confirm `SECRET_KEY` is in `.env` (not hardcoded)
- [ ] Test JWT token expiration
- [ ] Verify inactive users cannot login
- [ ] Test authentication bypass attempts
- [ ] Review OWASP security best practices

### Phase 9: Production Readiness
- [ ] Add rate limiting to auth endpoints
- [ ] Configure CORS if needed
- [ ] Set up proper logging
- [ ] Add health check endpoint
- [ ] Create `.env.example` file
- [ ] Update `README.md` with setup instructions
- [ ] Prepare for PostgreSQL migration (update `DATABASE_URL`)

---

## Quick Start Commands

```bash
# Install dependencies
poetry install

# Generate secret key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Set up environment
cat > .env << EOF
SECRET_KEY=your-generated-secret-key
DATABASE_URL=sqlite+aiosqlite:///./vibe_coding.db
DEBUG=True
EOF

# Initialize Alembic (if not already done)
alembic init alembic

# Generate migration
alembic revision --autogenerate -m "Create users table"

# Run migration
alembic upgrade head

# Start development server
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Run tests
pytest -v

# Run tests with coverage
pytest --cov=apps/users --cov-report=html

# Access API documentation
open http://localhost:8000/docs
```

---

## Architecture Validation

**Self-Check Questions**:
- [ ] Does domain layer have ZERO imports from FastAPI or SQLAlchemy?
- [ ] Can I swap SQLite for PostgreSQL by changing only `DATABASE_URL`?
- [ ] Can I test business logic without running HTTP server?
- [ ] Are passwords NEVER stored in plain text or logged?
- [ ] Are JWT tokens properly validated and expired?
- [ ] Do all endpoints return consistent error formats?
- [ ] Is email uniqueness enforced at database level?
- [ ] Are all async operations properly awaited?

---

## Next Steps

After completing RF-INF-001 (User Management), proceed with:

1. **RF-002: Trip Publication** (depends on user authentication)
2. **RF-003: Travel Request Management** (depends on user authentication)
3. **RF-004: Matching Engine** (depends on trips and requests)

This user management system provides the authentication foundation for all subsequent features.

---

**End of FastAPI Implementation Plan**
