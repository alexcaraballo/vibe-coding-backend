# Plan: RF-INF-001 - Gestión de Usuarios

**Issue**: #11
**Prioridad**: CRÍTICA (Base del sistema)
**Estimación**: 4-6 horas
**Dependencias**: 00-initial-structure.md (completado)

---

## Objetivo

Implementar sistema completo de gestión de usuarios con registro, autenticación JWT, perfiles y roles (conductor/pasajero/ambos), siguiendo Clean Architecture.

---

## Análisis Previo

### Arquitectura Objetivo
```
apps/users/
├── domain/
│   ├── models.py              # User (entidad pura)
│   └── repositories/
│       └── user_repository.py # IUserRepository (interface)
├── infrastructure/
│   ├── dependencies.py        # DI para repositorios
│   ├── auth/
│   │   ├── jwt.py            # Utilidades JWT
│   │   └── password.py        # Hashing de contraseñas
│   └── repositories/
│       └── user_repository.py # UserRepository (MongoDB)
└── api/
    ├── urls.py
    └── versioning/v1/
        ├── views.py           # Endpoints auth + users
        └── schemas/
            ├── requests.py    # RegisterRequest, LoginRequest, etc.
            └── responses.py   # UserResponse, TokenResponse
```

---

## Paso 1: Modelo de Dominio

**Archivo**: `apps/users/domain/models.py`

```python
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional
from enum import Enum

class UserRole(str, Enum):
    """Roles de usuario"""
    DRIVER = "driver"
    PASSENGER = "passenger"
    BOTH = "both"

class User(BaseModel):
    """
    Entidad User del dominio
    NO debe contener lógica de persistencia ni autenticación
    """
    id: Optional[str] = None
    email: EmailStr
    password_hash: str  # NUNCA password en texto plano
    name: str = Field(..., min_length=2, max_length=100)
    phone: Optional[str] = Field(None, pattern=r"^\+?[1-9]\d{1,14}$")
    role: UserRole = Field(default=UserRole.PASSENGER)

    # Metadatos
    is_active: bool = Field(default=True)
    is_verified: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    # Información adicional para conductores
    vehicle_model: Optional[str] = None
    vehicle_plate: Optional[str] = None
    license_number: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "name": "Juan Pérez",
                "phone": "+34600000000",
                "role": "passenger"
            }
        }
```

---

## Paso 2: Interface del Repositorio

**Archivo**: `apps/users/domain/repositories/user_repository.py`

```python
from abc import ABC, abstractmethod
from typing import Optional
from apps.users.domain.models import User

class IUserRepository(ABC):
    """Contrato para el repositorio de usuarios"""

    @abstractmethod
    async def create(self, user: User) -> User:
        """Crea un nuevo usuario. Retorna el usuario con id asignado."""
        pass

    @abstractmethod
    async def get_by_id(self, user_id: str) -> Optional[User]:
        """Obtiene usuario por ID"""
        pass

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        """Obtiene usuario por email (para login)"""
        pass

    @abstractmethod
    async def get_all(self, skip: int = 0, limit: int = 100) -> list[User]:
        """Lista usuarios con paginación"""
        pass

    @abstractmethod
    async def update(self, user_id: str, user: User) -> bool:
        """Actualiza usuario. Retorna True si actualizó."""
        pass

    @abstractmethod
    async def delete(self, user_id: str) -> bool:
        """Elimina usuario (soft delete recomendado)"""
        pass

    @abstractmethod
    async def email_exists(self, email: str) -> bool:
        """Verifica si email ya existe"""
        pass
```

---

## Paso 3: Implementación del Repositorio

**Archivo**: `apps/users/infrastructure/repositories/user_repository.py`

