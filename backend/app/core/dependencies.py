"""
backend/app/core/dependencies.py
----------------------------------
FastAPI dependency injection functions for ForensicEdge.

What is dependency injection in FastAPI?
-----------------------------------------
Instead of writing repetitive auth/db setup code in every route, FastAPI
lets you declare shared logic as "dependencies" via Depends().  FastAPI
resolves them automatically before calling the route handler.

    @router.get("/cases")
    async def list_cases(
        db:           AsyncSession  = Depends(get_db),
        current_user: User          = Depends(get_current_active_user),
    ):
        ...  # db is open, user is authenticated — no boilerplate needed

Dependencies in this file
--------------------------
    get_db()                — yields one AsyncSession per request
                              (re-exported from database.py for convenience)

    get_current_user()      — reads Bearer token → validates JWT → returns User
                              Raises 401 if token is missing, expired, or invalid.

    get_current_active_user() — wraps get_current_user, also checks is_active.
                              Raises 403 if user account has been deactivated.

    require_role(*roles)    — role-based access control factory.
                              Returns a dependency that raises 403 if the
                              current user's role is not in the allowed set.

Usage examples
--------------
    # Any authenticated user:
    Depends(get_current_active_user)

    # Admin only:
    Depends(require_role(UserRole.ADMIN))

    # Admin or AI engineer:
    Depends(require_role(UserRole.ADMIN, UserRole.AI_ENGINEER))

    # Read DB + auth together:
    db:   AsyncSession = Depends(get_db)
    user: User         = Depends(get_current_active_user)
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database  import get_db
from app.core.security  import UserRole, decode_token
from app.models.user    import User


# ---------------------------------------------------------------------------
# HTTP Bearer scheme
# ---------------------------------------------------------------------------
# HTTPBearer reads the Authorization: Bearer <token> header automatically.
# auto_error=False means it returns None instead of raising 401 when the
# header is missing — we handle the missing-token case ourselves with a
# clearer error message.

_bearer_scheme = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# Type aliases — cleaner route signatures
# ---------------------------------------------------------------------------
# Instead of:  db: AsyncSession = Depends(get_db)
# You can write: db: DBSession
#
# Used like:
#   async def my_route(db: DBSession, user: CurrentUser): ...

DBSession   = Annotated[AsyncSession, Depends(get_db)]
BearerToken = Annotated[
    HTTPAuthorizationCredentials | None,
    Depends(_bearer_scheme),
]


# ---------------------------------------------------------------------------
# get_current_user
# ---------------------------------------------------------------------------

async def get_current_user(
    credentials: BearerToken,
    db:          DBSession,
) -> User:
    """
    FastAPI dependency — decode JWT and return the authenticated User.

    Flow:
        1. Extract Bearer token from Authorization header.
        2. Decode and validate JWT via decode_token().
        3. Look up the user in the database by email (token subject).
        4. Return the User ORM object.

    Raises:
        HTTP 401 — token missing, expired, invalid signature, wrong type.
        HTTP 401 — user email in token not found in database
                   (e.g. account deleted after token was issued).

    Usage:
        user: User = Depends(get_current_user)
    """
    credentials_exception = HTTPException(
        status_code = status.HTTP_401_UNAUTHORIZED,
        detail      = "Could not validate credentials.",
        headers     = {"WWW-Authenticate": "Bearer"},
    )

    # Step 1 — token present?
    if credentials is None:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail      = "Authorization header missing. "
                          "Provide: Authorization: Bearer <token>",
            headers     = {"WWW-Authenticate": "Bearer"},
        )

    # Step 2 — decode and validate JWT
    try:
        token_data = decode_token(credentials.credentials, expected_type="access")
    except ValueError as e:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail      = str(e),
            headers     = {"WWW-Authenticate": "Bearer"},
        )

    # Step 3 — look up user in database
    result = await db.execute(
        select(User).where(User.email == token_data.subject)
    )
    user = result.scalar_one_or_none()

    if user is None:
        # Token was valid but user no longer exists — treat as unauthorised
        raise credentials_exception

    return user


# ---------------------------------------------------------------------------
# get_current_active_user
# ---------------------------------------------------------------------------

async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    FastAPI dependency — get authenticated user AND verify account is active.

    Use this (not get_current_user) on all protected routes.
    get_current_user is kept separate so token validation can be tested
    independently of the is_active check.

    Raises:
        HTTP 403 — user account has been deactivated by an administrator.
                   (report scenario: admin deactivates investigator account)

    Usage:
        user: User = Depends(get_current_active_user)
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code = status.HTTP_403_FORBIDDEN,
            detail      = "Account deactivated. Contact your administrator.",
        )
    return current_user


# ---------------------------------------------------------------------------
# require_role  — role-based access control factory
# ---------------------------------------------------------------------------

def require_role(*allowed_roles: UserRole):
    """
    Dependency factory for role-based access control.

    Returns a FastAPI dependency that:
        1. Authenticates the user (via get_current_active_user).
        2. Checks the user's role is in allowed_roles.
        3. Raises HTTP 403 if not authorised.

    Args:
        *allowed_roles : one or more UserRole values that may access the route.

    Returns:
        A FastAPI dependency function.

    Examples:
        # Admin only route:
        @router.delete("/users/{user_id}")
        async def delete_user(
            user_id: int,
            _: User = Depends(require_role(UserRole.ADMIN)),
            db: AsyncSession = Depends(get_db),
        ):
            ...

        # Admin or AI engineer:
        @router.post("/datasets")
        async def create_dataset(
            _: User = Depends(require_role(UserRole.ADMIN, UserRole.AI_ENGINEER)),
            db: AsyncSession = Depends(get_db),
        ):
            ...

        # Any authenticated active user (analyst, admin, or ai_engineer):
        @router.get("/compare")
        async def compare(
            user: User = Depends(get_current_active_user),
            db: AsyncSession = Depends(get_db),
        ):
            ...
    """
    allowed = set(role.value if isinstance(role, UserRole) else role
                  for role in allowed_roles)

    async def _check_role(
        current_user: Annotated[User, Depends(get_current_active_user)],
    ) -> User:
        if current_user.role not in allowed:
            raise HTTPException(
                status_code = status.HTTP_403_FORBIDDEN,
                detail      = (
                    f"Access denied. "
                    f"Required role: {' or '.join(sorted(allowed))}. "
                    f"Your role: {current_user.role}."
                ),
            )
        return current_user

    return _check_role


# ---------------------------------------------------------------------------
# Convenience type aliases for common dependency combinations
# ---------------------------------------------------------------------------

# Any logged-in active user
CurrentUser = Annotated[User, Depends(get_current_active_user)]

# Admin only
AdminUser = Annotated[User, Depends(require_role(UserRole.ADMIN))]

# Admin or AI engineer
AIOrAdminUser = Annotated[
    User,
    Depends(require_role(UserRole.ADMIN, UserRole.AI_ENGINEER)),
]