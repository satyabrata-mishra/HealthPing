import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from rich.logging import RichHandler


def setup_logging(log_level: str = "INFO", logs_dir: Path = Path("logs")) -> None:
    """Sets up application-wide logging with console and rotating file handlers.

    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        logs_dir: Directory where log files are stored.
    """
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Get root logger
    root_logger = logging.getLogger()
    
    # Remove existing handlers to avoid duplicates
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    root_logger.setLevel(numeric_level)

    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Rich Console Handler
    console_handler = RichHandler(
        level=numeric_level,
        show_time=False,
        rich_tracebacks=True
    )
    root_logger.addHandler(console_handler)

    # Rotating File Handler - General Health Log
    health_log_path = logs_dir / "health.log"
    health_handler = RotatingFileHandler(
        health_log_path,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=5,
        encoding="utf-8"
    )
    health_handler.setLevel(numeric_level)
    health_handler.setFormatter(formatter)
    root_logger.addHandler(health_handler)

    # Rotating File Handler - Error and Warning Log
    error_log_path = logs_dir / "error.log"
    error_handler = RotatingFileHandler(
        error_log_path,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=5,
        encoding="utf-8"
    )
    error_handler.setLevel(logging.WARNING)
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)

    # Mute httpx/httpcore details to prevent verbose output in default mode
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
