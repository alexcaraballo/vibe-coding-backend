# Plan: RF-BONUS-002 - Estimación de CO₂ Evitado

**Issue**: #11
**Prioridad**: BAJA (Bonus - Impacto ambiental)
**Estimación**: 2-3 horas
**Dependencias**:
- 04-RF-003-reserva-trayectos.md (completado)
- 06-RF-005-visualizacion-mapas.md (completado - calcula distancias)

---

## Objetivo

Calcular y mostrar la cantidad estimada de CO₂ evitada mediante el uso compartido de vehículos, incentivando el uso de la plataforma por su beneficio ambiental.

---

## Análisis Previo

### Fórmulas de Cálculo

**1. Emisiones por Vehículo**
- Promedio vehículo gasolina: **120 g CO₂/km**
- Promedio vehículo diésel: **105 g CO₂/km**
- Promedio vehículo híbrido: **70 g CO₂/km**
- Promedio vehículo eléctrico: **0 g CO₂/km** (directo, sin considerar generación eléctrica)

**2. Cálculo de CO₂ Evitado**
```
CO₂_evitado = distancia_km × emisiones_por_km × (num_pasajeros)
```

**Ejemplo**:
- Viaje Cádiz → Sevilla: 125 km
- 2 pasajeros comparten el trayecto
- Vehículo gasolina: 120 g CO₂/km
- CO₂ evitado = 125 × 120 × 2 = **30,000 g = 30 kg CO₂**

**3. Equivalencias Visuales**
- 1 kg CO₂ ≈ 0.4 árboles necesarios para absorber en 1 año
- 1 kg CO₂ ≈ 5 km recorridos en coche promedio
- 1000 kg CO₂ ≈ 1 vuelo Madrid-Barcelona

### Arquitectura Objetivo
```
apps/trips/
├── domain/
│   ├── models.py               # Trip con campo co2_saved_kg
│   └── services/
│       └── co2_service.py      # ICO2Service (interface)
└── infrastructure/
    └── services/
        └── co2_calculator.py   # CO2Calculator (implementación)
```

---

## Paso 1: Modelo de Dominio - Emisiones

**Archivo**: `apps/trips/domain/models.py`

Agregar enum de tipos de vehículo y actualizar Trip:

```python
from enum import Enum

class VehicleType(str, Enum):
    """Tipos de vehículo con emisiones asociadas"""
    GASOLINE = "gasoline"
    DIESEL = "diesel"
    HYBRID = "hybrid"
    ELECTRIC = "electric"

class EmissionFactors:
    """Factores de emisión en g CO₂/km según tipo de vehículo"""
    FACTORS = {
        VehicleType.GASOLINE: 120,
        VehicleType.DIESEL: 105,
        VehicleType.HYBRID: 70,
        VehicleType.ELECTRIC: 0
    }

    @classmethod
    def get_factor(cls, vehicle_type: VehicleType) -> int:
        """Obtiene factor de emisión para un tipo de vehículo"""
        return cls.FACTORS.get(vehicle_type, 120)  # Default: gasolina

class Trip(BaseModel):
    # ... campos existentes ...

    # NUEVO: Información del vehículo
    vehicle_type: VehicleType = Field(
        default=VehicleType.GASOLINE,
        description="Tipo de vehículo del conductor"
    )
    vehicle_model: Optional[str] = Field(None, max_length=100)
    vehicle_plate: Optional[str] = Field(None, max_length=20)

    # NUEVO: Métricas ambientales
    distance_km: Optional[float] = Field(
        None,
        ge=0,
        description="Distancia total del trayecto en km"
    )
    co2_saved_per_passenger_kg: Optional[float] = Field(
        None,
        ge=0,
        description="CO₂ evitado por cada pasajero en kg"
    )
    total_co2_saved_kg: Optional[float] = Field(
        default=0.0,
        ge=0,
        description="CO₂ total evitado por todos los pasajeros en kg"
    )

    def calculate_co2_savings(self, distance_km: float, passengers_count: int):
        """
        Calcula el CO₂ evitado por el viaje compartido.

        Args:
            distance_km: Distancia del trayecto
            passengers_count: Número de pasajeros (excluye conductor)
        """
        emission_factor = EmissionFactors.get_factor(self.vehicle_type)

        # CO₂ evitado por pasajero (en gramos)
        co2_per_passenger_g = distance_km * emission_factor

        # Convertir a kg
        self.co2_saved_per_passenger_kg = round(co2_per_passenger_g / 1000, 2)

        # Total evitado
        self.total_co2_saved_kg = round(
            (co2_per_passenger_g * passengers_count) / 1000,
            2
        )

        self.distance_km = round(distance_km, 2)
```

