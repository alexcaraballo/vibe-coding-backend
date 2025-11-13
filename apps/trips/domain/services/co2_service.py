"""CO2 calculation service interface."""
from abc import ABC, abstractmethod
from typing import Optional
from apps.trips.domain.models import Trip


class ICO2Service(ABC):
    """Interface for CO2 calculation service."""

    @abstractmethod
    async def calculate_trip_distance(self, trip: Trip) -> float:
        """
        Calculate the distance of a trip in kilometers.

        Args:
            trip: Trip to calculate distance for

        Returns:
            Distance in kilometers
        """
        pass

    @abstractmethod
    async def calculate_and_update_co2(self, trip: Trip) -> Trip:
        """
        Calculate CO2 savings for a trip and update the trip entity.

        This method:
        1. Calculates the trip distance (if not already set)
        2. Calls trip.calculate_co2_savings() to update CO2 fields

        Args:
            trip: Trip to calculate CO2 for

        Returns:
            Updated trip with CO2 calculations
        """
        pass

    @abstractmethod
    async def get_user_co2_stats(self, user_id: int) -> dict:
        """
        Get CO2 statistics for a user (driver or passenger).

        Returns:
            Dictionary with:
            - total_co2_saved_kg: Total CO2 saved
            - trips_count: Number of trips
            - average_co2_per_trip_kg: Average CO2 per trip
            - equivalence_trees: Equivalent trees planted
            - equivalence_km_not_driven: Equivalent km not driven in average car
        """
        pass
