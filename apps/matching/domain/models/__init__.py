"""Domain models for matching."""
from apps.matching.domain.models.travel_request import TravelRequest, TravelRequestStatus
from apps.matching.domain.models.match_result import MatchResult, MatchScore, WaypointInsertion

__all__ = [
    "TravelRequest",
    "TravelRequestStatus",
    "MatchResult",
    "MatchScore",
    "WaypointInsertion",
]
