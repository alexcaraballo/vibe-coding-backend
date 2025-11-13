"""Utility functions for the application."""
import uuid
from datetime import datetime, timezone
from typing import Any


def generate_uuid() -> str:
    """
    Generate a unique identifier.

    Returns:
        UUID string
    """
    return str(uuid.uuid4())


def utcnow() -> datetime:
    """
    Get current UTC datetime.

    Returns:
        Current datetime in UTC
    """
    return datetime.now(timezone.utc)


def to_dict(obj: Any, exclude: list[str] = None) -> dict:
    """
    Convert an object to dictionary, excluding specified fields.

    Args:
        obj: Object to convert
        exclude: List of field names to exclude

    Returns:
        Dictionary representation of the object
    """
    exclude = exclude or []
    if hasattr(obj, '__dict__'):
        return {
            key: value
            for key, value in obj.__dict__.items()
            if not key.startswith('_') and key not in exclude
        }
    return {}


def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format datetime to string.

    Args:
        dt: Datetime object to format
        format_str: Format string (default: YYYY-MM-DD HH:MM:SS)

    Returns:
        Formatted datetime string
    """
    return dt.strftime(format_str)


def calculate_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two coordinates using Haversine formula.

    Args:
        lat1: Latitude of first point
        lon1: Longitude of first point
        lat2: Latitude of second point
        lon2: Longitude of second point

    Returns:
        Distance in kilometers
    """
    from math import radians, sin, cos, sqrt, atan2

    # Earth radius in kilometers
    R = 6371.0

    # Convert to radians
    lat1_rad = radians(lat1)
    lon1_rad = radians(lon1)
    lat2_rad = radians(lat2)
    lon2_rad = radians(lon2)

    # Differences
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    # Haversine formula
    a = sin(dlat / 2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return R * c
