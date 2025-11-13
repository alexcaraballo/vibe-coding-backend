# Plan: RF-002 - Búsqueda de Trayectos

**Issue**: #2
**Prioridad**: ALTA (Core MVP)
**Estimación**: 2-3 horas
**Dependencias**: 02-RF-001-publicacion-trayectos.md (completado)

---

## Objetivo

Permitir a los pasajeros buscar trayectos disponibles según origen, destino y otros criterios opcionales, con búsqueda exacta o aproximada por nombre de ciudad.

---

## Análisis Previo

### Funcionalidad ya implementada en RF-001
✅ El repositorio `ITripRepository` ya tiene el método `search()`
✅ El endpoint `GET /trips/v1/` ya lista todos los trayectos

### Lo que falta
❌ Endpoint específico de búsqueda con filtros avanzados
❌ Búsqueda "aproximada" por ciudad (regex, case-insensitive)
❌ Filtros por fecha
❌ Optimización de consultas

---

## Paso 1: Actualizar Endpoint de Búsqueda

**Archivo**: `apps/trips/api/versioning/v1/views.py`

Agregar este nuevo endpoint después del `GET /`:

```python
@router.get("/search", response_model=TripListResponse)
async def search_trips(
    repo: Annotated[ITripRepository, Depends(get_trip_repository)],
    origin: Optional[str] = Query(None, description="Ciudad de origen (búsqueda aproximada)"),
    destination: Optional[str] = Query(None, description="Ciudad de destino (búsqueda aproximada)"),
    date_from: Optional[date] = Query(None, description="Fecha mínima (YYYY-MM-DD)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500)
):
    """
    Buscar trayectos disponibles con filtros.

    **Endpoint:** `GET /trips/search?from=A&to=B`

    **Características:**
    - Búsqueda exacta o aproximada por ciudad
    - Filtro por fecha (solo trayectos futuros)
    - Solo retorna trayectos activos con plazas disponibles
    - No requiere autenticación

    **Ejemplos:**
    - `/trips/search?origin=Cádiz&destination=Sevilla`
    - `/trips/search?origin=cadiz&destination=sev` (aproximada)
    - `/trips/search?date_from=2025-12-15`
    """
    # Buscar trayectos usando el repositorio
    trips = await repo.search(
        origin=origin,
        destination=destination,
        date_from=date_from,
        skip=skip,
        limit=limit
    )

    # Filtrar solo trayectos con plazas disponibles
    available_trips = [t for t in trips if t.has_available_seats()]

    return TripListResponse(
        trips=[TripResponse(**t.model_dump()) for t in available_trips],
        total=len(available_trips),
        skip=skip,
        limit=limit
    )
```

---

## Paso 2: Mejorar Método de Búsqueda en Repositorio

Ya existe, pero podemos mejorarlo para soportar búsqueda aproximada.

**Archivo**: `apps/trips/infrastructure/repositories/trip_repository.py`

Actualizar el método `search`:

```python
async def search(
    self,
    origin: Optional[str] = None,
    destination: Optional[str] = None,
    date_from: Optional[date] = None,
    skip: int = 0,
    limit: int = 100
) -> list[Trip]:
    """
    Busca trayectos por criterios con búsqueda aproximada.

    - Búsqueda case-insensitive con regex
    - Solo trayectos activos
    - Solo con plazas disponibles
    - Fecha >= date_from si se proporciona
    """
    query = {
        "status": "active",
        "is_active": True,
        "available_seats": {"$gt": 0}  # Solo con plazas
    }

    # Búsqueda aproximada por ciudad (case-insensitive, parcial)
    if origin:
        query["origin"] = {"$regex": origin, "$options": "i"}
    if destination:
        query["destination"] = {"$regex": destination, "$options": "i"}

    # Filtro por fecha (solo futuros)
    if date_from:
        query["departure_date"] = {"$gte": date_from.isoformat()}
    else:
        # Por defecto, solo trayectos futuros
        from datetime import date as dt_date
        query["departure_date"] = {"$gte": dt_date.today().isoformat()}

    # Ordenar por fecha de salida (más cercanos primero)
    cursor = self._collection.find(query).sort("departure_date", 1).skip(skip).limit(limit)

    trips = []
    async for doc in cursor:
        doc["id"] = str(doc.pop("_id"))
        trips.append(Trip(**doc))
    return trips
```

---

## Paso 3: Agregar Schema de Request para Búsqueda

**Archivo**: `apps/trips/api/versioning/v1/schemas/requests.py`

Agregar:

```python
from typing import Optional
from datetime import date

class SearchTripsRequest(BaseModel):
    """Schema para búsqueda de trayectos (query params)"""
    origin: Optional[str] = Field(None, description="Ciudad de origen")
    destination: Optional[str] = Field(None, description="Ciudad de destino")
    date_from: Optional[date] = Field(None, description="Fecha mínima del viaje")
    skip: int = Field(0, ge=0)
    limit: int = Field(100, ge=1, le=500)

    class Config:
        json_schema_extra = {
            "example": {
                "origin": "Cádiz",
                "destination": "Sevilla",
                "date_from": "2025-12-15",
                "skip": 0,
                "limit": 10
            }
        }
```

---

## Paso 4: Optimización - Índices de MongoDB

Ya se crearon en RF-001, pero verificar:

```python
# scripts/create_indexes.py

async def create_trip_indexes():
    """Verificar índices para búsqueda eficiente"""
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.MONGODB_DB_NAME]

    # Índice compuesto para búsqueda
    await db.trips.create_index([
        ("origin", 1),
        ("destination", 1),
        ("departure_date", 1),
        ("status", 1)
    ])

    # Índice para filtrar disponibles
    await db.trips.create_index([
        ("available_seats", 1),
        ("is_active", 1)
    ])

    print("✅ Índices optimizados para búsqueda")

    client.close()
```

---

## Paso 5: Testing

**Archivo**: `tests/test_trips/test_search_trips.py`

```python
import pytest
from httpx import AsyncClient
from datetime import date, time, timedelta
from main import app

@pytest.mark.asyncio
async def test_search_trips_by_origin():
    """Test búsqueda por origen"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/v1/trips/v1/search?origin=Cádiz")

    assert response.status_code == 200
    data = response.json()
    assert "trips" in data
    # Verificar que todos tienen "Cádiz" en origin
    for trip in data["trips"]:
        assert "cádiz" in trip["origin"].lower()

@pytest.mark.asyncio
async def test_search_trips_by_origin_and_destination():
    """Test búsqueda por origen y destino"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/v1/trips/v1/search?origin=Cádiz&destination=Sevilla")

    assert response.status_code == 200
    data = response.json()
    assert "trips" in data

@pytest.mark.asyncio
async def test_search_trips_approximate():
    """Test búsqueda aproximada (case-insensitive, parcial)"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Buscar con minúsculas y parcial
        response = await ac.get("/api/v1/trips/v1/search?origin=cadiz&destination=sev")

    assert response.status_code == 200
    data = response.json()
    assert "trips" in data

@pytest.mark.asyncio
async def test_search_trips_by_date():
    """Test búsqueda por fecha mínima"""
    tomorrow = (date.today() + timedelta(days=1)).isoformat()

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get(f"/api/v1/trips/v1/search?date_from={tomorrow}")

    assert response.status_code == 200
    data = response.json()
    # Verificar que todos son >= tomorrow
    for trip in data["trips"]:
        assert trip["departure_date"] >= tomorrow

@pytest.mark.asyncio
async def test_search_trips_no_results():
    """Test búsqueda sin resultados"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/v1/trips/v1/search?origin=CiudadInexistente")

    assert response.status_code == 200
    data = response.json()
    assert len(data["trips"]) == 0
    assert data["total"] == 0

@pytest.mark.asyncio
async def test_search_trips_only_available_seats():
    """Test que solo retorna trayectos con plazas disponibles"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/v1/trips/v1/search?origin=Cádiz")

    assert response.status_code == 200
    data = response.json()
    # Verificar que todos tienen available_seats > 0
    for trip in data["trips"]:
        assert trip["available_seats"] > 0

@pytest.mark.asyncio
async def test_search_trips_pagination():
    """Test paginación en búsqueda"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/v1/trips/v1/search?skip=0&limit=5")

    assert response.status_code == 200
    data = response.json()
    assert len(data["trips"]) <= 5
    assert data["skip"] == 0
    assert data["limit"] == 5
```

---

## Paso 6: Documentación en Swagger

Agregar ejemplo de uso en el endpoint:

```python
@router.get("/search", response_model=TripListResponse)
async def search_trips(
    # ... parámetros ...
):
    """
    Buscar trayectos disponibles con filtros.

    ## Características
    - ✅ Búsqueda **aproximada** por ciudad (case-insensitive, parcial)
    - ✅ Filtro por fecha (solo trayectos futuros)
    - ✅ Solo retorna trayectos activos con plazas disponibles
    - ✅ Ordenados por fecha de salida (más cercanos primero)
    - ✅ No requiere autenticación

    ## Ejemplos de Uso

    **Búsqueda exacta:**
    ```
    GET /trips/search?origin=Cádiz&destination=Sevilla
    ```

    **Búsqueda aproximada:**
    ```
    GET /trips/search?origin=cadiz&destination=sev
    ```
    Retorna trayectos donde origen contiene "cadiz" y destino contiene "sev"

    **Filtro por fecha:**
    ```
    GET /trips/search?date_from=2025-12-15
    ```

    **Solo origen:**
    ```
    GET /trips/search?origin=Cádiz
    ```

    **Paginación:**
    ```
    GET /trips/search?origin=Cádiz&skip=10&limit=5
    ```

    ## Reglas de Negocio
    - Solo trayectos con `status = "active"`
    - Solo trayectos con `available_seats > 0`
    - Solo trayectos con `is_active = True`
    - Por defecto, solo trayectos con `departure_date >= hoy`
    """
    # ... código ...
```

---

## Paso 7: Casos Edge - Manejo de Caracteres Especiales

**Actualizar método search** para manejar caracteres especiales en regex:

```python
import re

async def search(
    self,
    origin: Optional[str] = None,
    destination: Optional[str] = None,
    date_from: Optional[date] = None,
    skip: int = 0,
    limit: int = 100
) -> list[Trip]:
    """Busca trayectos con sanitización de entrada"""
    query = {
        "status": "active",
        "is_active": True,
        "available_seats": {"$gt": 0}
    }

    # Sanitizar entrada para evitar inyección de regex
    def sanitize_regex(text: str) -> str:
        """Escapa caracteres especiales de regex"""
        return re.escape(text)

    if origin:
        safe_origin = sanitize_regex(origin)
        query["origin"] = {"$regex": safe_origin, "$options": "i"}
    if destination:
        safe_destination = sanitize_regex(destination)
        query["destination"] = {"$regex": safe_destination, "$options": "i"}

    if date_from:
        query["departure_date"] = {"$gte": date_from.isoformat()}
    else:
        from datetime import date as dt_date
        query["departure_date"] = {"$gte": dt_date.today().isoformat()}

    cursor = self._collection.find(query).sort("departure_date", 1).skip(skip).limit(limit)

    trips = []
    async for doc in cursor:
        doc["id"] = str(doc.pop("_id"))
        trips.append(Trip(**doc))
    return trips
```

---

## Checklist de Implementación

- [ ] Agregar endpoint `GET /trips/search` en views.py
- [ ] Mejorar método `search()` en repositorio:
  - [ ] Búsqueda case-insensitive
  - [ ] Filtro por plazas disponibles
  - [ ] Filtro por fecha futura
  - [ ] Ordenación por fecha
  - [ ] Sanitización de entrada (regex escape)
- [ ] Agregar `SearchTripsRequest` schema (opcional, ya se usan query params)
- [ ] Verificar índices en MongoDB
- [ ] Tests de búsqueda:
  - [ ] Por origen
  - [ ] Por destino
  - [ ] Por origen y destino
  - [ ] Búsqueda aproximada
  - [ ] Por fecha
  - [ ] Sin resultados
  - [ ] Solo con plazas disponibles
  - [ ] Paginación
- [ ] Documentar ejemplos en Swagger
- [ ] Validar en /docs
- [ ] Probar con Postman/curl

---

## Verificación

```bash
# Buscar trayectos por origen y destino
curl "http://localhost:8000/api/v1/trips/v1/search?origin=Cádiz&destination=Sevilla"

# Búsqueda aproximada (case-insensitive)
curl "http://localhost:8000/api/v1/trips/v1/search?origin=cadiz&destination=sev"

# Buscar por fecha
curl "http://localhost:8000/api/v1/trips/v1/search?date_from=2025-12-15"

# Solo por origen
curl "http://localhost:8000/api/v1/trips/v1/search?origin=Cádiz"

# Con paginación
curl "http://localhost:8000/api/v1/trips/v1/search?origin=Cádiz&skip=0&limit=5"

# Ver documentación en Swagger
open http://localhost:8000/docs
```

---

## Criterios de Aceptación (de Issue #2)

✅ Pasajero puede buscar por origen y destino
✅ Sistema retorna trayectos coincidentes
✅ Búsqueda puede ser exacta o aproximada por ciudad
✅ Solo se retornan trayectos activos con plazas disponibles
✅ Búsqueda funciona sin autenticación (pública)
✅ Paginación implementada
✅ Ordenación por fecha (más cercanos primero)

---

## Próximo Paso

Una vez completado RF-002, proceder con:
- **RF-INF-002**: Validación de Disponibilidad (validaciones previas a reserva)
- **RF-INF-004**: Gestión de Plazas (lógica de decrementar/incrementar plazas)
- **RF-003**: Reserva de Trayectos (usa validación y gestión de plazas)