---

## Paso 2: Interface del Servicio de CO₂

**Archivo**: `apps/trips/domain/services/co2_service.py`

```python
from abc import ABC, abstractmethod
from typing import Optional
from apps.trips.domain.models import Trip, VehicleType

class ICO2Service(ABC):
    """Contrato para servicio de cálculo de CO₂"""

    @abstractmethod
    def calculate_trip_emissions(
        self,
        distance_km: float,
        vehicle_type: VehicleType
    ) -> float:
        """
        Calcula emisiones totales del trayecto.

        Returns:
            Emisiones en kg CO₂
        """
        pass

    @abstractmethod
    def calculate_savings_per_passenger(
        self,
        distance_km: float,
        vehicle_type: VehicleType
    ) -> float:
        """
        Calcula CO₂ evitado por cada pasajero.

        Returns:
            CO₂ evitado en kg
        """
        pass

    @abstractmethod
    def calculate_total_savings(
        self,
        distance_km: float,
        vehicle_type: VehicleType,
        passengers_count: int
    ) -> float:
        """
        Calcula CO₂ total evitado por todos los pasajeros.

        Returns:
            CO₂ total evitado en kg
        """
        pass

    @abstractmethod
    def get_environmental_equivalence(self, co2_kg: float) -> dict:
        """
        Convierte kg de CO₂ en equivalencias comprensibles.

        Returns:
            Dict con equivalencias: árboles, km en coche, vuelos, etc.
        """
        pass
```

---

## Paso 3: Implementación del Servicio

**Archivo**: `apps/trips/infrastructure/services/co2_calculator.py`

