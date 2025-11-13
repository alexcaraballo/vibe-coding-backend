"""Response schemas for matching API."""
from pydantic import BaseModel, ConfigDict
from datetime import datetime, date, time
from typing import Optional
from apps.matching.domain.models import TravelRequestStatus


class TravelRequestResponse(BaseModel):
    """Response de travel request"""
    id: int
    passenger_id: int
    origin_lat: float
    origin_lng: float
    destination_lat: float
    destination_lng: float
    origin_address: Optional[str]
    destination_address: Optional[str]
    travel_date: date
    time_from: Optional[time]
    time_to: Optional[time]
    seats_requested: int
    passenger_notes: Optional[str]
    status: str
    matched_trip_id: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class MatchScoreResponse(BaseModel):
    """Response de score de matching"""
    trip_id: int
    score: float
    detour_additional: int
    proximity_score: float
    time_compatibility_score: float


class WaypointInsertionResponse(BaseModel):
    """Response de inserción de waypoints"""
    pickup_index: int
    dropoff_index: int
    pickup_location: dict
    dropoff_location: dict
    additional_detour_minutes: int


class MatchResultResponse(BaseModel):
    """Response de resultado de matching"""
    trip_id: int
    is_compatible: bool
    reason: Optional[str]
    trip_origin: str
    trip_destination: str
    departure_time: time
    available_seats: int
    current_detour_minutes: int
    max_detour_minutes: int
    additional_detour_minutes: Optional[int]
    projected_total_detour: Optional[int]
    proposed_insertion: Optional[WaypointInsertionResponse]
    match_score: Optional[MatchScoreResponse]
    driver_id: int

    model_config = ConfigDict(from_attributes=True)


class MatchListResponse(BaseModel):
    """Lista de matches sugeridos"""
    travel_request_id: int
    matches: list[MatchResultResponse]
    total_matches: int