```python
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from typing import Optional
from bson import ObjectId

from apps.users.domain.models import User
from apps.users.domain.repositories.user_repository import IUserRepository

class UserRepository(IUserRepository):
    """Implementación MongoDB del repositorio de usuarios"""

    def __init__(self, db: AsyncIOMotorDatabase):
        self._collection = db["users"]

    async def create(self, user: User) -> User:
        """Crea usuario en MongoDB"""
        user_dict = user.model_dump(exclude={"id"}, mode="json")
        result = await self._collection.insert_one(user_dict)
        user.id = str(result.inserted_id)
        return user

    async def get_by_id(self, user_id: str) -> Optional[User]:
        """Obtiene por ID"""
        doc = await self._collection.find_one({"_id": ObjectId(user_id)})
        if doc:
            doc["id"] = str(doc.pop("_id"))
            return User(**doc)
        return None

    async def get_by_email(self, email: str) -> Optional[User]:
        """Obtiene por email"""
        doc = await self._collection.find_one({"email": email})
        if doc:
            doc["id"] = str(doc.pop("_id"))
            return User(**doc)
        return None

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[User]:
        """Lista usuarios"""
        cursor = self._collection.find().skip(skip).limit(limit)
        users = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            users.append(User(**doc))
        return users

    async def update(self, user_id: str, user: User) -> bool:
        """Actualiza usuario"""
        user.updated_at = datetime.utcnow()
        update_dict = user.model_dump(exclude={"id", "created_at"}, mode="json")

        result = await self._collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_dict}
        )
        return result.modified_count > 0

    async def delete(self, user_id: str) -> bool:
        """Soft delete (marca como inactivo)"""
        result = await self._collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
        )
        return result.modified_count > 0

    async def email_exists(self, email: str) -> bool:
        """Verifica si email existe"""
        count = await self._collection.count_documents({"email": email})
        return count > 0
```

---

## Paso 4: Utilidades de Autenticación

**Archivo**: `apps/users/infrastructure/auth/password.py`

```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hashea contraseña con bcrypt"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica contraseña"""
    return pwd_context.verify(plain_password, hashed_password)
```

**Archivo**: `apps/users/infrastructure/auth/jwt.py`

```python
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt

from config.settings import settings

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Crea JWT token"""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    """Decodifica JWT token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None
```

---

## Paso 5: Dependency Injection

**Archivo**: `apps/users/infrastructure/dependencies.py`

```python
from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from motor.motor_asyncio import AsyncIOMotorDatabase

from config.database import get_database
from apps.users.domain.repositories.user_repository import IUserRepository
from apps.users.infrastructure.repositories.user_repository import UserRepository
from apps.users.infrastructure.auth.jwt import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_user_repository(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)]
) -> IUserRepository:
    """Inyecta repositorio de usuarios"""
    return UserRepository(db)

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    repo: Annotated[IUserRepository, Depends(get_user_repository)]
):
    """Obtiene usuario actual desde JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user = await repo.get_by_id(user_id)
    if user is None:
        raise credentials_exception

    return user
```

---

## Paso 6: DTOs (Schemas)

**Archivo**: `apps/users/api/versioning/v1/schemas/requests.py`

```python
from pydantic import BaseModel, EmailStr, Field
from apps.users.domain.models import UserRole

class RegisterRequest(BaseModel):
    """Schema para registro de usuario"""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., pattern=r"^\+?[1-9]\d{1,14}$")
    role: UserRole = Field(default=UserRole.PASSENGER)

class LoginRequest(BaseModel):
    """Schema para login"""
    email: EmailStr
    password: str

class UpdateProfileRequest(BaseModel):
    """Schema para actualizar perfil"""
    name: str | None = Field(None, min_length=2, max_length=100)
    phone: str | None = Field(None, pattern=r"^\+?[1-9]\d{1,14}$")
    vehicle_model: str | None = None
    vehicle_plate: str | None = None
    license_number: str | None = None
```

**Archivo**: `apps/users/api/versioning/v1/schemas/responses.py`

```python
from pydantic import BaseModel, EmailStr
from datetime import datetime
from apps.users.domain.models import UserRole

class UserResponse(BaseModel):
    """Schema de respuesta de usuario"""
    id: str
    email: EmailStr
    name: str
    phone: str | None
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime

    # Info conductor (si aplica)
    vehicle_model: str | None = None
    vehicle_plate: str | None = None
    license_number: str | None = None

class TokenResponse(BaseModel):
    """Schema de respuesta de autenticación"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
```

---

## Paso 7: Endpoints (Views)

**Archivo**: `apps/users/api/versioning/v1/views.py`