```python
import math
from apps.trips.domain.models import VehicleType, EmissionFactors
from apps.trips.domain.services.co2_service import ICO2Service

class CO2Calculator(ICO2Service):
    """
    Implementación del servicio de cálculo de CO₂.
    Usa factores de emisión estándar de la industria.
    """

    def calculate_trip_emissions(
        self,
        distance_km: float,
        vehicle_type: VehicleType
    ) -> float:
        """Calcula emisiones totales del trayecto"""
        emission_factor = EmissionFactors.get_factor(vehicle_type)
        emissions_g = distance_km * emission_factor
        return round(emissions_g / 1000, 2)  # Convertir a kg

    def calculate_savings_per_passenger(
        self,
        distance_km: float,
        vehicle_type: VehicleType
    ) -> float:
        """
        Calcula CO₂ evitado por pasajero.

        Lógica: Cada pasajero evita hacer el viaje en su propio vehículo.
        """
        return self.calculate_trip_emissions(distance_km, vehicle_type)

    def calculate_total_savings(
        self,
        distance_km: float,
        vehicle_type: VehicleType,
        passengers_count: int
    ) -> float:
        """
        Calcula CO₂ total evitado.

        Args:
            passengers_count: Número de pasajeros (sin incluir conductor)
        """
        savings_per_passenger = self.calculate_savings_per_passenger(
            distance_km, vehicle_type
        )
        total_savings = savings_per_passenger * passengers_count
        return round(total_savings, 2)

    def get_environmental_equivalence(self, co2_kg: float) -> dict:
        """
        Convierte kg de CO₂ en equivalencias visuales.

        Referencias:
        - 1 árbol absorbe ~21 kg CO₂/año
        - 1 km en coche promedio = ~0.12 kg CO₂
        - Vuelo Madrid-Barcelona = ~85 kg CO₂
        """
        return {
            "co2_kg": co2_kg,
            "trees_equivalent": round(co2_kg / 21, 1),
            "car_km_equivalent": round(co2_kg / 0.12, 0),
            "madrid_barcelona_flights": round(co2_kg / 85, 2),
            "message": self._generate_message(co2_kg)
        }

    def _generate_message(self, co2_kg: float) -> str:
        """Genera mensaje motivacional según cantidad de CO₂"""
        if co2_kg < 5:
            return f"Has evitado {co2_kg} kg de CO₂. ¡Cada viaje cuenta!"
        elif co2_kg < 20:
            trees = round(co2_kg / 21, 1)
            return f"Has evitado {co2_kg} kg de CO₂. Equivale al trabajo anual de {trees} árboles."
        elif co2_kg < 50:
            km = round(co2_kg / 0.12, 0)
            return f"Has evitado {co2_kg} kg de CO₂. ¡Como no conducir {km} km!"
        else:
            flights = round(co2_kg / 85, 2)
            return f"Has evitado {co2_kg} kg de CO₂. ¡Equivale a {flights} vuelos Madrid-Barcelona!"

    def estimate_yearly_impact(
        self,
        trips_per_month: int,
        avg_distance_km: float,
        avg_passengers: int,
        vehicle_type: VehicleType
    ) -> dict:
        """
        Estima el impacto anual basado en uso promedio.

        Útil para mostrar estadísticas de usuario.
        """
        monthly_savings = self.calculate_total_savings(
            avg_distance_km, vehicle_type, avg_passengers
        ) * trips_per_month

        yearly_savings = monthly_savings * 12

        return {
            "monthly_co2_saved_kg": round(monthly_savings, 2),
            "yearly_co2_saved_kg": round(yearly_savings, 2),
            "yearly_trees_equivalent": round(yearly_savings / 21, 1),
            "yearly_car_km_equivalent": round(yearly_savings / 0.12, 0)
        }
```

---

## Paso 4: Integrar con BookingService

**Archivo**: `apps/trips/infrastructure/services/booking_service.py`

Actualizar para calcular CO₂ al crear reserva:

```python
from apps.trips.infrastructure.services.co2_calculator import CO2Calculator
from apps.maps.domain.services.map_service import IMapService

class BookingService:
    def __init__(
        self,
        booking_repo: IBookingRepository,
        trip_repo: ITripRepository,
        map_service: Optional[IMapService] = None  # NUEVO: Inyectar para calcular distancia
    ):
        self.booking_repo = booking_repo
        self.trip_repo = trip_repo
        self.map_service = map_service
        self.co2_calculator = CO2Calculator()  # NUEVO

    async def create_booking(
        self,
        trip_id: str,
        passenger_id: str,
        seats_requested: int = 1,
        passenger_notes: Optional[str] = None
    ) -> Booking:
        # ... validaciones existentes ...

        # 7. Crear la reserva
        booking = Booking(...)
        created_booking = await self.booking_repo.create(booking)

        # 8. Actualizar plazas disponibles
        trip.available_seats -= seats_requested

        # 9. NUEVO: Calcular CO₂ evitado si hay distancia disponible
        if trip.distance_km and trip.distance_km > 0:
            # Obtener número actual de pasajeros
            passengers_count = trip.total_seats - trip.available_seats - 1  # -1 por el conductor

            # Calcular CO₂
            trip.calculate_co2_savings(trip.distance_km, passengers_count)
        elif self.map_service:
            # Si no hay distancia, intentar calcularla usando map service
            try:
                from apps.maps.domain.models import Coordinates

                if trip.origin_lat and trip.destination_lat:
                    origin = Coordinates(latitude=trip.origin_lat, longitude=trip.origin_lng)
                    dest = Coordinates(latitude=trip.destination_lat, longitude=trip.destination_lng)

                    route = await self.map_service.get_route(origin, dest)
                    if route and route.distance_km:
                        passengers_count = trip.total_seats - trip.available_seats - 1
                        trip.calculate_co2_savings(route.distance_km, passengers_count)
            except Exception as e:
                print(f"Error calculating CO₂: {e}")

        await self.trip_repo.update(trip_id, trip)

        return created_booking
```

