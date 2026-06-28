from pydantic import BaseModel, Field
from typing import List, Optional
from models.health_result import HealthResult


class Report(BaseModel):
    """Aggregated health check report for a monitoring cycle."""

    total_services: int = Field(..., ge=0)
    healthy: int = Field(..., ge=0)
    failed: int = Field(..., ge=0)
    average_response_time: float = Field(..., ge=0.0)
    slowest_service: Optional[str] = None
    fastest_service: Optional[str] = None
    execution_time: float = Field(..., ge=0.0)
    timestamp: str  # ISO 8601 formatted UTC timestamp
    results: List[HealthResult] = Field(default_factory=list)
