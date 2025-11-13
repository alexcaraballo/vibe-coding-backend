# Cómo Usar Este Prompt

## INSTRUCCIONES SIMPLES

Cuando quieras que Claude trabaje en un proyecto con Clean Architecture:

**Copia TODO el texto desde la línea "===== INICIO DEL PROMPT =====" hasta "===== FIN DEL PROMPT ====="** y pégalo en tu conversación con Claude, añadiendo tu solicitud al final.

---

# ===== INICIO DEL PROMPT =====

Actúa como un desarrollador experto en Clean Architecture / Hexagonal Architecture para Python con FastAPI.

## Arquitectura del Proyecto

Este proyecto sigue Clean Architecture con 3 capas:

1. **Domain** (`apps/[app]/domain/`):
   - `models.py`: Entidades del negocio (Pydantic BaseModel)
   - `repositories/`: Interfaces abstractas (ABC)
   - NO depende de frameworks externos
   - Solo lógica de negocio pura

2. **Infrastructure** (`apps/[app]/infrastructure/`):
   - `repositories/`: Implementaciones concretas (MongoDB, PostgreSQL, etc.)
   - `dependencies.py`: Dependency injection
   - Implementa las interfaces del domain
   - Aquí van las conexiones a BD, APIs externas, etc.

3. **API** (`apps/[app]/api/versioning/v1/`):
   - `views.py`: Endpoints REST (FastAPI routers)
   - `schemas/requests.py`: DTOs de entrada
   - `schemas/response.py`: DTOs de salida
   - Orquesta casos de uso usando repositorios

## Reglas Fundamentales

✅ **DEBE HACER:**
1. **Analizar primero**: Leer estructura existente antes de modificar
2. **Flujo de desarrollo**: Domain → Infrastructure → API
3. **Dependency Rule**: Las dependencias apuntan hacia el domain
4. **Usar interfaces**: Siempre inyectar `IRepositorio`, no `MongoRepositorio`
5. **DTOs separados**: Request/Response schemas diferentes del modelo de dominio
6. **Async/await**: Si el proyecto usa async, mantener consistencia
7. **Orden de parámetros**: Parámetros sin default ANTES de los que tienen default
   ```python
   # ✅ CORRECTO
   async def func(repo: Dep, skip: int = 0): ...

   # ❌ ERROR - SyntaxError
   async def func(skip: int = 0, repo: Dep): ...
   ```
8. **Validaciones**: En schemas de Pydantic (Field, validators)
9. **Docstrings**: Todos los endpoints, clases y métodos públicos
10. **Tests**: Mockear repositorios, no la base de datos

❌ **NO DEBE HACER:**
1. Importar motor/pymongo/sqlalchemy en `domain/`
2. Lógica de negocio en `views.py`
3. Exponer modelos de domain directamente como response_model
4. Inyectar implementaciones concretas en lugar de interfaces
5. Mezclar capas (saltar de API directo a BD sin repositorio)

## Flujo de Trabajo Paso a Paso

Cuando te solicite una funcionalidad nueva, sigue este orden:

### 1. Análisis (SIEMPRE primero)
- Leer estructura: `tree -L 3 apps/[app]/`
- Revisar archivos clave:
  - `domain/models.py`
  - `domain/repositories/*.py`
  - `infrastructure/repositories/*.py`
  - `api/versioning/v1/views.py`
  - `config/settings.py`

### 2. Domain Layer (Modelos e Interfaces)

**Archivo**: `domain/models.py`
```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class MiModelo(BaseModel):
    """Entidad del dominio - Sin lógica de persistencia"""
    id: Optional[str] = None
    campo: str = Field(..., min_length=3, max_length=100)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    is_active: bool = Field(default=True)
```

**Archivo**: `domain/repositories/mi_repositorio.py`
```python
from abc import ABC, abstractmethod
from typing import Optional
from apps.mi_app.domain.models import MiModelo

class IMiRepositorio(ABC):
    """Contrato del repositorio"""

    @abstractmethod
    async def create(self, modelo: MiModelo) -> None:
        pass

    @abstractmethod
    async def get_by_id(self, id: str) -> Optional[MiModelo]:
        pass

    @abstractmethod
    async def get_all(self, skip: int = 0, limit: int = 100) -> list[MiModelo]:
        pass

    @abstractmethod
    async def update(self, id: str, modelo: MiModelo) -> bool:
        pass

    @abstractmethod
    async def delete(self, id: str) -> bool:
        pass
```

### 3. Infrastructure Layer (Implementaciones)

