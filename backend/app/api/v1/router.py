from fastapi import APIRouter

from app.api.v1.endpoints.ai import router as ai_router
from app.api.v1.endpoints.analytics import router as analytics_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.automation import router as automation_router
from app.api.v1.endpoints.business_analyst import router as business_analyst_router
from app.api.v1.endpoints.comments import router as comments_router
from app.api.v1.endpoints.connections import router as connections_router
from app.api.v1.endpoints.dashboards import router as dashboards_router
from app.api.v1.endpoints.datasets import router as datasets_router
from app.api.v1.endpoints.experiments import router as experiments_router
from app.api.v1.endpoints.governance import router as governance_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.intelligence import router as intelligence_router
from app.api.v1.endpoints.invitations import router as invitations_router
from app.api.v1.endpoints.metrics import router as metrics_router
from app.api.v1.endpoints.ml import router as ml_router
from app.api.v1.endpoints.nla import router as nla_router
from app.api.v1.endpoints.notifications import router as notifications_router
from app.api.v1.endpoints.prompts import router as prompts_router
from app.api.v1.endpoints.reports import router as reports_router
from app.api.v1.endpoints.shares import router as shares_router
from app.api.v1.endpoints.transformations import router as transformations_router
from app.api.v1.endpoints.users import router as users_router
from app.api.v1.endpoints.workspaces import router as workspaces_router

api_v1_router = APIRouter()

# Mount health & readiness probes
api_v1_router.include_router(health_router)

# Mount authentication endpoints
api_v1_router.include_router(auth_router)

# Mount user endpoints
api_v1_router.include_router(users_router)

# Mount workspace management endpoints
api_v1_router.include_router(workspaces_router)

# Mount invitation endpoints
api_v1_router.include_router(invitations_router)

# Mount dataset endpoints
api_v1_router.include_router(datasets_router)

# Mount dataset analytics and analysis-run endpoints
api_v1_router.include_router(analytics_router)

# Mount report endpoints
api_v1_router.include_router(reports_router)

# Mount External Data Source Connections endpoints
api_v1_router.include_router(connections_router)

# Mount Dashboard Builder endpoints
api_v1_router.include_router(dashboards_router)

# Mount Data Transformation endpoints
api_v1_router.include_router(transformations_router)

# Mount AI analytics endpoints
api_v1_router.include_router(ai_router)

# Mount Prompt Lab endpoints
api_v1_router.include_router(prompts_router)
api_v1_router.include_router(experiments_router)

# Mount Advanced Analytics & ML endpoints
api_v1_router.include_router(ml_router)

# Mount Collaboration, Sharing, Comments & Notifications (Phase 5B)
api_v1_router.include_router(shares_router)
api_v1_router.include_router(comments_router)
api_v1_router.include_router(notifications_router)

# Mount Enterprise Governance, RBAC & Security Audit (Phase 5C)
api_v1_router.include_router(governance_router)

# Mount Automated Refresh, Pipeline Orchestration & Background Jobs (Phase 5D)
api_v1_router.include_router(automation_router)

# Mount Dataset Intelligence, Semantics & Metrics (Phase 6B)
api_v1_router.include_router(intelligence_router)
api_v1_router.include_router(metrics_router)

# Mount Conversational Natural Language Analytics (Phase 6C)
api_v1_router.include_router(nla_router)

# Mount AI Business Analyst & Autonomous Insights (Phase 6D)
api_v1_router.include_router(business_analyst_router)





