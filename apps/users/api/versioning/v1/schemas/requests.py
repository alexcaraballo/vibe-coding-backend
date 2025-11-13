"""Pydantic request schemas for User API.

This module defines the structure of incoming HTTP requests
for user management endpoints.
"""
from pydantic import BaseModel, EmailStr, Field, field_validator

from apps.users.domain.models import UserRole


class RegisterRequest(BaseModel):
    """Schema for user registration request."""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., pattern=r"^\+?[1-9]\d{1,14}$")
    role: UserRole = Field(default=UserRole.PASSENGER)

    @field_validator("email")
    @classmethod
    def email_to_lowercase(cls, v: str) -> str:
        """Normalize email to lowercase."""
        return v.lower()

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "juan@example.com",
                "password": "SecurePassword123",
                "name": "Juan Pérez",
                "phone": "+34600000000",
                "role": "passenger"
            }
        }
    }


class LoginRequest(BaseModel):
    """Schema for login request (alternative to OAuth2PasswordRequestForm)."""

    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def email_to_lowercase(cls, v: str) -> str:
        """Normalize email to lowercase."""
        return v.lower()


class UpdateProfileRequest(BaseModel):
    """Schema for updating user profile (partial update)."""

    name: str | None = Field(None, min_length=2, max_length=100)
    phone: str | None = Field(None, pattern=r"^\+?[1-9]\d{1,14}$")
    vehicle_model: str | None = Field(None, max_length=100)
    vehicle_plate: str | None = Field(None, max_length=20)
    license_number: str | None = Field(None, max_length=50)

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Juan Pérez Updated",
                "phone": "+34600000001",
                "vehicle_model": "Toyota Corolla",
                "vehicle_plate": "ABC-1234",
                "license_number": "B-12345678"
            }
        }
    }
