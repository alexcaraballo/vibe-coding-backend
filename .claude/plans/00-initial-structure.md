# Plan: Estructura Inicial del Proyecto - Sistema de Carpooling

**Prioridad**: CRÍTICA - Debe ejecutarse PRIMERO
**Estimación**: 2-3 horas
**Dependencias**: Ninguna

---

## Objetivo

Crear la estructura base del proyecto siguiendo Clean Architecture (Hexagonal Architecture) para el sistema de carpooling, estableciendo las carpetas, configuración inicial y módulos necesarios para soportar todos los requisitos funcionales.

---

## Estructura de Directorio Propuesta

```
vibe-coding-backend/
├── apps/
│   ├── users/                      # Módulo de Usuarios (RF-INF-001)
│   │   ├── __init__.py
│   │   ├── domain/
│   │   │   ├── __init__.py
│   │   │   ├── models.py          # User, Driver, Passenger
│   │   │   └── repositories/
│   │   │       ├── __init__.py
│   │   │       └── user_repository.py
│   │   ├── infrastructure/
│   │   │   ├── __init__.py
│   │   │   ├── dependencies.py
│   │   │   └── repositories/
│   │   │       ├── __init__.py
│   │   │       └── user_repository.py
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
│   ├── trips/                      # Módulo de Trayectos (RF-001, RF-002, RF-003)
│   │   ├── __init__.py
│   │   ├── domain/
│   │   │   ├── __init__.py
│   │   │   ├── models.py          # Trip, Booking, TravelRequest
│   │   │   └── repositories/
│   │   │       ├── __init__.py
│   │   │       ├── trip_repository.py
│   │   │       ├── booking_repository.py
│   │   │       └── travel_request_repository.py
│   │   ├── infrastructure/
│   │   │   ├── __init__.py
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
│   ├── matching/                   # Módulo de Matching (RF-006)
│   │   ├── __init__.py
│   │   ├── domain/
│   │   │   ├── __init__.py
│   │   │   ├── models.py          # MatchResult, MatchScore
│   │   │   └── services/
│   │   │       ├── __init__.py
│   │   │       └── matching_service.py  # IMatchingService
│   │   ├── infrastructure/
│   │   │   ├── __init__.py
│   │   │   ├── dependencies.py
│   │   │   └── services/
│   │   │       ├── __init__.py
│   │   │       ├── matching_service.py
│   │   │       └── geocoding_service.py
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
│   └── maps/                       # Módulo de Mapas (RF-005)
│       ├── __init__.py
│       ├── domain/
│       │   ├── __init__.py
│       │   ├── models.py          # Route, Coordinates
│       │   └── services/
│       │       ├── __init__.py
│       │       └── map_service.py
│       ├── infrastructure/
│       │   ├── __init__.py
│       │   ├── dependencies.py
│       │   └── services/
│       │       ├── __init__.py
│       │       └── map_service.py
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
│   ├── settings.py                # Configuración global
│   └── database.py                # Configuración de BD
│
├── shared/                        # Código compartido
│   ├── __init__.py
│   ├── exceptions.py              # Excepciones custom
│   ├── validators.py              # Validadores comunes
│   └── utils.py                   # Utilidades
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_users/
│   ├── test_trips/
│   ├── test_matching/
│   └── test_maps/
│
├── main.py                        # Entry point de FastAPI
├── manage.py                      # Script de gestión (opcional)
├── pyproject.toml                 # Dependencias (Poetry)
├── .env.example                   # Variables de entorno ejemplo
├── .env                           # Variables de entorno (no en git)
├── README.md
└── .gitignore
```

---

## Pasos de Implementación

### Fase 1: Configuración Base

#### 1.1. Crear estructura de carpetas

