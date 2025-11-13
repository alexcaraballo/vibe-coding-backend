"""Advanced geometric calculations for matching."""
import math
from typing import Tuple
from apps.maps.domain.models import Coordinates


class DistanceCalculator:
    """
    Advanced geometric calculation service for matching.
    Provides precise distance calculations and route analysis.
    """

    @staticmethod
    def haversine_distance(coord1: Coordinates, coord2: Coordinates) -> float:
        """
        Calculate haversine distance between two coordinates.

        Args:
            coord1: First coordinate
            coord2: Second coordinate

        Returns:
            Distance in kilometers
        """
        R = 6371  # Earth radius in km

        lat1 = math.radians(coord1.latitude)
        lat2 = math.radians(coord2.latitude)
        dlat = math.radians(coord2.latitude - coord1.latitude)
        dlon = math.radians(coord2.longitude - coord1.longitude)

        a = (math.sin(dlat / 2) ** 2 +
             math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2)
        c = 2 * math.asin(math.sqrt(a))

        return R * c

    @staticmethod
    def point_to_segment_distance(
        point: Coordinates,
        segment_start: Coordinates,
        segment_end: Coordinates
    ) -> float:
        """
        Calculate perpendicular distance from point to line segment.

        Uses projection onto segment:
        1. If projection is inside segment: perpendicular distance
        2. If outside: distance to nearest endpoint

        Args:
            point: Point to measure from
            segment_start: Start of line segment
            segment_end: End of line segment

        Returns:
            Distance in kilometers
        """
        # Convert to approximate cartesian coordinates (valid for short distances)
        # For production, use precise spherical projection

        # Point P
        px = point.longitude
        py = point.latitude

        # Segment A-B
        ax = segment_start.longitude
        ay = segment_start.latitude
        bx = segment_end.longitude
        by = segment_end.latitude

        # Vector AB
        ab_x = bx - ax
        ab_y = by - ay

        # Vector AP
        ap_x = px - ax
        ap_y = py - ay

        # Dot product AB·AP
        ab_ap = ab_x * ap_x + ab_y * ap_y

        # Length squared of AB
        ab_len_sq = ab_x * ab_x + ab_y * ab_y

        # Avoid division by zero (A and B are the same point)
        if ab_len_sq == 0:
            return DistanceCalculator.haversine_distance(point, segment_start)

        # Projection parameter t (0 <= t <= 1 if inside segment)
        t = max(0, min(1, ab_ap / ab_len_sq))

        # Projected point on segment
        proj_x = ax + t * ab_x
        proj_y = ay + t * ab_y

        proj_point = Coordinates(latitude=proj_y, longitude=proj_x)

        # Distance from original point to projected point
        return DistanceCalculator.haversine_distance(point, proj_point)

    @staticmethod
    def is_within_radius(
        center: Coordinates,
        target: Coordinates,
        radius_km: float
    ) -> bool:
        """
        Check if target is within radius from center.

        Args:
            center: Center coordinate
            target: Target coordinate to check
            radius_km: Radius in kilometers

        Returns:
            True if target is within radius
        """
        distance = DistanceCalculator.haversine_distance(center, target)
        return distance <= radius_km

    @staticmethod
    def calculate_detour_for_waypoint(
        route_start: Coordinates,
        route_end: Coordinates,
        waypoint: Coordinates
    ) -> float:
        """
        Calculate additional detour when inserting a waypoint.

        Detour = (start_waypoint + waypoint_end) - (start_end)

        Args:
            route_start: Route origin
            route_end: Route destination
            waypoint: Waypoint to insert

        Returns:
            Detour distance in kilometers
        """
        # Original route distance
        original_distance = DistanceCalculator.haversine_distance(route_start, route_end)

        # Route with waypoint
        detour_distance = (
            DistanceCalculator.haversine_distance(route_start, waypoint) +
            DistanceCalculator.haversine_distance(waypoint, route_end)
        )

        # Detour is the difference
        return detour_distance - original_distance

    @staticmethod
    def find_closest_point_on_route(
        point: Coordinates,
        route_waypoints: list[Coordinates]
    ) -> Tuple[int, float]:
        """
        Find the closest segment on a multi-waypoint route.

        Args:
            point: Point to evaluate
            route_waypoints: List of route waypoints

        Returns:
            Tuple (segment_index, distance) where segment_index is the
            closest segment index and distance is in kilometers
        """
        if len(route_waypoints) < 2:
            return (0, float('inf'))

        min_distance = float('inf')
        closest_segment = 0

        for i in range(len(route_waypoints) - 1):
            segment_start = route_waypoints[i]
            segment_end = route_waypoints[i + 1]

            distance = DistanceCalculator.point_to_segment_distance(
                point, segment_start, segment_end
            )

            if distance < min_distance:
                min_distance = distance
                closest_segment = i

        return (closest_segment, min_distance)
