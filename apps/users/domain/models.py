"""Domain models for User management.

This module contains pure Python domain entities with zero framework dependencies.
Following Clean Architecture principles, these entities represent business concepts.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class UserRole(str, Enum):
    """User roles in the carpooling system."""
    DRIVER = "driver"
    PASSENGER = "passenger"
    BOTH = "both"


@dataclass
class User:
    """
    User domain entity (pure Python, no framework dependencies).

    This is the core business representation of a User.
    It contains only business logic and validation rules.
    """
    email: str
    password_hash: str  # NEVER store plain passwords
    name: str
    role: UserRole

    # Optional fields
    id: Optional[int] = None
    phone: Optional[str] = None
    is_active: bool = True
    is_verified: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    # Driver-specific fields (only used when role is DRIVER or BOTH)
    vehicle_model: Optional[str] = None
    vehicle_plate: Optional[str] = None
    license_number: Optional[str] = None

    def __post_init__(self):
        """Validate business rules on entity creation."""
        if not self.email or "@" not in self.email:
            raise ValueError("Invalid email address")
        if len(self.name) < 2:
            raise ValueError("Name must be at least 2 characters")
        if not self.password_hash:
            raise ValueError("Password hash is required")

    def is_driver(self) -> bool:
        """Check if user can act as driver."""
        return self.role in (UserRole.DRIVER, UserRole.BOTH)

    def is_passenger(self) -> bool:
        """Check if user can act as passenger."""
        return self.role in (UserRole.PASSENGER, UserRole.BOTH)

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