```python
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from apps.users.domain.models import User
from apps.users.domain.repositories.user_repository import IUserRepository
from apps.users.infrastructure.dependencies import get_user_repository, get_current_user
from apps.users.infrastructure.auth.password import hash_password, verify_password
from apps.users.infrastructure.auth.jwt import create_access_token
from apps.users.api.versioning.v1.schemas.requests import RegisterRequest, UpdateProfileRequest
from apps.users.api.versioning.v1.schemas.responses import UserResponse, TokenResponse

router = APIRouter()

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    repo: Annotated[IUserRepository, Depends(get_user_repository)]
):
    """Registrar nuevo usuario"""

    # Verificar si email ya existe
    if await repo.email_exists(payload.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Crear usuario
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        name=payload.name,
        phone=payload.phone,
        role=payload.role
    )

    created_user = await repo.create(user)

    # Generar token
    access_token = create_access_token(data={"sub": created_user.id})

    return TokenResponse(
        access_token=access_token,
        user=UserResponse(**created_user.model_dump())
    )

@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    repo: Annotated[IUserRepository, Depends(get_user_repository)]
):
    """Iniciar sesión"""

    # Buscar usuario por email
    user = await repo.get_by_email(form_data.username)  # OAuth2 usa 'username'

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    # Generar token
    access_token = create_access_token(data={"sub": user.id})

    return TokenResponse(
        access_token=access_token,
        user=UserResponse(**user.model_dump())
    )

@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: Annotated[User, Depends(get_current_user)]
):
    """Obtener perfil del usuario actual"""
    return UserResponse(**current_user.model_dump())

@router.put("/me", response_model=UserResponse)
async def update_current_user_profile(
    payload: UpdateProfileRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    repo: Annotated[IUserRepository, Depends(get_user_repository)]
):
    """Actualizar perfil del usuario actual"""

    # Actualizar solo campos proporcionados
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

    success = await repo.update(current_user.id, current_user)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile"
        )

    return UserResponse(**current_user.model_dump())

@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: str,
    repo: Annotated[IUserRepository, Depends(get_user_repository)],
    _: Annotated[User, Depends(get_current_user)]  # Requiere auth
):
    """Obtener perfil público de otro usuario"""
    user = await repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return UserResponse(**user.model_dump())
```

---

## Paso 8: Registrar Router

**Archivo**: `apps/users/api/urls.py`

```python
from fastapi import APIRouter
from apps.users.api.versioning.v1.views import router as v1_router

router = APIRouter()
router.include_router(v1_router, prefix="/v1", tags=["Users & Auth"])
```

**Actualizar**: `main.py`

```python
from apps.users.api.urls import router as users_router

# En la sección de routers
app.include_router(users_router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(users_router, prefix="/api/v1/users", tags=["Users"])
```

---

## Paso 9: Testing

**Archivo**: `tests/test_users/test_auth.py`

```python
import pytest
from httpx import AsyncClient
from main import app

@pytest.mark.asyncio
async def test_register_success():
    """Test registro exitoso"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/auth/v1/register",
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
    assert data["user"]["email"] == "test@example.com"

@pytest.mark.asyncio
async def test_register_duplicate_email():
    """Test registro con email duplicado"""
    # Crear primer usuario
    async with AsyncClient(app=app, base_url="http://test") as ac:
        await ac.post(
            "/api/v1/auth/v1/register",
            json={
                "email": "duplicate@example.com",
                "password": "password123",
                "name": "User 1",
                "phone": "+34600000001"
            }
        )

        # Intentar crear segundo usuario con mismo email
        response = await ac.post(
            "/api/v1/auth/v1/register",
            json={
                "email": "duplicate@example.com",
                "password": "password456",
                "name": "User 2",
                "phone": "+34600000002"
            }
        )

    assert response.status_code == 400
    assert "already registered" in response.json()["detail"].lower()
```

---

## Checklist de Implementación

- [ ] Modelo User en domain/models.py
- [ ] Interface IUserRepository en domain/repositories/
- [ ] Implementación UserRepository en infrastructure/repositories/
- [ ] Utilidades password.py y jwt.py
- [ ] Dependency injection en infrastructure/dependencies.py
- [ ] Schemas de request/response
- [ ] Endpoints en api/versioning/v1/views.py:
  - [ ] POST /register
  - [ ] POST /login
  - [ ] GET /me
  - [ ] PUT /me
  - [ ] GET /{user_id}
- [ ] Router registrado en main.py
- [ ] Tests unitarios (registro, login, perfil)
- [ ] Verificar en /docs (Swagger)
- [ ] Crear índice único en email en MongoDB

---

## Verificación

```bash
# Iniciar servidor
poetry run python main.py

# Probar endpoints
curl -X POST http://localhost:8000/api/v1/auth/v1/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123","name":"Test User","phone":"+34600000000"}'

# Ver documentación
open http://localhost:8000/docs
```

---

## Próximo Paso

Una vez completado RF-INF-001, proceder con:
- **RF-001**: Publicación de Trayectos (requiere autenticación)
