"""CO2 calculation service implementation."""
from typing import Optional
from apps.trips.domain.models import Trip
from apps.trips.domain.services.co2_service import ICO2Service
from apps.trips.domain.repositories.trip_repository import ITripRepository
from apps.trips.domain.repositories.booking_repository import IBookingRepository
from apps.maps.domain.services.map_service import IMapService
from apps.maps.domain.models import Coordinates


class CO2Calculator(ICO2Service):
    """Implementation of CO2 calculation service."""

    def __init__(
        self,
        trip_repo: ITripRepository,
        booking_repo: IBookingRepository,
        map_service: IMapService
    ):
        self.trip_repo = trip_repo
        self.booking_repo = booking_repo
        self.map_service = map_service

    async def calculate_trip_distance(self, trip: Trip) -> float:
        """
        Calculate the distance of a trip in kilometers using OSRM routing.

        Args:
            trip: Trip to calculate distance for

        Returns:
            Distance in kilometers, or 0 if calculation fails
        """
        if not (trip.origin_lat and trip.origin_lng and
                trip.destination_lat and trip.destination_lng):
            # No coordinates available, cannot calculate
            return 0.0

        origin = Coordinates(latitude=trip.origin_lat, longitude=trip.origin_lng)
        destination = Coordinates(latitude=trip.destination_lat, longitude=trip.destination_lng)

        try:
            route = await self.map_service.get_route(origin, destination)
            if route and route.distance_km:
                return route.distance_km
        except Exception:
            # If routing fails, use haversine as fallback
            pass

        # Fallback: use haversine distance (straight line) * 1.3 (detour factor)
        from apps.matching.infrastructure.services.distance_calculator import DistanceCalculator
        calculator = DistanceCalculator()
        straight_distance = calculator.haversine_distance(origin, destination)
        return straight_distance * 1.3  # Apply detour factor

    async def calculate_and_update_co2(self, trip: Trip) -> Trip:
        """
        Calculate CO2 savings for a trip and update the trip entity.

        Args:
            trip: Trip to calculate CO2 for

        Returns:
            Updated trip with CO2 calculations
        """
        # Calculate distance if not already set
        if not trip.distance_km or trip.distance_km <= 0:
            trip.distance_km = await self.calculate_trip_distance(trip)

        # Calculate CO2 using the domain method
        trip.calculate_co2_savings()

        return trip

    async def get_user_co2_stats(self, user_id: int) -> dict:
        """
        Get CO2 statistics for a user (driver or passenger).

        Returns statistics based on:
        - Trips as driver: all CO2 saved from those trips
        - Trips as passenger: CO2 per seat for booked trips

        Args:
            user_id: User ID

        Returns:
            Dictionary with CO2 statistics
        """
        # Get trips where user is driver
        driver_trips = await self.trip_repo.get_by_driver(user_id, skip=0, limit=10000)

        # Calculate CO2 from driver trips
        total_co2_driver = sum(
            trip.total_co2_saved_kg or 0
            for trip in driver_trips
            if trip.status.value == "completed"
        )
        driver_trips_count = len([t for t in driver_trips if t.status.value == "completed"])

        # Get bookings where user is passenger
        passenger_bookings = await self.booking_repo.get_by_passenger(user_id, skip=0, limit=10000)

        # Calculate CO2 from passenger bookings
        total_co2_passenger = 0.0
        passenger_trips_count = 0
        for booking in passenger_bookings:
            if booking.status.value == "completed":
                trip = await self.trip_repo.get_by_id(booking.trip_id)
                if trip and trip.co2_saved_per_passenger_kg:
                    total_co2_passenger += trip.co2_saved_per_passenger_kg * booking.seats_booked
                    passenger_trips_count += 1

        # Total statistics
        total_co2_saved_kg = total_co2_driver + total_co2_passenger
        total_trips_count = driver_trips_count + passenger_trips_count
        average_co2_per_trip_kg = (
            total_co2_saved_kg / total_trips_count
            if total_trips_count > 0
            else 0.0
        )

        # Calculate equivalences
        # 1 kg CO₂ ≈ 0.4 trees per year (approx)
        equivalence_trees = total_co2_saved_kg * 0.4

        # 1 kg CO₂ ≈ 5 km in average car (120g/km = 0.12kg/km → 1kg = 8.33km, round to 5)
        equivalence_km_not_driven = total_co2_saved_kg * 5.0

        return {
            "user_id": user_id,
            "total_co2_saved_kg": round(total_co2_saved_kg, 2),
            "trips_as_driver": driver_trips_count,
            "trips_as_passenger": passenger_trips_count,
            "total_trips": total_trips_count,
            "average_co2_per_trip_kg": round(average_co2_per_trip_kg, 2),
            "equivalence_trees": round(equivalence_trees, 1),
            "equivalence_km_not_driven": round(equivalence_km_not_driven, 1),
            "description": {
                "trees": f"Equivalente a plantar {round(equivalence_trees, 1)} árboles por un año",
                "km": f"Equivalente a no conducir {round(equivalence_km_not_driven, 1)} km en coche convencional"
            }
        }
