"""Trip domain models (Pure Python - no framework dependencies)."""
from dataclasses import dataclass, field
from datetime import datetime, date, time
from enum import Enum
from typing import Optional


class TripStatus(str, Enum):
    """Estados posibles de un trayecto."""
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class VehicleType(str, Enum):
    """Tipos de vehículo para cálculo de emisiones CO₂."""
    GASOLINE = "gasoline"
    DIESEL = "diesel"
    HYBRID = "hybrid"
    ELECTRIC = "electric"


class EmissionFactors:
    """
    Factores de emisión de CO₂ por tipo de vehículo.
    Valores en gramos de CO₂ por kilómetro (g/km).

    Fuentes:
    - IDAE (Instituto para la Diversificación y Ahorro de la Energía)
    - European Environment Agency
    """
    GASOLINE = 120.0  # g CO₂/km
    DIESEL = 105.0    # g CO₂/km
    HYBRID = 70.0     # g CO₂/km
    ELECTRIC = 0.0    # g CO₂/km (cero emisiones directas)

    @classmethod
    def get_factor(cls, vehicle_type: VehicleType) -> float:
        """Obtiene el factor de emisión para un tipo de vehículo."""
        mapping = {
            VehicleType.GASOLINE: cls.GASOLINE,
            VehicleType.DIESEL: cls.DIESEL,
            VehicleType.HYBRID: cls.HYBRID,
            VehicleType.ELECTRIC: cls.ELECTRIC,
        }
        return mapping.get(vehicle_type, cls.GASOLINE)  # Default: gasoline


@dataclass
class Trip:
    """
    Entidad Trip del dominio.
    Representa un trayecto publicado por un conductor.
    """
    # Información básica del trayecto
    origin: str
    destination: str
    departure_date: date
    departure_time: time

    # Gestión de plazas
    available_seats: int
    total_seats: int

    # Conductor
    driver_id: int  # Foreign key to users.id

    # Identificador (asignado por BD)
    id: Optional[int] = None

    # Coordenadas geográficas (para matching)
    origin_lat: Optional[float] = None
    origin_lng: Optional[float] = None
    destination_lat: Optional[float] = None
    destination_lng: Optional[float] = None

    # Motor de Matching (RF-006)
    estimated_arrival_time: Optional[time] = None
    max_detour_minutes: int = 30
    current_detour_minutes: int = 0

    # CO₂ Impact (RF-BONUS-002)
    vehicle_type: VehicleType = VehicleType.GASOLINE
    distance_km: Optional[float] = None  # Distancia total del trayecto
    co2_saved_per_passenger_kg: Optional[float] = None  # CO₂ evitado por pasajero
    total_co2_saved_kg: Optional[float] = None  # CO₂ total evitado (todos los pasajeros)

    # Metadatos
    status: TripStatus = TripStatus.ACTIVE
    price_per_seat: Optional[float] = None
    description: Optional[str] = None

    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        """Validate business rules on entity creation."""
        if len(self.origin) < 3:
            raise ValueError("Origin must be at least 3 characters")
        if len(self.destination) < 3:
            raise ValueError("Destination must be at least 3 characters")
        if self.available_seats < 0 or self.available_seats > 10:
            raise ValueError("Available seats must be between 0 and 10")
        if self.total_seats < 1 or self.total_seats > 10:
            raise ValueError("Total seats must be between 1 and 10")
        if self.available_seats > self.total_seats:
            raise ValueError("Available seats cannot exceed total seats")
        if self.price_per_seat is not None and self.price_per_seat < 0:
            raise ValueError("Price per seat cannot be negative")
        if self.max_detour_minutes < 0 or self.max_detour_minutes > 120:
            raise ValueError("Max detour minutes must be between 0 and 120")

    def has_available_seats(self) -> bool:
        """Verifica si hay plazas disponibles."""
        return self.available_seats > 0

    def can_accommodate(self, seats_requested: int) -> bool:
        """Verifica si puede acomodar N plazas."""
        return self.available_seats >= seats_requested

    def reserve_seats(self, seats: int) -> None:
        """
        Reserve seats (reduce available seats).
        Raises ValueError if not enough seats available.
        """
        if not self.can_accommodate(seats):
            raise ValueError(f"Cannot reserve {seats} seats. Only {self.available_seats} available.")
        self.available_seats -= seats

    def release_seats(self, seats: int) -> None:
        """
        Release seats (increase available seats after cancellation).
        Raises ValueError if would exceed total seats.
        """
        if self.available_seats + seats > self.total_seats:
            raise ValueError(f"Cannot release {seats} seats. Would exceed total seats.")
        self.available_seats += seats

    def calculate_co2_savings(self) -> None:
        """
        Calcula el CO₂ evitado por este trayecto.

        Fórmula:
        - CO₂_evitado_por_pasajero = distancia_km × emisiones_por_km
        - CO₂_total_evitado = CO₂_por_pasajero × num_pasajeros_ocupados

        El CO₂ se evita porque los pasajeros no toman vehículos individuales.
        Solo se calcula si existe la distancia del trayecto.
        """
        if not self.distance_km or self.distance_km <= 0:
            self.co2_saved_per_passenger_kg = None
            self.total_co2_saved_kg = None
            return

        # Obtener factor de emisión según tipo de vehículo
        emission_factor_g_per_km = EmissionFactors.get_factor(self.vehicle_type)

        # Calcular CO₂ evitado por pasajero (en kg)
        co2_per_passenger_g = self.distance_km * emission_factor_g_per_km
        self.co2_saved_per_passenger_kg = co2_per_passenger_g / 1000.0  # Convert g to kg

        # Calcular CO₂ total evitado (número de pasajeros ocupados)
        passengers_occupied = self.total_seats - self.available_seats
        self.total_co2_saved_kg = self.co2_saved_per_passenger_kg * passengers_occupied


class BookingStatus(str, Enum):
    """Estados posibles de una reserva."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


@dataclass
class Booking:
    """
    Entidad Booking del dominio.
    Representa una reserva de un pasajero en un trayecto.
    """
    # Relaciones
    trip_id: int  # Foreign key to trips.id
    passenger_id: int  # Foreign key to users.id

    # Detalles de la reserva
    seats_booked: int = 1

    # Identificador (asignado por BD)
    id: Optional[int] = None

    # Estado
    status: BookingStatus = BookingStatus.CONFIRMED

    # Información adicional
    pickup_location: Optional[str] = None
    dropoff_location: Optional[str] = None
    passenger_notes: Optional[str] = None

    # Metadatos
    booking_date: datetime = field(default_factory=datetime.utcnow)
    cancellation_date: Optional[datetime] = None
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        """Validate business rules on entity creation."""
        if self.seats_booked < 1 or self.seats_booked > 10:
            raise ValueError("Seats booked must be between 1 and 10")
        if self.passenger_notes and len(self.passenger_notes) > 500:
            raise ValueError("Passenger notes cannot exceed 500 characters")
        if self.pickup_location and len(self.pickup_location) > 200:
            raise ValueError("Pickup location cannot exceed 200 characters")
        if self.dropoff_location and len(self.dropoff_location) > 200:
            raise ValueError("Dropoff location cannot exceed 200 characters")

    def can_be_cancelled(self) -> bool:
        """Verifica si la reserva puede ser cancelada."""
        return self.status == BookingStatus.CONFIRMED and self.is_active

    def cancel(self) -> None:
        """Cancela la reserva."""
        if not self.can_be_cancelled():
            raise ValueError("Booking cannot be cancelled")
        self.status = BookingStatus.CANCELLED
        self.is_active = False
        self.cancellation_date = datetime.utcnow()