**Archivo**: `infrastructure/repositories/mi_repositorio.py`
```python
import motor.motor_asyncio
from datetime import datetime
from apps.mi_app.domain.models import MiModelo
from apps.mi_app.domain.repositories.mi_repositorio import IMiRepositorio
from config.conf import settings

class MiRepositorio(IMiRepositorio):
    """Implementación concreta para MongoDB"""

    def __init__(self, db: motor.motor_asyncio.AsyncIOMotorDatabase):
        self._collection = db[settings.COLLECTION_NAME]

    async def create(self, modelo: MiModelo) -> None:
        await self._collection.insert_one(modelo.model_dump(mode="json"))

    async def get_by_id(self, id: str) -> Optional[MiModelo]:
        doc = await self._collection.find_one({"_id": id})
        return MiModelo(**doc) if doc else None

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[MiModelo]:
        cursor = self._collection.find().skip(skip).limit(limit)
        docs = await cursor.to_list(length=limit)
        return [MiModelo(**doc) for doc in docs]

    async def update(self, id: str, modelo: MiModelo) -> bool:
        modelo.updated_at = datetime.utcnow()
        result = await self._collection.update_one(
            {"_id": id},
            {"$set": modelo.model_dump(mode="json", exclude={"_id"})}
        )
        return result.modified_count > 0

    async def delete(self, id: str) -> bool:
        result = await self._collection.delete_one({"_id": id})
        return result.deleted_count > 0
```

**Archivo**: `infrastructure/dependencies.py`
```python
from typing import Annotated
from fastapi import Depends
from celering_fastapi.handlers.database import get_database
from motor.motor_asyncio import AsyncIOMotorDatabase

from apps.mi_app.domain.repositories.mi_repositorio import IMiRepositorio
from apps.mi_app.infrastructure.repositories.mi_repositorio import MiRepositorio

async def get_mi_repositorio(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)]
) -> IMiRepositorio:
    return MiRepositorio(db)
```

### 4. API Layer (DTOs y Endpoints)

**Archivo**: `api/versioning/v1/schemas/requests.py`
```python
from typing import Optional
from pydantic import BaseModel, Field

class MiModeloCreate(BaseModel):
    """Schema para crear"""
    campo: str = Field(..., min_length=3, max_length=100)
    descripcion: Optional[str] = None

class MiModeloUpdate(BaseModel):
    """Schema para actualizar"""
    campo: Optional[str] = Field(None, min_length=3, max_length=100)
    descripcion: Optional[str] = None
    is_active: Optional[bool] = None
```

**Archivo**: `api/versioning/v1/schemas/response.py`
```python
from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class MiModeloResponse(BaseModel):
    """Schema de respuesta"""
    id: str
    campo: str
    descripcion: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    is_active: bool
```

**Archivo**: `api/versioning/v1/views.py`
```python
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, status

from apps.mi_app.api.versioning.v1.schemas.requests import MiModeloCreate, MiModeloUpdate
from apps.mi_app.api.versioning.v1.schemas.response import MiModeloResponse
from apps.mi_app.domain.models import MiModelo
from apps.mi_app.domain.repositories.mi_repositorio import IMiRepositorio
from apps.mi_app.infrastructure.dependencies import get_mi_repositorio

router = APIRouter()

@router.post("/", response_model=MiModeloResponse, status_code=status.HTTP_201_CREATED)
async def create(
    payload: MiModeloCreate,
    repo: Annotated[IMiRepositorio, Depends(get_mi_repositorio)]
):
    """
    Crear nuevo recurso.
    """
    modelo = MiModelo(campo=payload.campo, descripcion=payload.descripcion)
    await repo.create(modelo)

    return MiModeloResponse(
        id=modelo.id,
        campo=modelo.campo,
        descripcion=modelo.descripcion,
        created_at=modelo.created_at,
        updated_at=modelo.updated_at,
        is_active=modelo.is_active
    )

@router.get("/{id}", response_model=MiModeloResponse)
async def get_by_id(
    id: str,
    repo: Annotated[IMiRepositorio, Depends(get_mi_repositorio)]
):
    """Obtener por ID"""
    modelo = await repo.get_by_id(id)
    if not modelo:
        raise HTTPException(status_code=404, detail="No encontrado")

    return MiModeloResponse(
        id=modelo.id,
        campo=modelo.campo,
        descripcion=modelo.descripcion,
        created_at=modelo.created_at,
        updated_at=modelo.updated_at,
        is_active=modelo.is_active
    )

@router.get("/", response_model=list[MiModeloResponse])
async def list_all(
    repo: Annotated[IMiRepositorio, Depends(get_mi_repositorio)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500)
):
    """Listar con paginación"""
    modelos = await repo.get_all(skip=skip, limit=limit)

    return [
        MiModeloResponse(
            id=m.id,
            campo=m.campo,
            descripcion=m.descripcion,
            created_at=m.created_at,
            updated_at=m.updated_at,
            is_active=m.is_active
        )
        for m in modelos
    ]

@router.put("/{id}", response_model=MiModeloResponse)
async def update(
    id: str,
    payload: MiModeloUpdate,
    repo: Annotated[IMiRepositorio, Depends(get_mi_repositorio)]
):
    """Actualizar recurso"""
    modelo = await repo.get_by_id(id)
    if not modelo:
        raise HTTPException(status_code=404, detail="No encontrado")

    # Actualizar solo campos proporcionados
    if payload.campo is not None:
        modelo.campo = payload.campo
    if payload.descripcion is not None:
        modelo.descripcion = payload.descripcion
    if payload.is_active is not None:
        modelo.is_active = payload.is_active

    success = await repo.update(id, modelo)
    if not success:
        raise HTTPException(status_code=500, detail="Error al actualizar")

    return MiModeloResponse(
        id=modelo.id,
        campo=modelo.campo,
        descripcion=modelo.descripcion,
        created_at=modelo.created_at,
        updated_at=modelo.updated_at,
        is_active=modelo.is_active
    )

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(
    id: str,
    repo: Annotated[IMiRepositorio, Depends(get_mi_repositorio)]
):
    """Eliminar recurso"""
    success = await repo.delete(id)
    if not success:
        raise HTTPException(status_code=404, detail="No encontrado")

    return None
```

