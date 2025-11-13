"""Pydantic response schemas for User API.

This module defines the structure of outgoing HTTP responses
for user management endpoints.
"""
from datetime import datetime
from pydantic import BaseModel, EmailStr

from apps.users.domain.models import UserRole


class UserResponse(BaseModel):
    """Schema for user data in API responses."""

    id: int
    email: EmailStr
    name: str
    phone: str | None
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime

    # Driver-specific fields
    vehicle_model: str | None = None
    vehicle_plate: str | None = None
    license_number: str | None = None

    model_config = {
        "from_attributes": True,  # Enable ORM mode for SQLAlchemy models
        "json_schema_extra": {
            "example": {
                "id": 1,
                "email": "juan@example.com",
                "name": "Juan Pérez",
                "phone": "+34600000000",
                "role": "passenger",
                "is_active": True,
                "is_verified": False,
                "created_at": "2025-11-13T10:00:00Z",
                "vehicle_model": None,
                "vehicle_plate": None,
                "license_number": None
            }
        }
    }


class TokenResponse(BaseModel):
    """Schema for authentication response (login/register)."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse

    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "user": {
                    "id": 1,
                    "email": "juan@example.com",
                    "name": "Juan Pérez",
                    "phone": "+34600000000",
                    "role": "passenger",
                    "is_active": True,
                    "is_verified": False,
                    "created_at": "2025-11-13T10:00:00Z"
                }
            }
        }
    }
