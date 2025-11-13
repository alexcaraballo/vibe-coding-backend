"""FastAPI endpoints for User management.

This module implements HTTP endpoints for user registration, authentication,
and profile management following REST principles.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from apps.users.domain.models import User
from apps.users.domain.repositories.user_repository import IUserRepository
from apps.users.infrastructure.dependencies import get_user_repository, get_current_user
from apps.users.infrastructure.auth.password import hash_password, verify_password
from apps.users.infrastructure.auth.jwt import create_access_token
from apps.users.api.versioning.v1.schemas.requests import (
    RegisterRequest,
    UpdateProfileRequest
)
from apps.users.api.versioning.v1.schemas.responses import (
    UserResponse,
    TokenResponse
)

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    repo: Annotated[IUserRepository, Depends(get_user_repository)]
):
    """
    Register new user account.

    Creates a new user with hashed password and returns JWT token.
    Email must be unique in the system.

    **Success Response:**
    - Status: 201 Created
    - Returns: JWT token and user profile

    **Error Responses:**
    - 400: Email already registered
    - 422: Validation error (invalid email, password too short, etc.)
    """
    # Check if email already exists
    if await repo.email_exists(payload.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create user entity
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        name=payload.name,
        phone=payload.phone,
        role=payload.role
    )

    # Persist to database
    created_user = await repo.create(user)

    # Generate JWT token
    access_token = create_access_token(data={"sub": str(created_user.id)})

    return TokenResponse(
        access_token=access_token,
        user=UserResponse.model_validate(created_user)
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    repo: Annotated[IUserRepository, Depends(get_user_repository)]
):
    """
    Authenticate user and return JWT token.

    Uses OAuth2PasswordRequestForm (form-data with username/password).
    Note: 'username' field contains email address.

    **Request Body (form-data):**
    - username: Email address
    - password: Plain password

    **Success Response:**
    - Status: 200 OK
    - Returns: JWT token and user profile

    **Error Responses:**
    - 401: Incorrect email or password
    - 403: User account is inactive
    """
    # Find user by email (OAuth2 uses 'username' field)
    user = await repo.get_by_email(form_data.username)

    # Verify credentials
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    # Generate JWT token
    access_token = create_access_token(data={"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user)
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: Annotated[User, Depends(get_current_user)]
):
    """
    Get authenticated user's profile.

    Requires valid JWT token in Authorization header.

    **Headers:**
    - Authorization: Bearer {token}

    **Success Response:**
    - Status: 200 OK
    - Returns: User profile

    **Error Responses:**
    - 401: Invalid or missing token
    """
    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse)
async def update_current_user_profile(
    payload: UpdateProfileRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    repo: Annotated[IUserRepository, Depends(get_user_repository)]
):
    """
    Update authenticated user's profile.

    Supports partial updates (only provided fields are updated).
    Requires valid JWT token in Authorization header.

    **Headers:**
    - Authorization: Bearer {token}

    **Request Body (all fields optional):**
    - name: Updated name
    - phone: Updated phone number
    - vehicle_model: Vehicle model (for drivers)
    - vehicle_plate: Vehicle plate (for drivers)
    - license_number: Driver's license (for drivers)

    **Success Response:**
    - Status: 200 OK
    - Returns: Updated user profile

    **Error Responses:**
    - 401: Invalid or missing token
    - 422: Validation error
    - 500: Failed to update profile
    """
    # Update only provided fields
    if payload.name is not None:
        current_user.name = payload.name
    if payload.phone is not None:
        current_user.phone = payload.phone
    if payload.vehicle_model is not None:
        current_user.vehicle_model = payload.vehicle_model
    if payload.vehicle_plate is not None:
        current_user.vehicle_plate = payload.vehicle_plate
    if payload.license_number is not None:
        current_user.license_number = payload.license_number

    # Persist changes
    success = await repo.update(current_user.id, current_user)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile"
        )

    return UserResponse.model_validate(current_user)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: int,
    repo: Annotated[IUserRepository, Depends(get_user_repository)],
    _: Annotated[User, Depends(get_current_user)]  # Requires authentication
):
    """
    Get public profile of another user by ID.

    Useful for viewing driver/passenger profiles in trip matching.
    Requires valid JWT token in Authorization header.

    **Path Parameters:**
    - user_id: User's ID

    **Headers:**
    - Authorization: Bearer {token}

    **Success Response:**
    - Status: 200 OK
    - Returns: User profile

    **Error Responses:**
    - 401: Invalid or missing token
    - 404: User not found
    """
    user = await repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return UserResponse.model_validate(user)
