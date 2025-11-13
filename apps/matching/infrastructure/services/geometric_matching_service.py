"""Geometric matching service for advanced route compatibility."""
from typing import Optional
from apps.maps.domain.models import Coordinates
from apps.matching.infrastructure.services.distance_calculator import DistanceCalculator
from apps.trips.domain.models import Trip


class GeometricMatchingService:
    """
    Specialized service for advanced geographic matching.
    Improves upon basic RF-006 matching with precise geometric calculations.
    """

    def __init__(self):
        self.calculator = DistanceCalculator()

    def is_pickup_compatible(
        self,
        pickup_location: Coordinates,
        trip: Trip,
        max_deviation_km: float = 10.0
    ) -> bool:
        """
        Check if pickup location is compatible with trip route.

        Uses perpendicular distance to route segment for precision.

        Args:
            pickup_location: Passenger pickup coordinates
            trip: Trip to evaluate
            max_deviation_km: Maximum allowed deviation (default: 10 km)

        Returns:
            True if pickup is near the route
        """
        # Validate trip has coordinates
        if not (trip.origin_lat and trip.origin_lng and
                trip.destination_lat and trip.destination_lng):
            return False

        trip_origin = Coordinates(latitude=trip.origin_lat, longitude=trip.origin_lng)
        trip_dest = Coordinates(latitude=trip.destination_lat, longitude=trip.destination_lng)

        # Calculate perpendicular distance to route segment
        distance = self.calculator.point_to_segment_distance(
            pickup_location,
            trip_origin,
            trip_dest
        )

        return distance <= max_deviation_km

    def is_dropoff_compatible(
        self,
        dropoff_location: Coordinates,
        trip: Trip,
        max_deviation_km: float = 10.0
    ) -> bool:
        """
        Check if dropoff location is compatible with trip route.

        Same algorithm as pickup but for destination.

        Args:
            dropoff_location: Passenger dropoff coordinates
            trip: Trip to evaluate
            max_deviation_km: Maximum allowed deviation (default: 10 km)

        Returns:
            True if dropoff is near the route
        """
        if not (trip.origin_lat and trip.origin_lng and
                trip.destination_lat and trip.destination_lng):
            return False

        trip_origin = Coordinates(latitude=trip.origin_lat, longitude=trip.origin_lng)
        trip_dest = Coordinates(latitude=trip.destination_lat, longitude=trip.destination_lng)

        distance = self.calculator.point_to_segment_distance(
            dropoff_location,
            trip_origin,
            trip_dest
        )

        return distance <= max_deviation_km

    def calculate_route_compatibility_score(
        self,
        pickup: Coordinates,
        dropoff: Coordinates,
        trip: Trip
    ) -> float:
        """
        Calculate geographic compatibility score (0-100).

        Factors:
        - Distance from pickup to route
        - Distance from dropoff to route
        - Combined distance evaluation

        Args:
            pickup: Pickup coordinates
            dropoff: Dropoff coordinates
            trip: Trip to evaluate

        Returns:
            Score 0-100 (higher is better)
        """
        if not (trip.origin_lat and trip.origin_lng and
                trip.destination_lat and trip.destination_lng):
            return 0.0

        trip_origin = Coordinates(latitude=trip.origin_lat, longitude=trip.origin_lng)
        trip_dest = Coordinates(latitude=trip.destination_lat, longitude=trip.destination_lng)

        # Distance from pickup to route
        pickup_distance = self.calculator.point_to_segment_distance(
            pickup, trip_origin, trip_dest
        )

        # Distance from dropoff to route
        dropoff_distance = self.calculator.point_to_segment_distance(
            dropoff, trip_origin, trip_dest
        )

        # Score based on proximity (lower distance = higher score)
        total_distance = pickup_distance + dropoff_distance

        if total_distance <= 2:
            return 100.0
        elif total_distance <= 5:
            return 95.0
        elif total_distance <= 10:
            return 85.0
        elif total_distance <= 15:
            return 70.0
        elif total_distance <= 20:
            return 50.0
        elif total_distance <= 30:
            return 30.0
        else:
            return max(0, 30 - (total_distance - 30) * 2)

    def search_trips_by_location(
        self,
        location: Coordinates,
        radius_km: float,
        trips: list[Trip]
    ) -> list[Trip]:
        """
        Search trips that pass near a specific location.

        Args:
            location: Reference location
            radius_km: Search radius
            trips: List of trips to filter

        Returns:
            Trips with origin, destination, or route within radius
        """
        compatible_trips = []

        for trip in trips:
            if not (trip.origin_lat and trip.origin_lng and
                    trip.destination_lat and trip.destination_lng):
                continue

            trip_origin = Coordinates(latitude=trip.origin_lat, longitude=trip.origin_lng)
            trip_dest = Coordinates(latitude=trip.destination_lat, longitude=trip.destination_lng)

            # Check if origin or destination are within radius
            origin_in_range = self.calculator.is_within_radius(
                location, trip_origin, radius_km
            )
            dest_in_range = self.calculator.is_within_radius(
                location, trip_dest, radius_km
            )

            # Or if the route passes near the location
            distance_to_route = self.calculator.point_to_segment_distance(
                location, trip_origin, trip_dest
            )
            route_passes_nearby = distance_to_route <= radius_km

            if origin_in_range or dest_in_range or route_passes_nearby:
                compatible_trips.append(trip)

        return compatible_trips
