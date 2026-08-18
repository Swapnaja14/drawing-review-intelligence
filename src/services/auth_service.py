"""
src/services/auth_service.py
Authentication Service managing PBKDF2 salted password hashing, user login,
sign-out session management, and demo accounts.
"""

import hashlib
import os
import secrets
from datetime import datetime, timezone
from typing import Optional, Dict
import uuid

from sqlalchemy import func
from src.infrastructure.storage.repository import DatabaseEngine
from src.infrastructure.storage.models import UserModel
from src.core.dtos.auth_dtos import UserDTO, SessionTokenDTO
from src.core.exceptions.auth_exceptions import InvalidCredentialsError, UserNotFoundError
from src.infrastructure.logging.logger import get_logger

logger = get_logger("AuthService")


class AuthService:
    """
    Authentication Service managing sign in, sign out, password verification,
    and user session state.
    """

    def __init__(self, db_engine: DatabaseEngine) -> None:
        self.db_engine = db_engine
        self._active_sessions: Dict[str, SessionTokenDTO] = {}
        self._seed_demo_users()

    def _hash_password(self, password: str, salt: Optional[bytes] = None) -> tuple[str, str]:
        """Hashes password using PBKDF2 with SHA-256 and salt."""
        if salt is None:
            salt = os.urandom(16)
        pwd_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
        return pwd_hash.hex(), salt.hex()

    def _verify_password(self, password: str, stored_hash: str, stored_salt_hex: str) -> bool:
        """Verifies input password against stored salt and hash."""
        salt = bytes.fromhex(stored_salt_hex)
        input_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000).hex()
        return secrets.compare_digest(input_hash, stored_hash)

    def _seed_demo_users(self) -> None:
        """Seeds default demo accounts into SQLite database if empty."""
        session = self.db_engine.get_session()
        try:
            if session.query(UserModel).count() == 0:
                demo_accounts = [
                    ("admin", "admin@ucc.com", "Password123!", "Lead Engineer"),
                    ("soham", "soham@ucc.com", "Password123!", "Backend Lead"),
                    ("reviewer", "reviewer@ucc.com", "Password123!", "Reviewer"),
                ]

                for uname, email, plain_pwd, role in demo_accounts:
                    pwd_hash, salt_hex = self._hash_password(plain_pwd)
                    user_record = UserModel(
                        id=f"USR-{uuid.uuid4().hex[:8].upper()}",
                        username=uname,
                        email=email,
                        password_hash=pwd_hash,
                        salt=salt_hex,
                        role=role,
                        created_at=datetime.now(timezone.utc)
                    )
                    session.add(user_record)

                session.commit()
                logger.info("Seeded demo user accounts into database (admin, soham, reviewer).")
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to seed demo users: {e}")
        finally:
            session.close()

    def authenticate_user(self, username_or_email: str, password: str) -> SessionTokenDTO:
        """
        Authenticates user with username/email and password.

        Returns:
            SessionTokenDTO: Active session container.

        Raises:
            InvalidCredentialsError: If username or password does not match.
        """
        session = self.db_engine.get_session()
        try:
            uname_clean = username_or_email.strip().lower()
            user_record = session.query(UserModel).filter(
                (func.lower(UserModel.username) == uname_clean) |
                (func.lower(UserModel.email) == uname_clean)
            ).first()

            if not user_record:
                logger.warning(f"Failed login attempt for unknown user: {username_or_email}")
                raise InvalidCredentialsError("Invalid username or password.")

            if not self._verify_password(password, user_record.password_hash, user_record.salt):
                logger.warning(f"Invalid password for user: {username_or_email}")
                raise InvalidCredentialsError("Invalid username or password.")

            # Update last login
            user_record.last_login = datetime.now(timezone.utc)
            session.commit()

            user_dto = UserDTO(
                user_id=user_record.id,
                username=user_record.username,
                email=user_record.email,
                role=user_record.role,
                is_authenticated=True,
                last_login=user_record.last_login
            )

            # Generate session token
            token_str = f"TOK-{secrets.token_hex(16)}"
            session_dto = SessionTokenDTO(
                token=token_str,
                user=user_dto,
                created_at=datetime.now(timezone.utc)
            )
            self._active_sessions[token_str] = session_dto

            logger.info(f"User '{user_record.username}' ({user_record.role}) signed in successfully.")
            return session_dto
        finally:
            session.close()

    def sign_out(self, token: str) -> bool:
        """Invalidates an active user session token."""
        if token in self._active_sessions:
            user = self._active_sessions[token].user
            del self._active_sessions[token]
            logger.info(f"User '{user.username}' signed out successfully.")
            return True
        return False

    def validate_session(self, token: str) -> Optional[UserDTO]:
        """Validates token and returns active UserDTO if valid."""
        if token in self._active_sessions:
            return self._active_sessions[token].user
        return None
