"""FastAPI dependency injection for User management.

This module provides dependency injection functions for FastAPI endpoints,
including repository instances and authentication validation.
"""
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_async_session
from apps.users.domain.models import User
from apps.users.domain.repositories.user_repository import IUserRepository
from apps.users.infrastructure.repositories.user_repository import UserRepository
from apps.users.infrastructure.auth.jwt import decode_access_token

# OAuth2 scheme for token extraction from Authorization header
# tokenUrl points to the login endpoint
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_user_repository(
    session: Annotated[AsyncSession, Depends(get_async_session)]
) -> IUserRepository:
    """
    Dependency that provides UserRepository instance.

    Args:
        session: SQLAlchemy async session (injected)

    Returns:
        IUserRepository implementation (UserRepository)

    Example:
        >>> @router.get("/users")
        >>> async def list_users(repo: Annotated[IUserRepository, Depends(get_user_repository)]):
        ...     return await repo.get_all()
    """
    return UserRepository(session)


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    repo: Annotated[IUserRepository, Depends(get_user_repository)]
) -> User:
    """
    Dependency that extracts and validates current user from JWT token.

    This is used to protect endpoints that require authentication.
    It extracts the token from the Authorization header, validates it,
    fetches the user from the database, and returns the User entity.

    Args:
        token: JWT token from Authorization header (extracted by oauth2_scheme)
        repo: User repository for database lookup

    Returns:
        Current User entity

    Raises:
        HTTPException 401: If token is invalid or user not found
        HTTPException 403: If user account is inactive

    Example:
        >>> @router.get("/profile")
        >>> async def get_profile(user: Annotated[User, Depends(get_current_user)]):
        ...     return {"email": user.email, "name": user.name}
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Decode token
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    # Extract user ID from token payload
    user_id_str: str = payload.get("sub")
    if user_id_str is None:
        raise credentials_exception

    try:
        user_id = int(user_id_str)
    except ValueError:
        raise credentials_exception

    # Fetch user from database
    user = await repo.get_by_id(user_id)
    if user is None:
        raise credentials_exception

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """
    Dependency that ensures current user is active.

    This is redundant with get_current_user but provided for clarity.

    Args:
        current_user: User from get_current_user dependency

    Returns:
        Active User entity

    Raises:
        HTTPException 403: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user
