from pydantic import BaseModel, HttpUrl, Field


class Service(BaseModel):
    """Represents a monitored service."""

    name: str = Field(..., min_length=1)
    url: HttpUrl
    method: str = "GET"
    timeout: int = Field(default=20, gt=0)
    retries: int = Field(default=3, ge=0)
    expected_status: int = Field(default=200, ge=100, le=599)
    enabled: bool = True
    notify_on_failure: bool = True
    payload: dict | None = None
    headers: dict[str, str] | None = None