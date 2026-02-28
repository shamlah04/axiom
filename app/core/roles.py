"""
app/core/roles.py
──────────────────
Role-based access control dependencies for Phase 3.

Roles (fleet-scoped, stored on User.role):
  owner      → full access including billing, team management, destructive ops
  dispatcher → create/edit jobs, trucks, drivers; no billing or team changes
  viewer     → read-only access to all fleet data

Usage:
    from app.core.roles import require_owner, require_dispatcher_or_above

    @router.post("/team/invites",
                 dependencies=[Depends(require_owner)])
    async def invite_member(...):
        ...

    @router.post("/jobs",
                 dependencies=[Depends(require_dispatcher_or_above)])
    async def create_job(...):
        ...
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, status

from app.core.deps import get_current_fleet_user
from app.models.models import User
from app.models.team import UserRole


# Role hierarchy (higher index = more permissions)
_ROLE_LEVEL: dict[UserRole, int] = {
    UserRole.viewer:      1,
    UserRole.dispatcher:  2,
    UserRole.owner:       3,
}


def _role_level(user: User) -> int:
    """Get user's role level. Defaults to viewer if role not set."""
    try:
        return _ROLE_LEVEL.get(UserRole(user.role), 1)
    except (ValueError, AttributeError):
        return 1


def require_role(minimum_role: UserRole):
    """
    Returns a FastAPI dependency that enforces a minimum role.

    Example:
        dependencies=[Depends(require_role(UserRole.owner))]
    """
    async def _check(
        current_user: User = Depends(get_current_fleet_user),
    ) -> User:
        user_level = _role_level(current_user)
        required_level = _ROLE_LEVEL.get(minimum_role, 1)

        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "insufficient_role",
                    "message": f"This action requires the '{minimum_role.value}' role or higher.",
                    "your_role": current_user.role if hasattr(current_user, "role") else "unknown",
                    "required_role": minimum_role.value,
                },
            )
        return current_user

    return _check


# Pre-built dependency instances
require_owner              = require_role(UserRole.owner)
require_dispatcher_or_above = require_role(UserRole.dispatcher)
require_viewer_or_above    = require_role(UserRole.viewer)   # effectively: just be in the fleet
