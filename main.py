import argparse
import asyncio
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from config.loader import ConfigLoader
from config.validator import ConfigValidator
from utils.logger import setup_logging
from monitor.checker import MonitoringEngine
from reports.generator import ReportGenerator, HistoryAggregator
from notifications.email_sender import EmailSender

logger = logging.getLogger("healthping")


async def run_monitoring_cycle(mode: str) -> int:
    """Executes a single monitoring cycle, writes reports, and dispatches notifications.

    Args:
        mode: Run mode ('check', 'daily', or 'weekly').

    Returns:
        int: Exit code (0 for success, 1 for critical system failure).
    """
    try:
        config_dir = Path("config")
        reports_dir = Path("report_outputs")
        templates_dir = Path("templates")

        # 1. Load Configurations
        settings = ConfigLoader.load_settings(config_dir)
        
        # Initialize logging first using Settings
        setup_logging(log_level=settings.log_level)
        
        logger.info(f"Loaded global settings. Log level set to {settings.log_level}")

        services = ConfigLoader.load_services(config_dir)
        email_config = ConfigLoader.load_email_config(config_dir)

        # 2. Validate configurations
        ConfigValidator.validate(services)
        logger.info(f"Loaded and validated {len(services)} services.")

        # 3. Perform asynchronous health checks
        start_time = time.monotonic()
        engine = MonitoringEngine(settings)
        results = await engine.run_checks(services)
        elapsed_time = time.monotonic() - start_time

        if not results:
            logger.warning("No health checks were executed.")
            return 0

        # 4. Generate report models & metrics
        generator = ReportGenerator(reports_dir, templates_dir)
        report = generator.generate_report_model(results, elapsed_time)

        # Filename timestamp (filesystem-safe format: YYYYMMDD_HHMMSS)
        fs_timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        # 5. Write requested reports
        if settings.generate_json_report:
            generator.write_json_report(report, f"report_{fs_timestamp}.json")
            # Maintain a copy of the latest run details
            generator.write_json_report(report, "report_latest.json")

        if settings.generate_csv_report:
            generator.write_csv_report(report, f"report_{fs_timestamp}.csv")

        if settings.generate_html_report:
            generator.write_html_report(report, f"report_{fs_timestamp}.html")
            generator.write_html_report(report, "report_latest.html")

        # 6. Notification dispatch based on run mode
        sender = EmailSender(email_config, templates_dir)

        if mode == "check":
            logger.info("Dispatching unified status update email...")
            sender.send_status_update(report)

        elif mode == "daily":
            # Compile historical trends for the past 24 hours (1 day)
            logger.info("Compiling daily history aggregates...")
            history = HistoryAggregator.aggregate_history(reports_dir, days=1)
            sender.send_summary_report(report, history=history, is_weekly=False)

        elif mode == "weekly":
            # Compile historical trends for the past 7 days
            logger.info("Compiling weekly history aggregates...")
            history = HistoryAggregator.aggregate_history(reports_dir, days=7)
            sender.send_summary_report(report, history=history, is_weekly=True)

        return 0

    except FileNotFoundError as e:
        # Logging instead of print()
        logger.critical(f"Configuration file missing error: {e}", exc_info=True)
        return 1
    except ValueError as e:
        logger.critical(f"Configuration or validation error: {e}", exc_info=True)
        return 1
    except Exception as e:
        logger.critical(f"Critical execution error in monitoring cycle: {e}", exc_info=True)
        return 1


def main() -> None:
    """Main entrypoint parsing CLI args and executing the cycle."""
    # Prevent encoding crashes (UnicodeEncodeError) on Windows consoles with limited encodings
    if sys.stdout is not None:
        try:
            sys.stdout.reconfigure(errors="backslashreplace")
        except AttributeError:
            pass
    if sys.stderr is not None:
        try:
            sys.stderr.reconfigure(errors="backslashreplace")
        except AttributeError:
            pass

    parser = argparse.ArgumentParser(
        description="HealthPing: Clean, concurrent, scheduler-free service monitor CLI."
    )
    parser.add_argument(
        "--mode",
        choices=["check", "daily", "weekly"],
        default="check",
        help="Run mode. 'check' executes and alerts, 'daily'/'weekly' send summaries.",
    )
    args = parser.parse_args()

    exit_code = asyncio.run(run_monitoring_cycle(args.mode))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()