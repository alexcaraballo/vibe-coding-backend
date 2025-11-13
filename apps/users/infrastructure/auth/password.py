"""Password hashing utilities using argon2.

This module provides secure password hashing and verification
using passlib with argon2 backend (more modern and secure than bcrypt).
"""
from passlib.context import CryptContext

# Configure argon2 password hashing context
# Argon2 is the winner of the Password Hashing Competition (2015)
pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto"
)


def hash_password(plain_password: str) -> str:
    """
    Hash a plain password using bcrypt.

    Args:
        plain_password: Password in plain text

    Returns:
        Hashed password string (safe to store in database)

    Example:
        >>> hashed = hash_password("my_secure_password")
        >>> # Store hashed in database
    """
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.

    Args:
        plain_password: Password to verify
        hashed_password: Stored password hash

    Returns:
        True if password matches, False otherwise

    Example:
        >>> hashed = hash_password("secret")
        >>> verify_password("secret", hashed)
        True
        >>> verify_password("wrong", hashed)
        False
    """
    return pwd_context.verify(plain_password, hashed_password)
