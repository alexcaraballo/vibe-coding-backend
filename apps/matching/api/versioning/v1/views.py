"""FastAPI endpoints for matching."""
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, status

from apps.matching.domain.models import TravelRequest
from apps.matching.domain.services.matching_service import IMatchingService
from apps.matching.domain.repositories.travel_request_repository import ITravelRequestRepository
from apps.matching.infrastructure.dependencies import get_matching_service, get_travel_request_repository
from apps.matching.api.versioning.v1.schemas.requests import CreateTravelRequestRequest, AcceptMatchRequest
from apps.matching.api.versioning.v1.schemas.responses import TravelRequestResponse, MatchListResponse, MatchResultResponse
from apps.users.infrastructure.dependencies import get_current_active_user
from apps.users.domain.models import User
from apps.maps.domain.services.map_service import IMapService
from apps.maps.infrastructure.dependencies import get_map_service
from apps.trips.domain.repositories.trip_repository import ITripRepository
from apps.trips.infrastructure.dependencies import get_trip_repository

router = APIRouter()


@router.post("/travel-requests", response_model=TravelRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_travel_request(
    payload: CreateTravelRequestRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    travel_request_repo: Annotated[ITravelRequestRepository, Depends(get_travel_request_repository)],
    map_service: Annotated[IMapService, Depends(get_map_service)]
):
    """Crear petición de viaje y geocodificar ubicaciones"""
    origin_coords = await map_service.geocode(payload.origin_address)
    if not origin_coords:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No se encontró origen: {payload.origin_address}")

    dest_coords = await map_service.geocode(payload.destination_address)
    if not dest_coords:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No se encontró destino: {payload.destination_address}")

    travel_request = TravelRequest(
        passenger_id=current_user.id,
        origin_lat=origin_coords.latitude,
        origin_lng=origin_coords.longitude,
        destination_lat=dest_coords.latitude,
        destination_lng=dest_coords.longitude,
        origin_address=payload.origin_address,
        destination_address=payload.destination_address,
        travel_date=payload.travel_date,
        time_from=payload.time_from,
        time_to=payload.time_to,
        seats_requested=payload.seats_requested,
        passenger_notes=payload.passenger_notes
    )

    created = await travel_request_repo.create(travel_request)
    return TravelRequestResponse(**created.__dict__)


@router.get("/travel-requests/{request_id}/matches", response_model=MatchListResponse)
async def find_matches(
    request_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    matching_service: Annotated[IMatchingService, Depends(get_matching_service)],
    travel_request_repo: Annotated[ITravelRequestRepository, Depends(get_travel_request_repository)]
):
    """Encontrar trayectos compatibles para una petición"""
    travel_request = await travel_request_repo.get_by_id(request_id)
    if not travel_request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Petición de viaje no encontrada")

    if travel_request.passenger_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado")

    matches = await matching_service.find_compatible_trips(travel_request)

    return MatchListResponse(
        travel_request_id=request_id,
        matches=[MatchResultResponse(**m.model_dump()) for m in matches],
        total_matches=len(matches)
    )


@router.post("/travel-requests/{request_id}/accept", status_code=status.HTTP_201_CREATED)
async def accept_match(
    request_id: int,
    payload: AcceptMatchRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    matching_service: Annotated[IMatchingService, Depends(get_matching_service)]
):
    """Aceptar un match y crear reserva"""
    success = await matching_service.accept_match(
        travel_request_id=request_id,
        trip_id=payload.trip_id,
        passenger_id=current_user.id
    )

    if not success:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="No se pudo aceptar el match")

    return {"message": "Match aceptado exitosamente", "trip_id": payload.trip_id}


@router.get("/my-travel-requests", response_model=list[TravelRequestResponse])
async def get_my_travel_requests(
    current_user: Annotated[User, Depends(get_current_active_user)],
    travel_request_repo: Annotated[ITravelRequestRepository, Depends(get_travel_request_repository)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500)
):
    """Listar mis peticiones de viaje"""
    requests = await travel_request_repo.get_by_passenger(current_user.id, skip=skip, limit=limit)
    return [TravelRequestResponse(**r.__dict__) for r in requests]


@router.get("/search-by-location")
async def search_trips_by_location(
    trip_repo: Annotated[ITripRepository, Depends(get_trip_repository)],
    lat: float = Query(..., ge=-90, le=90, description="Latitud de la ubicación"),
    lng: float = Query(..., ge=-180, le=180, description="Longitud de la ubicación"),
    radius_km: float = Query(20.0, ge=1, le=100, description="Radio de búsqueda en kilómetros")
):
    """
    Buscar trayectos que pasen cerca de una ubicación específica.

    **Endpoint:** `GET /matching/v1/search-by-location?lat=36.5&lng=-6.2&radius_km=20`

    **Características:**
    - Búsqueda geográfica por radio
    - Encuentra trayectos cuya ruta pasa cerca de la ubicación
    - Útil para descubrimiento de rutas alternativas

    **Uso:**
    Usuario en Jerez busca viajes que pasen cerca de su ubicación actual.
    """
    from apps.maps.domain.models import Coordinates
    from apps.matching.infrastructure.services.geometric_matching_service import GeometricMatchingService
    from apps.trips.api.versioning.v1.schemas.responses import TripResponse

    location = Coordinates(latitude=lat, longitude=lng)

    # Get all active trips (limited for performance)
    all_trips = await trip_repo.search(skip=0, limit=1000)
    active_trips = [t for t in all_trips if t.status == "active"]

    # Filter by geographic proximity
    geometric_service = GeometricMatchingService()
    nearby_trips = geometric_service.search_trips_by_location(
        location, radius_km, active_trips
    )

    return [TripResponse(**t.__dict__) for t in nearby_trips]
