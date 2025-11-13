"""Utility for calculating geographic detours."""
import math
from apps.maps.domain.models import Coordinates


class DetourCalculator:
    """Utilidad para calcular desvíos geográficos"""

    @staticmethod
    def haversine_distance(coord1: Coordinates, coord2: Coordinates) -> float:
        """
        Calcula distancia en km entre dos coordenadas usando fórmula de Haversine.

        Returns:
            Distancia en kilómetros
        """
        R = 6371  # Radio de la Tierra en km

        lat1 = math.radians(coord1.latitude)
        lat2 = math.radians(coord2.latitude)
        dlat = math.radians(coord2.latitude - coord1.latitude)
        dlon = math.radians(coord2.longitude - coord1.longitude)

        a = (math.sin(dlat / 2) ** 2 +
             math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2)
        c = 2 * math.asin(math.sqrt(a))

        return R * c

    @staticmethod
    def estimate_detour_minutes(distance_km: float, avg_speed_kmh: float = 80) -> int:
        """
        Estima tiempo de desvío en minutos.

        Args:
            distance_km: Distancia del desvío en km
            avg_speed_kmh: Velocidad promedio (default: 80 km/h)

        Returns:
            Tiempo estimado en minutos
        """
        hours = distance_km / avg_speed_kmh
        return int(hours * 60)

    @staticmethod
    def is_point_near_segment(
        point: Coordinates,
        segment_start: Coordinates,
        segment_end: Coordinates,
        threshold_km: float = 10.0
    ) -> bool:
        """
        Verifica si un punto está cerca de un segmento de ruta.

        Args:
            point: Punto a verificar
            segment_start: Inicio del segmento
            segment_end: Fin del segmento
            threshold_km: Distancia máxima en km (default: 10 km)

        Returns:
            True si el punto está cerca del segmento
        """
        # Calcular distancia del punto a ambos extremos
        dist_to_start = DetourCalculator.haversine_distance(point, segment_start)
        dist_to_end = DetourCalculator.haversine_distance(point, segment_end)

        # Si está cerca de alguno de los extremos, es compatible
        if dist_to_start <= threshold_km or dist_to_end <= threshold_km:
            return True

        # Verificar distancia perpendicular al segmento (simplificado)
        # Para MVP, usar promedio de distancias como aproximación
        avg_distance = (dist_to_start + dist_to_end) / 2
        return avg_distance <= threshold_km
