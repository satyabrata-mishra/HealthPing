from pydantic import BaseModel, Field
from typing import Optional


class HealthResult(BaseModel):
    """Result of a single service health check execution."""

    service_name: str = Field(..., min_length=1)
    url: str
    status: str  # "HEALTHY" | "FAILED"
    http_status_code: Optional[int] = None
    latency: float  # latency in seconds
    timestamp: str  # ISO 8601 formatted UTC timestamp
    failure_reason: Optional[str] = None
    retry_count: int = Field(default=0, ge=0)
