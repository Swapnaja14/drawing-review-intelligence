"""
src/core/dtos/auth_dtos.py
Data Transfer Objects (DTOs) for Authentication & Session management.
"""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass(frozen=True)
class UserDTO:
    """Immutable user representation after authentication."""
    user_id: str
    username: str
    email: str
    role: str
    is_authenticated: bool = True
    last_login: Optional[datetime] = None


@dataclass(frozen=True)
class SessionTokenDTO:
    """Session token for active user logins."""
    token: str
    user: UserDTO
    created_at: datetime
