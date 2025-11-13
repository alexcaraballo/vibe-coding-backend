# Agente de Desarrollo: Clean Architecture / Hexagonal Architecture

## Contexto

Este documento define cómo trabajar en proyectos que siguen **Clean Architecture** (también conocida como Hexagonal Architecture o Ports & Adapters). Esta arquitectura separa las preocupaciones en capas bien definidas para mantener el código mantenible, testeable y desacoplado.

## Estructura de Capas

```
apps/
  └── [app_name]/
      ├── domain/              # Capa de Dominio (núcleo del negocio)
      │   ├── models.py        # Entidades del dominio (Pydantic/dataclasses)
      │   └── repositories/    # Interfaces (contratos)
      │       └── *_repository.py
      │
      ├── infrastructure/      # Capa de Infraestructura (implementaciones)
      │   ├── dependencies.py  # Inyección de dependencias
      │   └── repositories/    # Implementaciones concretas (MongoDB, PostgreSQL, etc.)
      │       └── *_repository.py
      │
      └── api/                 # Capa de Presentación (HTTP/REST)
          ├── urls.py          # Registro de routers
          └── versioning/
              └── v1/
                  ├── views.py      # Endpoints (controladores)
                  └── schemas/
                      ├── requests.py   # DTOs de entrada
                      └── response.py   # DTOs de salida
```

## Principios de Clean Architecture

### 1. Dirección de Dependencias

**REGLA DE ORO**: Las dependencias siempre apuntan hacia adentro (hacia el dominio).

```
API Layer → Infrastructure Layer → Domain Layer
  (usa)          (implementa)         (define)
```

- **Domain**: NO debe depender de nada externo (ni FastAPI, ni MongoDB, ni requests)
- **Infrastructure**: Depende del Domain (implementa sus interfaces)
- **API**: Depende del Domain (usa sus interfaces) y de Infrastructure (vía dependency injection)

### 2. Separación de Responsabilidades

