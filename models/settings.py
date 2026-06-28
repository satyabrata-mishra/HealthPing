from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Global HealthPing settings."""

    concurrency: int = Field(default=10, gt=0)
    default_timeout: int = Field(default=20, gt=0)
    retry_delay: int = Field(default=2, ge=0)
    log_level: str = "INFO"

    generate_html_report: bool = True
    generate_csv_report: bool = True
    generate_json_report: bool = True