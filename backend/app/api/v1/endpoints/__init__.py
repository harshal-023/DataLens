from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.invitations import router as invitations_router
from app.api.v1.endpoints.users import router as users_router
from app.api.v1.endpoints.workspaces import router as workspaces_router

__all__ = [
    "auth_router",
    "health_router",
    "invitations_router",
    "users_router",
    "workspaces_router",
]