---

## Paso 5: DTOs - Schemas

**Archivo**: `apps/trips/api/versioning/v1/schemas/requests.py`

Actualizar `CreateTripRequest`:

```python
class CreateTripRequest(BaseModel):
    # ... campos existentes ...

    vehicle_type: Optional[str] = Field(
        default="gasoline",
        description="Tipo de vehículo: gasoline, diesel, hybrid, electric"
    )
    vehicle_model: Optional[str] = Field(None, max_length=100)
    vehicle_plate: Optional[str] = Field(None, max_length=20)
```

**Archivo**: `apps/trips/api/versioning/v1/schemas/responses.py`

Actualizar `TripResponse`:

```python
class CO2ImpactResponse(BaseModel):
    """Información del impacto ambiental del trayecto"""
    co2_saved_per_passenger_kg: float
    total_co2_saved_kg: float
    trees_equivalent: float
    car_km_equivalent: float
    message: str

class TripResponse(BaseModel):
    # ... campos existentes ...

    vehicle_type: str
    vehicle_model: Optional[str] = None
    distance_km: Optional[float] = None
    co2_saved_per_passenger_kg: Optional[float] = None
    total_co2_saved_kg: Optional[float] = None

    # Información enriquecida
    co2_impact: Optional[CO2ImpactResponse] = None
```

---

## Paso 6: Endpoints de CO₂

**Archivo**: `apps/trips/api/versioning/v1/views.py`

Agregar endpoints específicos:

```python
from apps.trips.infrastructure.services.co2_calculator import CO2Calculator

@router.get("/{trip_id}/co2-impact", response_model=CO2ImpactResponse)
async def get_trip_co2_impact(
    trip_id: str,
    trip_repo: Annotated[ITripRepository, Depends(get_trip_repository)]
):
    """
    Obtener impacto ambiental de un trayecto.

    **Endpoint:** `GET /trips/{trip_id}/co2-impact`

    **Retorna:**
    - CO₂ evitado por pasajero
    - CO₂ total evitado
    - Equivalencias ambientales
    """
    trip = await trip_repo.get_by_id(trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trayecto no encontrado")

    if not trip.co2_saved_per_passenger_kg or trip.co2_saved_per_passenger_kg == 0:
        raise HTTPException(
            status_code=400,
            detail="Este trayecto aún no tiene cálculo de CO₂"
        )

    co2_calculator = CO2Calculator()
    equivalence = co2_calculator.get_environmental_equivalence(
        trip.total_co2_saved_kg
    )

    return CO2ImpactResponse(
        co2_saved_per_passenger_kg=trip.co2_saved_per_passenger_kg,
        total_co2_saved_kg=trip.total_co2_saved_kg,
        trees_equivalent=equivalence["trees_equivalent"],
        car_km_equivalent=equivalence["car_km_equivalent"],
        message=equivalence["message"]
    )

@router.get("/users/me/co2-stats", response_model=dict)
async def get_user_co2_stats(
    current_user: Annotated[User, Depends(get_current_user)],
    booking_repo: Annotated[IBookingRepository, Depends(get_booking_repository)],
    trip_repo: Annotated[ITripRepository, Depends(get_trip_repository)]
):
    """
    Obtener estadísticas de CO₂ evitado por el usuario.

    **Endpoint:** `GET /trips/users/me/co2-stats`

    **Retorna:**
    - Total CO₂ evitado
    - Número de viajes
    - Equivalencias ambientales
    """
    # Obtener todas las reservas del usuario
    bookings = await booking_repo.get_by_passenger(current_user.id, skip=0, limit=1000)

    total_co2_saved = 0.0
    trips_count = 0

    for booking in bookings:
        if booking.status == "confirmed" or booking.status == "completed":
            trip = await trip_repo.get_by_id(booking.trip_id)
            if trip and trip.co2_saved_per_passenger_kg:
                # Multiplicar por plazas reservadas
                total_co2_saved += trip.co2_saved_per_passenger_kg * booking.seats_booked
                trips_count += 1

    co2_calculator = CO2Calculator()
    equivalence = co2_calculator.get_environmental_equivalence(total_co2_saved)

    return {
        "total_co2_saved_kg": round(total_co2_saved, 2),
        "trips_count": trips_count,
        "trees_equivalent": equivalence["trees_equivalent"],
        "car_km_equivalent": equivalence["car_km_equivalent"],
        "madrid_barcelona_flights": equivalence["madrid_barcelona_flights"],
        "message": equivalence["message"]
    }
```

