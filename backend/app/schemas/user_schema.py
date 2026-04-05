"""
backend/app/schemas/user_schema.py
------------------------------------
Pydantic schemas for user management and authentication.

Schema hierarchy
----------------
    UserBase          shared fields (full_name, email, role)
    UserCreate        POST /auth/register  — adds password
    UserUpdate        PATCH /users/{id}    — all fields optional (admin only)
    UserResponse      returned to client   — NEVER includes password_hash
    UserInDB          internal use only    — includes password_hash

    LoginRequest      POST /auth/login     — email + password
    TokenResponse     login response       — access_token + refresh_token + user
    RefreshRequest    POST /auth/refresh   — refresh_token only

Security rule
-------------
    password_hash is NEVER included in any Response schema.
    Pydantic's model_config with from_attributes=True reads ORM objects
    but only exposes fields explicitly declared in the schema.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.security import UserRole


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class UserBase(BaseModel):
    full_name: str = Field(
        ...,
        min_length = 2,
        max_length = 120,
        examples   = ["Abebe Girma"],
    )
    email: EmailStr = Field(
        ...,
        examples=["abebe.girma@forensicedge.et"],
    )
    role: UserRole = Field(
        default = UserRole.ANALYST,
        examples = [UserRole.ANALYST],
    )


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class UserCreate(UserBase):
    """
    Body for POST /api/v1/auth/register or POST /api/v1/admin/users.
    Password is validated here and hashed in auth_service.py before storage.
    """
    password: str = Field(
        ...,
        min_length = 8,
        max_length = 128,
        examples   = ["StrongPass123!"],
    )

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        """
        Enforce minimum password complexity.
        At least one uppercase, one lowercase, one digit.
        """
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter.")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit.")
        return v


class UserUpdate(BaseModel):
    """
    Body for PATCH /api/v1/admin/users/{user_id}.
    All fields optional — only provided fields are updated.
    Admin only (enforced in route via require_role).
    """
    full_name:  Optional[str]      = Field(None, min_length=2, max_length=120)
    email:      Optional[EmailStr] = None
    role:       Optional[UserRole] = None
    is_active:  Optional[bool]     = None
    password:   Optional[str]      = Field(None, min_length=8, max_length=128)


class LoginRequest(BaseModel):
    """Body for POST /api/v1/auth/login."""
    email:    EmailStr = Field(..., examples=["abebe.girma@forensicedge.et"])
    password: str      = Field(..., examples=["StrongPass123!"])


class RefreshRequest(BaseModel):
    """Body for POST /api/v1/auth/refresh."""
    refresh_token: str = Field(..., description="JWT refresh token")


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class UserResponse(BaseModel):
    """
    User object returned to the client.
    password_hash is deliberately excluded — never expose it.
    """
    id:         int
    full_name:  str
    email:      str
    role:       UserRole
    is_active:  bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """
    Response for POST /auth/login and POST /auth/refresh.
    Contains both tokens and the authenticated user's profile.
    """
    access_token:  str
    refresh_token: str
    token_type:    str        = "bearer"
    user:          UserResponse


class AccessTokenResponse(BaseModel):
    """
    Minimal response for POST /auth/refresh — only new access token returned.
    The refresh token is unchanged so no need to re-send it.
    """
    access_token: str
    token_type:   str = "bearer"


class UserListResponse(BaseModel):
    """Paginated list of users for GET /admin/users."""
    total:  int
    page:   int
    limit:  int
    users:  list[UserResponse]