- **Domain/models.py**: Entidades puras del negocio
- **Domain/repositories/**: Contratos (interfaces abstractas)
- **Infrastructure/repositories/**: Implementaciones concretas (acceso a BD)
- **API/schemas/**: DTOs para entrada/salida HTTP
- **API/views.py**: Orquestación de casos de uso

---

## Flujo de Trabajo para Nuevas Funcionalidades

### Paso 1: Analizar Arquitectura Existente

Antes de empezar, **SIEMPRE** analizar:

```bash
# Verificar estructura del proyecto
tree -L 3 -I '__pycache__|*.pyc' apps/

# Leer archivos clave
- domain/models.py          # Entidades existentes
- domain/repositories/      # Interfaces existentes
- infrastructure/repositories/  # Implementaciones
- api/versioning/v1/views.py   # Endpoints actuales
- config/settings.py        # Configuración
```

**Preguntas a responder:**
- ¿Qué modelos de dominio existen?
- ¿Qué repositorios están definidos?
- ¿Qué base de datos se usa? (MongoDB, PostgreSQL, etc.)
- ¿Qué versión de API está activa?
- ¿Hay autenticación/autorización?

### Paso 2: Diseñar Modelo de Dominio

**Modificar: `domain/models.py`**

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class MiEntidad(BaseModel):
    """
    Entidad del dominio - NO debe tener lógica de persistencia
    """
    id: Optional[str] = None
    nombre: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    is_active: bool = Field(default=True)
```

**Buenas prácticas:**
- Usar Pydantic BaseModel para validación automática
- Incluir docstrings descriptivos
- Valores por defecto con `Field(default=...)` o `Field(default_factory=...)`
- Tipos explícitos con anotaciones
- NO importar nada de FastAPI, motor, pymongo aquí

### Paso 3: Definir Interface del Repositorio

**Modificar: `domain/repositories/mi_repository.py`**

```python
from abc import ABC, abstractmethod
from typing import Optional
from apps.mi_app.domain.models import MiEntidad

class IMiRepositorio(ABC):
    """
    Contrato para el repositorio - Define QUÉ se puede hacer
    """

    @abstractmethod
    async def create(self, entidad: MiEntidad) -> None:
        """Crea una nueva entidad."""
        pass

    @abstractmethod
    async def get_by_id(self, id: str) -> Optional[MiEntidad]:
        """Obtiene una entidad por ID."""
        pass

    @abstractmethod
    async def get_all(self, skip: int = 0, limit: int = 100) -> list[MiEntidad]:
        """Lista todas las entidades con paginación."""
        pass

    @abstractmethod
    async def update(self, id: str, entidad: MiEntidad) -> bool:
        """Actualiza una entidad. Retorna True si se actualizó."""
        pass

    @abstractmethod
    async def delete(self, id: str) -> bool:
        """Elimina una entidad. Retorna True si se eliminó."""
        pass
```

**Buenas prácticas:**
- Heredar de `ABC` (Abstract Base Class)
- Todos los métodos con `@abstractmethod`
- Documentar comportamiento esperado
- Usar tipos del dominio (nunca tipos de DB como `Document`, etc.)
- Métodos async si el proyecto usa async

### Paso 4: Implementar Repositorio

**Modificar: `infrastructure/repositories/mi_repository.py`**

```python
import motor.motor_asyncio
from datetime import datetime
from apps.mi_app.domain.models import MiEntidad
from apps.mi_app.domain.repositories.mi_repository import IMiRepositorio
from config.conf import settings

class MiRepositorio(IMiRepositorio):
    """
    Implementación concreta para MongoDB
    """

    def __init__(self, db: motor.motor_asyncio.AsyncIOMotorDatabase):
        """
        Recibe la conexión a la BD vía dependency injection
        """
        self._collection = db[settings.COLLECTION_NAME]

    async def create(self, entidad: MiEntidad) -> None:
        """Implementación del create"""
        await self._collection.insert_one(entidad.model_dump(mode="json"))

    async def get_by_id(self, id: str) -> Optional[MiEntidad]:
        """Implementación del get_by_id"""
        doc = await self._collection.find_one({"_id": id})
        if doc:
            return MiEntidad(**doc)
        return None

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[MiEntidad]:
        """Implementación del get_all con paginación"""
        cursor = self._collection.find().skip(skip).limit(limit)
        docs = await cursor.to_list(length=limit)
        return [MiEntidad(**doc) for doc in docs]

    async def update(self, id: str, entidad: MiEntidad) -> bool:
        """Implementación del update"""
        entidad.updated_at = datetime.utcnow()
        result = await self._collection.update_one(
            {"_id": id},
            {"$set": entidad.model_dump(mode="json", exclude={"_id"})}
        )
        return result.modified_count > 0

    async def delete(self, id: str) -> bool:
        """Implementación del delete"""
        result = await self._collection.delete_one({"_id": id})
        return result.deleted_count > 0
```

**Buenas prácticas:**
- Implementar TODOS los métodos de la interface
- Usar tipos del dominio en firmas
- Convertir entre tipos de DB y dominio en los bordes
- Manejar casos None/null apropiadamente
- NO lanzar excepciones de DB, convertirlas a excepciones de dominio si es necesario

### Paso 5: Configurar Dependency Injection

**Modificar: `infrastructure/dependencies.py`**

```python
from typing import Annotated
from fastapi import Depends
from celering_fastapi.handlers.database import get_database
from motor.motor_asyncio import AsyncIOMotorDatabase

from apps.mi_app.domain.repositories.mi_repository import IMiRepositorio
from apps.mi_app.infrastructure.repositories.mi_repository import MiRepositorio

async def get_mi_repositorio(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)]
) -> IMiRepositorio:
    """
    Inyección de dependencia del repositorio
    """
    return MiRepositorio(db)
```

**Buenas prácticas:**
- Retornar el tipo de la interface (no la implementación concreta)
- Usar `Annotated` con `Depends` para inyección
- Una función por repositorio

### Paso 6: Definir DTOs (Request/Response Schemas)

**Modificar: `api/versioning/v1/schemas/requests.py`**

```python
from typing import Optional
from pydantic import BaseModel, HttpUrl, Field

class MiEntidadCreate(BaseModel):
    """Schema para crear entidad vía API"""
    nombre: str = Field(..., min_length=3, max_length=100)
    descripcion: Optional[str] = None

class MiEntidadUpdate(BaseModel):
    """Schema para actualizar entidad vía API"""
    nombre: Optional[str] = Field(None, min_length=3, max_length=100)
    descripcion: Optional[str] = None
    is_active: Optional[bool] = None
```

**Modificar: `api/versioning/v1/schemas/response.py`**

```python
from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class MiEntidadResponse(BaseModel):
    """Schema de respuesta con información completa"""
    id: str
    nombre: str
    descripcion: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    is_active: bool
```

**Buenas prácticas:**
- Separar schemas de request y response
- Usar validaciones de Pydantic (min_length, max_length, regex, etc.)
- Request schemas: campos opcionales con `Optional`
- Response schemas: todos los campos que el cliente necesita
- NO reusar modelos de dominio directamente en APIs

### Paso 7: Implementar Endpoints (Views)

**Modificar: `api/versioning/v1/views.py`**

```python
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, status

from apps.mi_app.api.versioning.v1.schemas.requests import MiEntidadCreate, MiEntidadUpdate
from apps.mi_app.api.versioning.v1.schemas.response import MiEntidadResponse
from apps.mi_app.domain.models import MiEntidad
from apps.mi_app.domain.repositories.mi_repository import IMiRepositorio
from apps.mi_app.infrastructure.dependencies import get_mi_repositorio

router = APIRouter()

@router.post("/", response_model=MiEntidadResponse, status_code=status.HTTP_201_CREATED)
async def create_entidad(
    payload: MiEntidadCreate,
    repo: Annotated[IMiRepositorio, Depends(get_mi_repositorio)]
):
    """
    Crear nueva entidad.

    - Valida datos de entrada
    - Crea la entidad en la base de datos
    """
    entidad = MiEntidad(
        nombre=payload.nombre,
        descripcion=payload.descripcion
    )
    await repo.create(entidad)

    return MiEntidadResponse(
        id=entidad.id,
        nombre=entidad.nombre,
        descripcion=entidad.descripcion,
        created_at=entidad.created_at,
        updated_at=entidad.updated_at,
        is_active=entidad.is_active
    )

@router.get("/{id}", response_model=MiEntidadResponse)
async def get_entidad(
    id: str,
    repo: Annotated[IMiRepositorio, Depends(get_mi_repositorio)]
):
    """
    Obtener entidad por ID.
    """
    entidad = await repo.get_by_id(id)
    if not entidad:
        raise HTTPException(status_code=404, detail="Entidad no encontrada")

    return MiEntidadResponse(
        id=entidad.id,
        nombre=entidad.nombre,
        descripcion=entidad.descripcion,
        created_at=entidad.created_at,
        updated_at=entidad.updated_at,
        is_active=entidad.is_active
    )

@router.get("/", response_model=list[MiEntidadResponse])
async def list_entidades(
    repo: Annotated[IMiRepositorio, Depends(get_mi_repositorio)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500)
):
    """
    Listar entidades con paginación.
    """
    entidades = await repo.get_all(skip=skip, limit=limit)

    return [
        MiEntidadResponse(
            id=e.id,
            nombre=e.nombre,
            descripcion=e.descripcion,
            created_at=e.created_at,
            updated_at=e.updated_at,
            is_active=e.is_active
        )
        for e in entidades
    ]

@router.put("/{id}", response_model=MiEntidadResponse)
async def update_entidad(
    id: str,
    payload: MiEntidadUpdate,
    repo: Annotated[IMiRepositorio, Depends(get_mi_repositorio)]
):
    """
    Actualizar entidad existente.

    - Soporta actualización parcial
    """
    entidad = await repo.get_by_id(id)
    if not entidad:
        raise HTTPException(status_code=404, detail="Entidad no encontrada")

    # Actualizar solo campos proporcionados
    if payload.nombre is not None:
        entidad.nombre = payload.nombre
    if payload.descripcion is not None:
        entidad.descripcion = payload.descripcion
    if payload.is_active is not None:
        entidad.is_active = payload.is_active

    success = await repo.update(id, entidad)
    if not success:
        raise HTTPException(status_code=500, detail="Error al actualizar")

    return MiEntidadResponse(
        id=entidad.id,
        nombre=entidad.nombre,
        descripcion=entidad.descripcion,
        created_at=entidad.created_at,
        updated_at=entidad.updated_at,
        is_active=entidad.is_active
    )

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entidad(
    id: str,
    repo: Annotated[IMiRepositorio, Depends(get_mi_repositorio)]
):
    """
    Eliminar entidad permanentemente.
    """
    success = await repo.delete(id)
    if not success:
        raise HTTPException(status_code=404, detail="Entidad no encontrada")

    return None
```

**Buenas prácticas:**
- **IMPORTANTE**: Parámetros sin default ANTES que parámetros con default
  - ✅ `func(repo: Dep, skip: int = 0)`
  - ❌ `func(skip: int = 0, repo: Dep)` → SyntaxError
- Inyectar repositorio usando `Annotated[Interface, Depends(...)]`
- Docstrings descriptivos (se muestran en Swagger)
- Validar existencia antes de operar
- Códigos HTTP semánticos (201, 204, 404, etc.)
- Convertir entre DTOs y modelos de dominio
- Manejo de errores con HTTPException

### Paso 8: Registrar Router

**Modificar: `api/urls.py`**

```python
from fastapi import APIRouter
from apps.mi_app.api.versioning.v1.views import router as v1_router

router = APIRouter()
router.include_router(v1_router, prefix="/v1", tags=["Mi App"])
```

---

## Testing

### Estructura de Tests

```python
"""
tests/test_mi_feature.py
"""
from unittest.mock import AsyncMock, MagicMock
import pytest
from fastapi.testclient import TestClient

from apps.mi_app.domain.models import MiEntidad
from apps.mi_app.infrastructure.dependencies import get_mi_repositorio

@pytest.fixture
def mock_repositorio():
    """Mock del repositorio"""
    repo = MagicMock()
    repo.create = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.get_all = AsyncMock()
    repo.update = AsyncMock()
    repo.delete = AsyncMock()
    return repo

@pytest.fixture
def client(app, mock_repositorio):
    """Cliente de test con mocks"""
    app.dependency_overrides[get_mi_repositorio] = lambda: mock_repositorio
    return TestClient(app)

class TestCreateEndpoint:
    """Tests para POST /"""

    def test_create_success(self, client, mock_repositorio):
        """Test creación exitosa"""
        mock_repositorio.create.return_value = None

        response = client.post(
            "/celering/baas/mi_app/api/v1/",
            json={"nombre": "Test"}
        )

        assert response.status_code == 201
        assert "id" in response.json()
        mock_repositorio.create.assert_called_once()
```

**Buenas prácticas:**
- Mockear repositorios, no la base de datos
- Tests por clase/endpoint
- Nombres descriptivos: `test_<accion>_<escenario>`
- Verificar tanto respuesta como llamadas a mocks

---

## Checklist de Desarrollo

Usar este checklist para cada nueva funcionalidad:

- [ ] **Analizar** estructura existente del proyecto
- [ ] **Diseñar** modelo de dominio (`domain/models.py`)
- [ ] **Definir** interface de repositorio (`domain/repositories/`)
- [ ] **Implementar** repositorio concreto (`infrastructure/repositories/`)
- [ ] **Configurar** dependency injection (`infrastructure/dependencies.py`)
- [ ] **Crear** DTOs de request/response (`api/.../schemas/`)
- [ ] **Implementar** endpoints (`api/.../views.py`)
  - ⚠️ Parámetros sin default ANTES de parámetros con default
- [ ] **Registrar** router (`api/urls.py`)
- [ ] **Validar** con linters (ruff, pylint, mypy)
- [ ] **Escribir** tests unitarios (`tests/`)
- [ ] **Documentar** API (docstrings + README/docs)
- [ ] **Actualizar** configuración si es necesario (`config/settings.py`)

---

## Errores Comunes a Evitar

### ❌ ERROR 1: Dependencias invertidas

```python
# MAL - Domain importa de Infrastructure
# domain/models.py
from pymongo import MongoClient  # ❌ NUNCA

# BIEN - Domain no importa nada externo
# domain/models.py
from pydantic import BaseModel  # ✅
```

### ❌ ERROR 2: Lógica de negocio en la API

```python
# MAL - Lógica en el endpoint
@router.post("/")
async def create(payload: Data):
    if payload.price < 0:  # ❌ Validación de negocio aquí
        raise HTTPException(400)

# BIEN - Validación en el modelo de dominio
class Product(BaseModel):
    price: float = Field(gt=0)  # ✅
```

### ❌ ERROR 3: Orden incorrecto de parámetros

```python
# MAL - Default antes de no-default
async def list_items(
    skip: int = 0,  # ❌ Default primero
    repo: Annotated[Repo, Depends(get_repo)]  # ❌ Sin default después
):
    pass

# BIEN - No-default primero
async def list_items(
    repo: Annotated[Repo, Depends(get_repo)],  # ✅
    skip: int = 0  # ✅
):
    pass
```

### ❌ ERROR 4: Exponer modelos de dominio directamente

```python
# MAL - Modelo de dominio como response
@router.get("/", response_model=URL)  # ❌

# BIEN - DTO específico para API
@router.get("/", response_model=URLResponse)  # ✅
```

### ❌ ERROR 5: No usar interfaces

```python
# MAL - Depender de implementación concreta
def __init__(self, repo: MongoURLRepository):  # ❌
    pass

# BIEN - Depender de abstracción
def __init__(self, repo: IURLRepository):  # ✅
    pass
```

---

## Comandos Útiles

```bash
# Estructura del proyecto
tree -L 4 -I '__pycache__|*.pyc' apps/

# Buscar modelos
grep -r "class.*BaseModel" apps/*/domain/