---

## Paso 7: Job para Actualizar CO₂ de Trayectos Existentes

**Archivo**: `scripts/calculate_co2_for_existing_trips.py`

```python
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from config.settings import settings
from apps.trips.infrastructure.services.co2_calculator import CO2Calculator
from apps.trips.domain.models import VehicleType

async def update_co2_for_trips():
    """
    Script para calcular CO₂ de trayectos existentes que no lo tienen.
    """
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.MONGODB_DB_NAME]
    trips_collection = db["trips"]

    co2_calculator = CO2Calculator()

    # Buscar trips sin CO₂ calculado
    cursor = trips_collection.find({
        "$or": [
            {"total_co2_saved_kg": {"$exists": False}},
            {"total_co2_saved_kg": 0}
        ],
        "distance_km": {"$gt": 0},
        "is_active": True
    })

    updated_count = 0

    async for trip_doc in cursor:
        try:
            distance_km = trip_doc.get("distance_km", 0)
            vehicle_type = trip_doc.get("vehicle_type", "gasoline")
            total_seats = trip_doc.get("total_seats", 0)
            available_seats = trip_doc.get("available_seats", 0)

            # Calcular pasajeros actuales
            passengers_count = total_seats - available_seats - 1  # -1 conductor

            if passengers_count > 0 and distance_km > 0:
                # Calcular CO₂
                savings_per_passenger = co2_calculator.calculate_savings_per_passenger(
                    distance_km, VehicleType(vehicle_type)
                )
                total_savings = co2_calculator.calculate_total_savings(
                    distance_km, VehicleType(vehicle_type), passengers_count
                )

                # Actualizar documento
                await trips_collection.update_one(
                    {"_id": trip_doc["_id"]},
                    {"$set": {
                        "co2_saved_per_passenger_kg": savings_per_passenger,
                        "total_co2_saved_kg": total_savings
                    }}
                )

                updated_count += 1
                print(f"✅ Trip {trip_doc['_id']}: {total_savings} kg CO₂ evitado")

        except Exception as e:
            print(f"❌ Error processing trip {trip_doc['_id']}: {e}")

    print(f"\n✅ Total trips actualizados: {updated_count}")
    client.close()

if __name__ == "__main__":
    asyncio.run(update_co2_for_trips())
```

---

## Paso 8: Testing

**Archivo**: `tests/test_trips/test_co2_calculator.py`

```python
import pytest
from apps.trips.infrastructure.services.co2_calculator import CO2Calculator
from apps.trips.domain.models import VehicleType

def test_calculate_trip_emissions():
    """Test cálculo de emisiones totales"""
    calculator = CO2Calculator()

    # 100 km en vehículo gasolina
    emissions = calculator.calculate_trip_emissions(100, VehicleType.GASOLINE)

    assert emissions == 12.0  # 100 km × 120 g/km = 12000 g = 12 kg

def test_calculate_savings_per_passenger():
    """Test CO₂ evitado por pasajero"""
    calculator = CO2Calculator()

    savings = calculator.calculate_savings_per_passenger(100, VehicleType.DIESEL)

    assert savings == 10.5  # 100 km × 105 g/km = 10500 g = 10.5 kg

def test_calculate_total_savings():
    """Test CO₂ total evitado"""
    calculator = CO2Calculator()

    # 3 pasajeros, 100 km, gasolina
    total = calculator.calculate_total_savings(100, VehicleType.GASOLINE, 3)

    assert total == 36.0  # 12 kg × 3 pasajeros

def test_get_environmental_equivalence():
    """Test equivalencias ambientales"""
    calculator = CO2Calculator()

    equivalence = calculator.get_environmental_equivalence(21.0)  # 21 kg = 1 árbol/año

    assert equivalence["co2_kg"] == 21.0
    assert equivalence["trees_equivalent"] == 1.0
    assert "message" in equivalence

@pytest.mark.asyncio
async def test_co2_impact_endpoint(client, trip_id):
    """Test endpoint de impacto CO₂"""
    response = await client.get(f"/api/v1/trips/v1/{trip_id}/co2-impact")

    assert response.status_code == 200
    data = response.json()
    assert "co2_saved_per_passenger_kg" in data
    assert "total_co2_saved_kg" in data
    assert "trees_equivalent" in data
    assert "message" in data

@pytest.mark.asyncio
async def test_user_co2_stats(client, auth_token):
    """Test estadísticas de usuario"""
    response = await client.get(
        "/api/v1/trips/v1/users/me/co2-stats",
        headers={"Authorization": f"Bearer {auth_token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "total_co2_saved_kg" in data
    assert "trips_count" in data
```

