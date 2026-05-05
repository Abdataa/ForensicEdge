"""
Typed payload schemas for authentication-related audit events.
"""

from typing import Optional

from pydantic import BaseModel


class UserLoginDetails(BaseModel):
    user_agent: Optional[str] = None
    device: Optional[str] = None
    location: Optional[str] = None
    login_method: Optional[str] = "password"


class UserLogoutDetails(BaseModel):
    reason: Optional[str] = None


class PasswordChangedDetails(BaseModel):
    changed_by_admin: bool = False