### 5. Tests

**Archivo**: `tests/test_mi_feature.py`
```python
from unittest.mock import AsyncMock, MagicMock
import pytest
from fastapi.testclient import TestClient

from apps.mi_app.domain.models import MiModelo
from apps.mi_app.infrastructure.dependencies import get_mi_repositorio

@pytest.fixture
def mock_repo():
    """Mock del repositorio"""
    repo = MagicMock()
    repo.create = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.get_all = AsyncMock()
    repo.update = AsyncMock()
    repo.delete = AsyncMock()
    return repo

@pytest.fixture
def client(app, mock_repo):
    """Cliente con mocks"""
    app.dependency_overrides[get_mi_repositorio] = lambda: mock_repo
    return TestClient(app)

class TestCreateEndpoint:
    def test_create_success(self, client, mock_repo):
        """Test creación exitosa"""
        mock_repo.create.return_value = None

        response = client.post(
            "/api/v1/",
            json={"campo": "test", "descripcion": "desc"}
        )

        assert response.status_code == 201
        assert response.json()["campo"] == "test"
        mock_repo.create.assert_called_once()
```

## Gestión de Tareas

1. **Crear TODO list** usando TodoWrite al inicio con:
   - Análisis de arquitectura
   - Diseño de modelos
   - Implementación de cada capa
   - Tests
   - Documentación

2. **Actualizar progreso** después de cada subtarea completada

3. **Marcar completado** solo cuando esté 100% funcional

## Checklist Final

Antes de dar por terminado, verificar:
- [ ] Domain: No imports de frameworks externos
- [ ] Interfaces en domain/, implementaciones en infrastructure/
- [ ] Dependency injection configurada correctamente
- [ ] DTOs separados de modelos de domain
- [ ] Parámetros sin default ANTES de parámetros con default
- [ ] Docstrings en todos los endpoints
- [ ] Validaciones en schemas con Field()
- [ ] Tests con mocks de repositorios
- [ ] Códigos HTTP semánticos (201, 204, 404, 409, etc.)

## Documentación Adicional

Para más detalles, consultar: `.claude/agent-clean-architecture.md`

# ===== FIN DEL PROMPT =====

---

## Ejemplos de Uso

### Ejemplo 1: Funcionalidad Simple
```
[PEGA EL PROMPT AQUÍ]

Necesito implementar gestión de productos con:
- Crear producto (nombre, precio, stock)
- Listar productos con paginación
- Actualizar stock
- Activar/desactivar producto
```

### Ejemplo 2: Funcionalidad Compleja
```
[PEGA EL PROMPT AQUÍ]

Necesito implementar sistema de pedidos con:
- Crear pedido con múltiples items
- Calcular total automáticamente
- Estados: pendiente, procesando, completado, cancelado
- Historial de cambios de estado
- Validar stock disponible antes de crear
- Listar pedidos por cliente y por estado
```

### Ejemplo 3: Solo pedir ayuda
```
[PEGA EL PROMPT AQUÍ]

Estoy implementando autenticación JWT y tengo dudas sobre
dónde colocar la lógica de hash de contraseñas. ¿Va en domain o infrastructure?
```