---

## Checklist de Implementación

- [ ] Agregar `VehicleType` enum y `EmissionFactors` a models.py
- [ ] Actualizar modelo `Trip` con campos CO₂ y vehículo
- [ ] Interface `ICO2Service`
- [ ] Implementar `CO2Calculator`:
  - [ ] `calculate_trip_emissions()`
  - [ ] `calculate_savings_per_passenger()`
  - [ ] `calculate_total_savings()`
  - [ ] `get_environmental_equivalence()`
  - [ ] `estimate_yearly_impact()`
- [ ] Integrar con `BookingService` para cálculo automático
- [ ] Actualizar schemas de request/response
- [ ] Endpoints:
  - [ ] GET /{trip_id}/co2-impact (impacto del trayecto)
  - [ ] GET /users/me/co2-stats (estadísticas del usuario)
- [ ] Script de migración para trips existentes
- [ ] Tests:
  - [ ] Test cálculo de emisiones
  - [ ] Test savings por pasajero
  - [ ] Test total savings
  - [ ] Test equivalencias
  - [ ] Test endpoints
- [ ] Documentar en Swagger
- [ ] Verificar en /docs

---

## Verificación

```bash
# Ver impacto CO₂ de un trayecto
curl http://localhost:8000/api/v1/trips/v1/<TRIP_ID>/co2-impact

# Ver mis estadísticas de CO₂
curl http://localhost:8000/api/v1/trips/v1/users/me/co2-stats \
  -H "Authorization: Bearer <TOKEN>"

# Crear trayecto con tipo de vehículo
curl -X POST http://localhost:8000/api/v1/trips/v1/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{
    "origin": "Cádiz",
    "destination": "Sevilla",
    "departure_date": "2025-12-15",
    "departure_time": "09:00:00",
    "available_seats": 3,
    "vehicle_type": "hybrid",
    "vehicle_model": "Toyota Prius"
  }'

# Ejecutar script de migración
python scripts/calculate_co2_for_existing_trips.py
```

---

## Criterios de Aceptación

✅ Cálculo automático de CO₂ evitado al crear reservas
✅ Diferentes factores de emisión según tipo de vehículo
✅ Endpoint para ver impacto ambiental del trayecto
✅ Endpoint para estadísticas personales de CO₂
✅ Equivalencias ambientales comprensibles (árboles, km, vuelos)
✅ Mensajes motivacionales según cantidad de CO₂
✅ Script de migración para trayectos existentes

---

## Mejoras Futuras

- Dashboard de impacto colectivo (CO₂ total evitado por todos los usuarios)
- Badges/logros por hitos de CO₂ evitado
- Comparación con transporte público
- Certificados de impacto ambiental descargables
- Integración con APIs de compensación de carbono
- Gráficos de evolución temporal del impacto

---

## Próximo Paso

Una vez completado RF-BONUS-002, proceder con:
- **RF-BONUS-003**: Visualización de Reservas de Otros Usuarios