```bash
# Apps principales
mkdir -p apps/{users,trips,matching,maps}

# Estructura por app (ejemplo con users)
for app in users trips matching maps; do
    mkdir -p apps/$app/{domain/{models,repositories,services},infrastructure/{repositories,services},api/versioning/v1/schemas}
    touch apps/$app/__init__.py
    touch apps/$app/domain/__init__.py
    touch apps/$app/domain/repositories/__init__.py
    touch apps/$app/infrastructure/__init__.py
    touch apps/$app/infrastructure/repositories/__init__.py
    touch apps/$app/api/__init__.py
    touch apps/$app/api/versioning/__init__.py
    touch apps/$app/api/versioning/v1/__init__.py
    touch apps/$app/api/versioning/v1/schemas/__init__.py
done

# Config y shared
mkdir -p config shared tests
touch config/__init__.py
touch shared/__init__.py
touch tests/__init__.py
```

#### 1.2. Configurar dependencias (pyproject.toml)

```toml
[tool.poetry]
name = "vibe-coding-backend"
version = "0.1.0"
description = "Sistema de Carpooling - MVP Hackathon"
authors = ["Team <team@example.com>"]

[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.109.0"
uvicorn = {extras = ["standard"], version = "^0.27.0"}
pydantic = "^2.5.0"
pydantic-settings = "^2.1.0"
motor = "^3.3.2"              # MongoDB async driver
pymongo = "^4.6.1"            # MongoDB sync (para scripts)
python-dotenv = "^1.0.0"
python-jose = {extras = ["cryptography"], version = "^3.3.0"}  # JWT
passlib = {extras = ["bcrypt"], version = "^1.7.4"}  # Password hashing
python-multipart = "^0.0.6"   # Form data
httpx = "^0.26.0"             # HTTP client para testing

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.3"
pytest-asyncio = "^0.21.1"
pytest-cov = "^4.1.0"
ruff = "^0.1.9"
mypy = "^1.8.0"
black = "^23.12.1"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

Ejecutar:
```bash
poetry install
```

#### 1.3. Configurar settings (config/settings.py)

```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    """Configuración global de la aplicación"""

    # App
    APP_NAME: str = "Vibe Coding Carpooling API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # Database
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "carpooling_db"

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

#### 1.4. Configurar database (config/database.py)

```python
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from config.settings import settings

class Database:
    """Singleton para conexión a MongoDB"""

    client: AsyncIOMotorClient = None

    @classmethod
    def get_client(cls) -> AsyncIOMotorClient:
        if cls.client is None:
            cls.client = AsyncIOMotorClient(settings.MONGODB_URL)
        return cls.client

    @classmethod
    def get_database(cls) -> AsyncIOMotorDatabase:
        client = cls.get_client()
        return client[settings.MONGODB_DB_NAME]

    @classmethod
    async def close(cls):
        if cls.client is not None:
            cls.client.close()
            cls.client = None

async def get_database() -> AsyncIOMotorDatabase:
    """Dependency para FastAPI"""
    return Database.get_database()
```

#### 1.5. Crear main.py (Entry Point)

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from config.settings import settings
from config.database import Database

# Importar routers (se agregarán gradualmente)
# from apps.users.api.urls import router as users_router
# from apps.trips.api.urls import router as trips_router
# from apps.matching.api.urls import router as matching_router
# from apps.maps.api.urls import router as maps_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events"""
    # Startup
    print("🚀 Starting application...")
    # Inicializar DB si es necesario
    yield
    # Shutdown
    print("👋 Shutting down application...")
    await Database.close()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION
    }

# Routers (descomentar a medida que se implementan)
# app.include_router(users_router, prefix="/api/v1/users", tags=["Users"])
# app.include_router(trips_router, prefix="/api/v1/trips", tags=["Trips"])
# app.include_router(matching_router, prefix="/api/v1/matching", tags=["Matching"])
# app.include_router(maps_router, prefix="/api/v1/maps", tags=["Maps"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
```

#### 1.6. Crear .env.example

```bash
# Application
APP_NAME="Vibe Coding Carpooling API"
DEBUG=True

# Database
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=carpooling_db

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

#### 1.7. Crear shared/exceptions.py

