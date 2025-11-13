"""User repository interface.

This module defines the contract for User persistence operations.
Implementations can use any persistence technology (SQLAlchemy, MongoDB, etc.)
"""
from abc import ABC, abstractmethod
from typing import Optional, List

from apps.users.domain.models import User


class IUserRepository(ABC):
    """
    Repository contract for User persistence.

    This interface defines what operations are available for User entities.
    The infrastructure layer provides concrete implementations.
    """

    @abstractmethod
    async def create(self, user: User) -> User:
        """
        Create a new user in the database.

        Args:
            user: User entity (without id)

        Returns:
            User entity with assigned id

        Raises:
            Exception: If email already exists or other constraint violation
        """
        pass

    @abstractmethod
    async def get_by_id(self, user_id: int) -> Optional[User]:
        """
        Retrieve user by ID.

        Args:
            user_id: User's primary key

        Returns:
            User entity if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Retrieve user by email address (for login).

        Args:
            email: User's email address

        Returns:
            User entity if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_all(self, skip: int = 0, limit: int = 100) -> List[User]:
        """
        List users with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of User entities
        """
        pass

    @abstractmethod
    async def update(self, user_id: int, user: User) -> bool:
        """
        Update existing user.

        Args:
            user_id: User's primary key
            user: User entity with updated data

        Returns:
            True if user was updated, False if not found
        """
        pass

    @abstractmethod
    async def delete(self, user_id: int) -> bool:
        """
        Soft delete user (mark as inactive).

        Args:
            user_id: User's primary key

        Returns:
            True if user was deleted, False if not found
        """
        pass

    @abstractmethod
    async def email_exists(self, email: str) -> bool:
        """
        Check if email is already registered.

        Args:
            email: Email address to check

        Returns:
            True if email exists, False otherwise
        """
        pass
