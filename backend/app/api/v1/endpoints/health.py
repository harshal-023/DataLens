from datetime import UTC, datetime

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.db.session import check_database_connection
from app.schemas.health import HealthResponse, ReadinessResponse

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Liveness Probe",
    description="Returns immediate ok status if the FastAPI process is running.",
)
async def get_health():
    return HealthResponse(status="ok", service="datalens-api")


@router.get(
    "/health/ready",
    response_model=ReadinessResponse,
    summary="Readiness Probe",
    description="Validates live connectivity to PostgreSQL database before accepting traffic.",
    responses={
        200: {"description": "All system components are healthy and ready."},
        503: {"description": "One or more critical components (PostgreSQL) are unreachable."},
    },
)
async def get_readiness():
    db_ok, error_msg = await check_database_connection()
    now_iso = datetime.now(UTC).isoformat()

    if not db_ok:
        content = ReadinessResponse(
            status="unavailable",
            service="datalens-api",
            components={"database": "disconnected"},
            timestamp=now_iso,
            error=error_msg,
        ).model_dump()
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=content)

    return ReadinessResponse(
        status="ready",
        service="datalens-api",
        components={"database": "connected"},
        timestamp=now_iso,
        error=None,
    )
