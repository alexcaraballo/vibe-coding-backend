"""SQLAlchemy implementation of User repository.

This module provides concrete implementation of IUserRepository using
SQLAlchemy async sessions for database operations.
"""
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.users.domain.models import User
from apps.users.domain.repositories.user_repository import IUserRepository
from apps.users.infrastructure.persistence.models import UserORM


class UserRepository(IUserRepository):
    """
    SQLAlchemy implementation of IUserRepository.

    Uses async SQLAlchemy session for all database operations.
    Converts between ORM models (UserORM) and domain entities (User).
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize repository with async session.

        Args:
            session: SQLAlchemy async session (injected by FastAPI)
        """
        self._session = session

    async def create(self, user: User) -> User:
        """Create new user in database."""
        user_orm = UserORM.from_domain(user)

        self._session.add(user_orm)
        await self._session.commit()
        await self._session.refresh(user_orm)

        return user_orm.to_domain()

    async def get_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        stmt = select(UserORM).where(UserORM.id == user_id)
        result = await self._session.execute(stmt)
        user_orm = result.scalar_one_or_none()

        return user_orm.to_domain() if user_orm else None

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email (case-insensitive)."""
        stmt = select(UserORM).where(UserORM.email == email.lower())
        result = await self._session.execute(stmt)
        user_orm = result.scalar_one_or_none()

        return user_orm.to_domain() if user_orm else None

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[User]:
        """List users with pagination."""
        stmt = select(UserORM).offset(skip).limit(limit).order_by(UserORM.created_at.desc())
        result = await self._session.execute(stmt)
        user_orms = result.scalars().all()

        return [user_orm.to_domain() for user_orm in user_orms]

    async def update(self, user_id: int, user: User) -> bool:
        """Update existing user."""
        stmt = select(UserORM).where(UserORM.id == user_id)
        result = await self._session.execute(stmt)
        user_orm = result.scalar_one_or_none()

        if not user_orm:
            return False

        # Update fields
        user_orm.name = user.name
        user_orm.phone = user.phone
        user_orm.role = user.role.value
        user_orm.is_active = user.is_active
        user_orm.is_verified = user.is_verified
        user_orm.vehicle_model = user.vehicle_model
        user_orm.vehicle_plate = user.vehicle_plate
        user_orm.license_number = user.license_number
        user_orm.updated_at = datetime.utcnow()

        await self._session.commit()
        return True

    async def delete(self, user_id: int) -> bool:
        """Soft delete user (mark as inactive)."""
        stmt = select(UserORM).where(UserORM.id == user_id)
        result = await self._session.execute(stmt)
        user_orm = result.scalar_one_or_none()

        if not user_orm:
            return False

        user_orm.is_active = False
        user_orm.updated_at = datetime.utcnow()

        await self._session.commit()
        return True

    async def email_exists(self, email: str) -> bool:
        """Check if email already exists."""
        stmt = select(UserORM.id).where(UserORM.email == email.lower())
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None
