import os
import json
import logging
from pathlib import Path
from typing import List
from dotenv import load_dotenv
from pydantic import ValidationError

from models.service import Service
from models.settings import Settings
from models.email_config import EmailConfiguration

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Loads and validates configuration files for HealthPing."""

    @staticmethod
    def load_services(config_dir: Path = Path("config")) -> List[Service]:
        """Loads and validates the services configuration file.

        Args:
            config_dir: Directory containing services.json.

        Returns:
            List[Service]: List of parsed and validated Service models.

        Raises:
            FileNotFoundError: If services.json does not exist.
            ValueError: If services.json contains invalid JSON or validation fails.
        """
        file_path = config_dir / "services.json"
        if not file_path.exists():
            raise FileNotFoundError(f"Services config file not found at {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in services config file: {e}")

        if "services" not in data or not isinstance(data["services"], list):
            raise ValueError("Services config must contain a list of 'services'")

        services = []
        for i, s in enumerate(data["services"]):
            try:
                services.append(Service(**s))
            except ValidationError as e:
                raise ValueError(f"Validation error in service index {i}: {e}")

        return services

    @staticmethod
    def load_settings(config_dir: Path = Path("config")) -> Settings:
        """Loads and validates the global settings file.

        Args:
            config_dir: Directory containing settings.json.

        Returns:
            Settings: Parsed and validated Settings model.

        Raises:
            ValueError: If settings.json contains invalid JSON or validation fails.
        """
        file_path = config_dir / "settings.json"
        if not file_path.exists():
            logger.warning(f"Settings file not found at {file_path}, using defaults.")
            return Settings()

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return Settings(**data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in settings: {e}")
        except ValidationError as e:
            raise ValueError(f"Validation error in settings: {e}")

    @staticmethod
    def load_email_config(config_dir: Path = Path("config")) -> EmailConfiguration:
        """Loads email settings from email.json and overrides with env variables.

        Args:
            config_dir: Directory containing email.json.

        Returns:
            EmailConfiguration: Validated EmailConfiguration model.

        Raises:
            ValueError: If SMTP configuration is invalid or missing required credentials.
        """
        # Ensure env vars are loaded from .env if present
        load_dotenv()

        file_path = config_dir / "email.json"
        email_data = {}

        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    email_data = json.load(f)
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON in email.json: {e}. Falling back to env vars.")
        else:
            logger.warning("email.json not found. Using environment variables.")

        # SMTP settings mapping (env variables take priority)
        smtp_server = os.getenv("SMTP_SERVER", email_data.get("smtp_server", "smtp.gmail.com"))
        
        smtp_port_raw = os.getenv("SMTP_PORT", str(email_data.get("smtp_port", 587)))
        try:
            smtp_port = int(smtp_port_raw)
        except ValueError:
            smtp_port = 587

        # Sender can be EMAIL_SENDER, fallback to SMTP_USERNAME or config sender_email
        sender_email = os.getenv(
            "EMAIL_SENDER", 
            os.getenv("SMTP_USERNAME", email_data.get("sender_email", ""))
        )
        
        # Receiver can be EMAIL_RECEIVER, fallback to config receiver_email
        receiver_email = os.getenv("EMAIL_RECEIVER", email_data.get("receiver_email", ""))

        # SMTP Credentials must come from environment variables
        smtp_username = os.getenv("SMTP_USERNAME")
        smtp_password = os.getenv("SMTP_PASSWORD")

        try:
            return EmailConfiguration(
                smtp_server=smtp_server,
                smtp_port=smtp_port,
                sender_email=sender_email,
                receiver_email=receiver_email,
                smtp_username=smtp_username,
                smtp_password=smtp_password
            )
        except ValidationError as e:
            raise ValueError(f"Validation error in email configuration: {e}")