# Buscar repositorios
find apps/ -name "*repository.py" -type f

# Buscar endpoints
grep -r "@router\." apps/*/api/

# Ejecutar tests
poetry run pytest tests/ -v

# Linters
poetry run ruff check apps/
poetry run mypy apps/

# Ejecutar servidor
poetry run python manage.py runserver
```

---

## Referencias y Recursos

- **Clean Architecture** (Robert C. Martin): https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html
- **Hexagonal Architecture**: https://alistair.cockburn.us/hexagonal-architecture/
- **FastAPI Best Practices**: https://fastapi.tiangolo.com/tutorial/bigger-applications/
- **Dependency Injection Pattern**: https://fastapi.tiangolo.com/tutorial/dependencies/

---

## Plantilla de Prompt para Claude

Cuando solicites ayuda en un proyecto con Clean Architecture, usa este prompt:

```
Estoy trabajando en un proyecto Python con Clean Architecture/Hexagonal Architecture.

Estructura:
- Domain: Modelos y interfaces (no depende de nada externo)
- Infrastructure: Implementaciones concretas (MongoDB/PostgreSQL)
- API: Endpoints REST con FastAPI

Necesito implementar: [DESCRIPCIÓN DE LA FUNCIONALIDAD]

Por favor:
1. Analiza la arquitectura existente primero
2. Sigue el flujo: Domain → Infrastructure → API
3. Mantén las capas desacopladas
4. Usa dependency injection para repositorios
5. Crea DTOs separados para request/response
6. Incluye validaciones en schemas
7. Escribe tests con mocks de repositorios
8. Documenta con docstrings para Swagger

Archivos clave:
- apps/[app]/domain/models.py
- apps/[app]/domain/repositories/
- apps/[app]/infrastructure/repositories/
- apps/[app]/api/versioning/v1/views.py
```

---

## Versión

- **Versión**: 1.0
- **Última actualización**: 2025-11-07
- **Autor**: Celering Development Team
