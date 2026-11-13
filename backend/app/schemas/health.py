
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field("ok", description="Overall liveness status")
    service: str = Field("datalens-api", description="Service identifier")


class ReadinessResponse(BaseModel):
    status: str = Field(..., description="'ready' or 'unavailable'")
    service: str = Field("datalens-api", description="Service identifier")
    components: dict[str, str] = Field(..., description="Status breakdown of essential components")
    timestamp: str = Field(..., description="UTC ISO timestamp of the probe")
    error: str | None = Field(None, description="Sanitized high-level error message if unavailable")
