"""
backend/app/core/security.py
------------------------------
Password hashing and JWT token utilities for ForensicEdge.

Responsibilities
----------------
1. Password hashing   — bcrypt via passlib (hash on register, verify on login)
2. Access tokens      — short-lived JWT (60 min default) for API requests
3. Refresh tokens     — long-lived JWT (7 days default) to obtain new access tokens
4. Token decoding     — verify signature, expiry, and token type

Token payload structure
-----------------------
    {
        "sub":  "user@example.com",   # subject — user's email
        "role": "analyst",            # analyst | admin | ai_engineer
        "type": "access",             # access | refresh
        "exp":  1720000000,           # Unix timestamp — expiry
        "iat":  1719996400,           # Unix timestamp — issued at
    }

User roles (from report use case diagram)
------------------------------------------
    analyst      — forensic investigator: upload images, run comparisons,
                   view and download reports, access analysis history
    admin        — system administrator: manage user accounts, view audit logs,
                   configure system settings
    ai_engineer  — AI team: manage datasets, trigger model retraining,
                   view model version history

Dependencies
------------
    pip install python-jose[cryptography] passlib[bcrypt]
"""

from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings


# ---------------------------------------------------------------------------
# User roles
# ---------------------------------------------------------------------------

class UserRole(str, Enum):
    """
    Roles defined in the ForensicEdge report use case diagram.
    Using str Enum means role values serialise naturally to/from JSON
    and database strings.
    """
    ANALYST     = "analyst"       # forensic investigator
    ADMIN       = "admin"         # system administrator
    AI_ENGINEER = "ai_engineer"   # AI / dataset management


# Role hierarchy — higher index = more permissions
# Used by require_role() to support "minimum role" checks
ROLE_HIERARCHY = [
    UserRole.ANALYST,
    UserRole.AI_ENGINEER,
    UserRole.ADMIN,
]


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

# bcrypt is the industry standard for password hashing.
# auto_deprecated="auto" automatically re-hashes passwords using outdated
# bcrypt configs the next time the user logs in — future-proof.
_pwd_context = CryptContext(
    schemes     = ["bcrypt"],
    deprecated  = "auto",
)


def hash_password(plain_password: str) -> str:
    """
    Hash a plain-text password using bcrypt.

    Args:
        plain_password : the password entered by the user at registration.

    Returns:
        A bcrypt hash string safe to store in the database.
        The hash includes the salt — no separate salt column needed.

    Example:
        hashed = hash_password("MySecret123!")
        # store hashed in users.password_hash column
    """
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain-text password against a stored bcrypt hash.

    Args:
        plain_password   : the password entered by the user at login.
        hashed_password  : the hash stored in the database.

    Returns:
        True if the password matches, False otherwise.

    Example:
        if not verify_password(form.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")
    """
    return _pwd_context.verify(plain_password, hashed_password)


# ---------------------------------------------------------------------------
# JWT token creation
# ---------------------------------------------------------------------------

def _create_token(
    subject:    str,
    role:       UserRole,
    token_type: str,
    expires_in: timedelta,
) -> str:
    """
    Internal helper — create a signed JWT with the ForensicEdge payload.

    Args:
        subject    : the user's email address (JWT 'sub' claim).
        role       : the user's role (analyst / admin / ai_engineer).
        token_type : "access" or "refresh".
        expires_in : how long until the token expires.

    Returns:
        Signed JWT string.
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub":  subject,
        "role": role.value if isinstance(role, UserRole) else role,
        "type": token_type,
        "iat":  now,
        "exp":  now + expires_in,
    }
    return jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def create_access_token(
    subject: str,
    role:    UserRole,
    expires_in: Optional[timedelta] = None,
) -> str:
    """
    Create a short-lived access token for API authentication.

    Access tokens are sent in the Authorization header:
        Authorization: Bearer <access_token>

    Args:
        subject    : user email — identifies who this token belongs to.
        role       : user's role — used by require_role() in dependencies.py.
        expires_in : override default expiry (ACCESS_TOKEN_EXPIRE_MINUTES).

    Returns:
        Signed JWT access token string.

    Example:
        token = create_access_token(subject=user.email, role=user.role)
        return {"access_token": token, "token_type": "bearer"}
    """
    if expires_in is None:
        expires_in = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return _create_token(subject, role, "access", expires_in)


def create_refresh_token(
    subject: str,
    role:    UserRole,
    expires_in: Optional[timedelta] = None,
) -> str:
    """
    Create a long-lived refresh token.

    Refresh tokens are stored client-side (httpOnly cookie recommended)
    and exchanged for a new access token at POST /api/v1/auth/refresh.
    They are NOT sent on every request — only to the refresh endpoint.

    Args:
        subject    : user email.
        role       : user's role.
        expires_in : override default expiry (REFRESH_TOKEN_EXPIRE_DAYS).

    Returns:
        Signed JWT refresh token string.
    """
    if expires_in is None:
        expires_in = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return _create_token(subject, role, "refresh", expires_in)


# ---------------------------------------------------------------------------
# JWT token decoding
# ---------------------------------------------------------------------------

class TokenData:
    """
    Parsed and validated contents of a JWT token.
    Returned by decode_token() and used by dependencies.py.
    """
    def __init__(self, subject: str, role: str, token_type: str):
        self.subject    = subject
        self.role       = role
        self.token_type = token_type

    def __repr__(self) -> str:
        return (
            f"TokenData(subject={self.subject!r}, "
            f"role={self.role!r}, type={self.token_type!r})"
        )


def decode_token(token: str, expected_type: str = "access") -> TokenData:
    """
    Decode and validate a JWT token.

    Verifies:
        - Signature (using SECRET_KEY)
        - Expiry (exp claim)
        - Token type (access vs refresh — prevents using a refresh token
          as an access token, which would be a security vulnerability)
        - Required claims are present (sub, role, type)

    Args:
        token         : the raw JWT string from the Authorization header.
        expected_type : "access" (default) or "refresh".

    Returns:
        TokenData with subject (email), role, and token_type.

    Raises:
        ValueError : with a descriptive message for any validation failure.
                     dependencies.py catches this and raises HTTPException 401.

    Example:
        try:
            token_data = decode_token(token)
        except ValueError as e:
            raise HTTPException(status_code=401, detail=str(e))
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError as e:
        # JWTError covers: expired signature, invalid signature,
        # malformed token, wrong algorithm
        raise ValueError(f"Invalid or expired token: {e}")

    # Validate required claims
    subject = payload.get("sub")
    role    = payload.get("role")
    t_type  = payload.get("type")

    if not subject:
        raise ValueError("Token missing 'sub' claim.")
    if not role:
        raise ValueError("Token missing 'role' claim.")
    if not t_type:
        raise ValueError("Token missing 'type' claim.")

    # Prevent refresh tokens being used as access tokens
    if t_type != expected_type:
        raise ValueError(
            f"Wrong token type: expected '{expected_type}', got '{t_type}'."
        )

    return TokenData(subject=subject, role=role, token_type=t_type)