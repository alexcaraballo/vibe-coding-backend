"""Matching service implementation - with geometric matching improvements."""
from typing import Optional
from datetime import time as time_type
from fastapi import HTTPException, status

from apps.matching.domain.models import TravelRequest, MatchResult, MatchScore, WaypointInsertion, TravelRequestStatus
from apps.matching.domain.services.matching_service import IMatchingService
from apps.matching.infrastructure.services.detour_calculator import DetourCalculator
from apps.matching.infrastructure.services.geometric_matching_service import GeometricMatchingService
from apps.trips.domain.repositories.trip_repository import ITripRepository
from apps.trips.domain.repositories.booking_repository import IBookingRepository
from apps.matching.domain.repositories.travel_request_repository import ITravelRequestRepository
from apps.maps.domain.models import Coordinates


class MatchingService(IMatchingService):
    """Matching service with improved geometric calculations"""

    def __init__(self, trip_repo: ITripRepository, booking_repo: IBookingRepository, travel_request_repo: ITravelRequestRepository):
        self.trip_repo = trip_repo
        self.booking_repo = booking_repo
        self.travel_request_repo = travel_request_repo
        self.calculator = DetourCalculator()
        self.geometric_service = GeometricMatchingService()  # NEW: Geometric matching

    async def find_compatible_trips(self, travel_request: TravelRequest) -> list[MatchResult]:
        """Encuentra trayectos compatibles"""
        trips = await self.trip_repo.search(date_from=travel_request.travel_date, skip=0, limit=1000)
        trips = [t for t in trips if t.status == "active" and t.available_seats >= travel_request.seats_requested]

        results = []
        for trip in trips:
            result = await self._evaluate_trip(travel_request, trip)
            if result:
                results.append(result)

        compatible_results = [r for r in results if r.is_compatible]
        compatible_results.sort(key=lambda r: r.match_score.score if r.match_score else 0, reverse=True)
        return compatible_results

    async def _evaluate_trip(self, travel_request: TravelRequest, trip) -> Optional[MatchResult]:
        """Evalúa compatibilidad de un trayecto"""
        # Temporal compatibility
        if travel_request.time_from or travel_request.time_to:
            if not self._is_time_compatible(trip.departure_time, travel_request.time_from, travel_request.time_to):
                return MatchResult(trip_id=trip.id, is_compatible=False, reason="Horario no compatible",
                                   trip_origin=trip.origin, trip_destination=trip.destination,
                                   departure_time=trip.departure_time, available_seats=trip.available_seats,
                                   current_detour_minutes=trip.current_detour_minutes,
                                   max_detour_minutes=trip.max_detour_minutes, driver_id=trip.driver_id)

        # Geographic validation
        if not (trip.origin_lat and trip.origin_lng and trip.destination_lat and trip.destination_lng):
            return MatchResult(trip_id=trip.id, is_compatible=False, reason="Trayecto sin coordenadas",
                               trip_origin=trip.origin, trip_destination=trip.destination,
                               departure_time=trip.departure_time, available_seats=trip.available_seats,
                               current_detour_minutes=trip.current_detour_minutes,
                               max_detour_minutes=trip.max_detour_minutes, driver_id=trip.driver_id)

        request_origin = Coordinates(latitude=travel_request.origin_lat, longitude=travel_request.origin_lng)
        request_dest = Coordinates(latitude=travel_request.destination_lat, longitude=travel_request.destination_lng)

        # IMPROVED: Use geometric matching for more precise route compatibility
        pickup_compatible = self.geometric_service.is_pickup_compatible(
            request_origin, trip, max_deviation_km=15.0
        )

        if not pickup_compatible:
            return MatchResult(trip_id=trip.id, is_compatible=False,
                               reason="Origen demasiado lejos de la ruta (cálculo geométrico preciso)",
                               trip_origin=trip.origin, trip_destination=trip.destination,
                               departure_time=trip.departure_time, available_seats=trip.available_seats,
                               current_detour_minutes=trip.current_detour_minutes,
                               max_detour_minutes=trip.max_detour_minutes, driver_id=trip.driver_id)

        dropoff_compatible = self.geometric_service.is_dropoff_compatible(
            request_dest, trip, max_deviation_km=15.0
        )

        if not dropoff_compatible:
            return MatchResult(trip_id=trip.id, is_compatible=False,
                               reason="Destino demasiado lejos de la ruta (cálculo geométrico preciso)",
                               trip_origin=trip.origin, trip_destination=trip.destination,
                               departure_time=trip.departure_time, available_seats=trip.available_seats,
                               current_detour_minutes=trip.current_detour_minutes,
                               max_detour_minutes=trip.max_detour_minutes, driver_id=trip.driver_id)

        # Detour calculation (recalculate coordinates for detour)
        trip_origin = Coordinates(latitude=trip.origin_lat, longitude=trip.origin_lng)
        trip_dest = Coordinates(latitude=trip.destination_lat, longitude=trip.destination_lng)

        detour_dist_pickup = self.calculator.haversine_distance(trip_origin, request_origin)
        detour_dist_dropoff = self.calculator.haversine_distance(request_dest, trip_dest)
        total_detour_km = detour_dist_pickup + detour_dist_dropoff
        additional_detour_minutes = self.calculator.estimate_detour_minutes(total_detour_km)
        projected_total = trip.current_detour_minutes + additional_detour_minutes

        if projected_total > trip.max_detour_minutes:
            return MatchResult(trip_id=trip.id, is_compatible=False,
                               reason=f"Desvío excedido: {projected_total} > {trip.max_detour_minutes} min",
                               trip_origin=trip.origin, trip_destination=trip.destination,
                               departure_time=trip.departure_time, available_seats=trip.available_seats,
                               current_detour_minutes=trip.current_detour_minutes,
                               max_detour_minutes=trip.max_detour_minutes,
                               additional_detour_minutes=additional_detour_minutes,
                               projected_total_detour=projected_total, driver_id=trip.driver_id)

        # IMPROVED: Calculate scores using geometric route compatibility
        geographic_score = self.geometric_service.calculate_route_compatibility_score(
            request_origin, request_dest, trip
        )
        time_score = self._calculate_time_score(trip.departure_time, travel_request.time_from, travel_request.time_to)
        final_score = (geographic_score * 0.6 + time_score * 0.4)

        proposed_insertion = WaypointInsertion(
            pickup_index=0, dropoff_index=1,
            pickup_location={"lat": request_origin.latitude, "lng": request_origin.longitude, "address": travel_request.origin_address},
            dropoff_location={"lat": request_dest.latitude, "lng": request_dest.longitude, "address": travel_request.destination_address},
            additional_detour_minutes=additional_detour_minutes
        )

        match_score = MatchScore(trip_id=trip.id, score=final_score, detour_additional=additional_detour_minutes,
                                 proximity_score=geographic_score, time_compatibility_score=time_score)

        return MatchResult(trip_id=trip.id, is_compatible=True, trip_origin=trip.origin, trip_destination=trip.destination,
                           departure_time=trip.departure_time, available_seats=trip.available_seats,
                           current_detour_minutes=trip.current_detour_minutes, max_detour_minutes=trip.max_detour_minutes,
                           additional_detour_minutes=additional_detour_minutes, projected_total_detour=projected_total,
                           proposed_insertion=proposed_insertion, match_score=match_score, driver_id=trip.driver_id)

    def _is_time_compatible(self, trip_time: time_type, time_from: Optional[time_type], time_to: Optional[time_type]) -> bool:
        if time_from and trip_time < time_from:
            return False
        if time_to and trip_time > time_to:
            return False
        return True

    def _calculate_proximity_score(self, pickup_dist_km: float, dropoff_dist_km: float) -> float:
        total_dist = pickup_dist_km + dropoff_dist_km
        if total_dist <= 5:
            return 100.0
        elif total_dist <= 10:
            return 90.0
        elif total_dist <= 20:
            return 70.0
        elif total_dist <= 30:
            return 50.0
        else:
            return max(0, 50 - (total_dist - 30))

    def _calculate_time_score(self, trip_time: time_type, time_from: Optional[time_type], time_to: Optional[time_type]) -> float:
        if not time_from and not time_to:
            return 100.0
        if time_from and time_to:
            return 100.0 if time_from <= trip_time <= time_to else 50.0
        if time_from:
            return 100.0 if trip_time >= time_from else 50.0
        if time_to:
            return 100.0 if trip_time <= time_to else 50.0
        return 100.0

    async def evaluate_compatibility(self, travel_request: TravelRequest, trip_id: int) -> Optional[MatchResult]:
        """Evalúa un trayecto específico"""
        trip = await self.trip_repo.get_by_id(trip_id)
        if not trip:
            return None
        return await self._evaluate_trip(travel_request, trip)

    async def accept_match(self, travel_request_id: int, trip_id: int, passenger_id: int) -> bool:
        """Acepta un match y crea booking"""
        travel_request = await self.travel_request_repo.get_by_id(travel_request_id)
        if not travel_request:
            raise HTTPException(status_code=404, detail="Petición no encontrada")
        if travel_request.passenger_id != passenger_id:
            raise HTTPException(status_code=403, detail="No autorizado")

        match_result = await self.evaluate_compatibility(travel_request, trip_id)
        if not match_result or not match_result.is_compatible:
            raise HTTPException(status_code=400, detail="El trayecto ya no es compatible")

        # Create booking using booking service
        from apps.trips.infrastructure.services.booking_service import BookingService
        booking_service = BookingService(self.booking_repo, self.trip_repo)
        await booking_service.create_booking(trip_id=trip_id, passenger_id=passenger_id,
                                            seats_requested=travel_request.seats_requested,
                                            passenger_notes=travel_request.passenger_notes)

        # Update trip detour
        trip = await self.trip_repo.get_by_id(trip_id)
        if trip:
            trip.current_detour_minutes += match_result.additional_detour_minutes
            await self.trip_repo.update(trip_id, trip)

        # Update travel request
        travel_request.status = TravelRequestStatus.ACCEPTED
        travel_request.matched_trip_id = trip_id
        await self.travel_request_repo.update(travel_request_id, travel_request)

        return True
