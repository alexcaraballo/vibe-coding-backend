"""FastAPI endpoints for maps management."""
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status

from apps.maps.domain.models import Coordinates
from apps.maps.domain.services.map_service import IMapService
from apps.maps.infrastructure.dependencies import get_map_service
from apps.maps.api.versioning.v1.schemas.requests import GeocodeRequest, RouteRequest
from apps.maps.api.versioning.v1.schemas.responses import (
    CoordinatesResponse,
    RouteResponse
)

# También necesitamos acceso a trips para obtener coordenadas
from apps.trips.domain.repositories.trip_repository import ITripRepository
from apps.trips.infrastructure.dependencies import get_trip_repository
from shared.exceptions import EntityNotFound

router = APIRouter()


@router.post("/geocode", response_model=CoordinatesResponse)
async def geocode_address(
    payload: GeocodeRequest,
    map_service: Annotated[IMapService, Depends(get_map_service)]
):
    """
    Geocodificar dirección (convertir a coordenadas).

    **Uso**: Convertir "Cádiz, España" a lat/lng
    """
    coordinates = await map_service.geocode(payload.address)

    if not coordinates:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontraron coordenadas para: {payload.address}"
        )

    return CoordinatesResponse(**coordinates.model_dump())


@router.post("/route", response_model=RouteResponse)
async def calculate_route(
    payload: RouteRequest,
    map_service: Annotated[IMapService, Depends(get_map_service)]
):
    """
    Calcular ruta entre dos puntos.

    **Opciones:**
    1. Proporcionar direcciones (origin_address, destination_address)
    2. Proporcionar coordenadas (origin_lat/lng, destination_lat/lng)

    **Retorna:**
    - Ruta con polyline (lista de coordenadas)
    - Distancia en km
    - Duración estimada en minutos
    """
    # Geocodificar si se proporcionaron direcciones
    if payload.origin_address:
        origin_coords = await map_service.geocode(payload.origin_address)
        if not origin_coords:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No se encontró origen: {payload.origin_address}"
            )
    elif payload.origin_lat and payload.origin_lng:
        origin_coords = Coordinates(
            latitude=payload.origin_lat,
            longitude=payload.origin_lng
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe proporcionar origin_address o origin_lat/lng"
        )

    if payload.destination_address:
        dest_coords = await map_service.geocode(payload.destination_address)
        if not dest_coords:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No se encontró destino: {payload.destination_address}"
            )
    elif payload.destination_lat and payload.destination_lng:
        dest_coords = Coordinates(
            latitude=payload.destination_lat,
            longitude=payload.destination_lng
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe proporcionar destination_address o destination_lat/lng"
        )

    # Calcular ruta
    route = await map_service.get_route(origin_coords, dest_coords)

    if not route:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo calcular la ruta"
        )

    return RouteResponse(**route.model_dump())


@router.get("/trip/{trip_id}/route", response_model=RouteResponse)
async def get_trip_route(
    trip_id: int,
    trip_repo: Annotated[ITripRepository, Depends(get_trip_repository)],
    map_service: Annotated[IMapService, Depends(get_map_service)]
):
    """
    Obtener ruta de un trayecto específico (RF-005).

    **Endpoint principal para RF-005:**
    - Obtiene trayecto por ID
    - Calcula ruta entre origen y destino
    - Retorna información completa de la ruta con polyline para visualización

    **No requiere autenticación** (búsqueda pública)
    """
    # Obtener trayecto
    trip = await trip_repo.get_by_id(trip_id)
    if not trip:
        raise EntityNotFound("Trip", trip_id)

    # Si el trayecto tiene coordenadas, usarlas directamente
    if (trip.origin_lat and trip.origin_lng and
        trip.destination_lat and trip.destination_lng):
        origin_coords = Coordinates(
            latitude=trip.origin_lat,
            longitude=trip.origin_lng
        )
        dest_coords = Coordinates(
            latitude=trip.destination_lat,
            longitude=trip.destination_lng
        )
    else:
        # Si no, geocodificar las direcciones
        origin_coords = await map_service.geocode(trip.origin)
        if not origin_coords:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No se pudo geocodificar origen: {trip.origin}"
            )

        dest_coords = await map_service.geocode(trip.destination)
        if not dest_coords:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No se pudo geocodificar destino: {trip.destination}"
            )

        # Actualizar trip con coordenadas (para futuras consultas)
        trip.origin_lat = origin_coords.latitude
        trip.origin_lng = origin_coords.longitude
        trip.destination_lat = dest_coords.latitude
        trip.destination_lng = dest_coords.longitude
        await trip_repo.update(trip_id, trip)

    # Calcular ruta
    route = await map_service.get_route(origin_coords, dest_coords)

    if not route:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo calcular la ruta"
        )

    return RouteResponse(**route.model_dump())