```python
"""Excepciones custom del dominio"""

class DomainException(Exception):
    """Excepción base del dominio"""
    def __init__(self, message: str, code: str = "DOMAIN_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)

class EntityNotFound(DomainException):
    """Entidad no encontrada"""
    def __init__(self, entity_type: str, entity_id: str):
        super().__init__(
            message=f"{entity_type} with id '{entity_id}' not found",
            code="ENTITY_NOT_FOUND"
        )

class ValidationError(DomainException):
    """Error de validación de negocio"""
    def __init__(self, message: str):
        super().__init__(message=message, code="VALIDATION_ERROR")

class InsufficientSeats(DomainException):
    """No hay plazas disponibles"""
    def __init__(self):
        super().__init__(
            message="No hay plazas disponibles en este trayecto",
            code="INSUFFICIENT_SEATS"
        )

class MaxDetourExceeded(DomainException):
    """Desvío máximo excedido"""
    def __init__(self, current: int, additional: int, max_allowed: int):
        super().__init__(
            message=f"Desvío excedido: {current + additional} > {max_allowed} minutos",
            code="MAX_DETOUR_EXCEEDED"
        )
```

#### 1.8. Configurar tests (tests/conftest.py)

```python
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from motor.motor_asyncio import AsyncIOMotorClient

from main import app
from config.settings import settings

@pytest.fixture
def client():
    """Cliente de pruebas de FastAPI"""
    return TestClient(app)

@pytest_asyncio.fixture
async def test_db():
    """Base de datos de pruebas"""
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[f"{settings.MONGODB_DB_NAME}_test"]

    yield db

    # Cleanup
    await client.drop_database(f"{settings.MONGODB_DB_NAME}_test")
    client.close()
```

---

### Fase 2: Verificación

#### 2.1. Verificar estructura

```bash
tree -L 4 -I '__pycache__|*.pyc' apps/
```

#### 2.2. Verificar dependencias

```bash
poetry install
poetry run python --version
```

#### 2.3. Iniciar servidor

```bash
poetry run python main.py
```

Verificar:
- http://localhost:8000/health
- http://localhost:8000/docs (Swagger UI)

#### 2.4. Ejecutar tests base

```bash
poetry run pytest tests/ -v
```

---

## Checklist de Finalización

- [ ] Estructura de carpetas creada para todos los módulos
- [ ] pyproject.toml configurado con todas las dependencias
- [ ] config/settings.py con todas las variables de entorno
- [ ] config/database.py con conexión a MongoDB
- [ ] main.py con FastAPI app funcional
- [ ] .env.example creado
- [ ] shared/exceptions.py con excepciones del dominio
- [ ] tests/conftest.py configurado
- [ ] Servidor arranca correctamente en http://localhost:8000
- [ ] /health endpoint responde correctamente
- [ ] /docs muestra Swagger UI
- [ ] Poetry install exitoso

---

## Siguientes Pasos

Una vez completada la estructura inicial, proceder con los planes en este orden:

1. **RF-INF-001**: Gestión de Usuarios (base para autenticación)
2. **RF-001**: Publicación de Trayectos
3. **RF-002**: Búsqueda de Trayectos
4. **RF-INF-002**: Validación de Disponibilidad
5. **RF-INF-004**: Gestión de Plazas
6. **RF-003**: Reserva de Trayectos
7. **RF-004**: Listado de Reservas
8. **RF-INF-003**: Cancelación de Reservas
9. **RF-006**: Motor de Matching Avanzado
10. **RF-005**: Visualización en Mapas
11. Bonus features (si hay tiempo)

---

## Notas Importantes

- ⚠️ MongoDB debe estar corriendo localmente o configurar URL remota
- ⚠️ No pushear .env al repositorio (ya está en .gitignore)
- ⚠️ SECRET_KEY debe ser diferente en producción
- ⚠️ Cada módulo (users, trips, matching, maps) es independiente
- ⚠️ Seguir siempre Clean Architecture: Domain → Infrastructure → API
