"""
tests/unit/test_auth_service.py
Unit test suite for AuthService and User Authentication.
"""

import pytest
from pathlib import Path

from src.infrastructure.storage.repository import DatabaseEngine
from src.services.auth_service import AuthService
from src.core.exceptions.auth_exceptions import InvalidCredentialsError


@pytest.fixture
def auth_service(tmp_path: Path) -> AuthService:
    db_file = tmp_path / "test_auth.db"
    db_engine = DatabaseEngine(db_path=db_file)
    return AuthService(db_engine=db_engine)


def test_demo_user_sign_in_success(auth_service: AuthService):
    """Verifies successful sign-in with demo credentials."""
    session = auth_service.authenticate_user("admin", "Password123!")

    assert session is not None
    assert session.user.username == "admin"
    assert session.user.role == "Lead Engineer"
    assert session.user.is_authenticated is True


def test_sign_in_soham(auth_service: AuthService):
    """Verifies sign-in for user soham."""
    session = auth_service.authenticate_user("soham", "Password123!")
    assert session.user.username == "soham"
    assert session.user.role == "Backend Lead"


def test_sign_in_invalid_password(auth_service: AuthService):
    """Verifies InvalidCredentialsError on wrong password."""
    with pytest.raises(InvalidCredentialsError):
        auth_service.authenticate_user("admin", "WrongPassword!")


def test_sign_in_invalid_username(auth_service: AuthService):
    """Verifies InvalidCredentialsError on non-existent username."""
    with pytest.raises(InvalidCredentialsError):
        auth_service.authenticate_user("unknown_user", "Password123!")


def test_sign_out(auth_service: AuthService):
    """Verifies session sign-out invalidates session token."""
    session = auth_service.authenticate_user("admin", "Password123!")
    token = session.token

    assert auth_service.validate_session(token) is not None
    assert auth_service.sign_out(token) is True
    assert auth_service.validate_session(token) is None
