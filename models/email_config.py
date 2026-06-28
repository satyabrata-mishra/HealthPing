from pydantic import BaseModel, Field
from typing import Optional


class EmailConfiguration(BaseModel):
    """Configuration for SMTP email notifications."""

    smtp_server: str = Field(..., min_length=1)
    smtp_port: int = Field(default=587, gt=0)
    sender_email: str = Field(..., min_length=1)
    receiver_email: str = Field(..., min_length=1)
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None

    @property
    def is_valid_for_sending(self) -> bool:
        """Helper properties to verify if basic settings are present."""
        return bool(
            self.smtp_server
            and self.smtp_port
            and self.sender_email
            and self.receiver_email
        )
