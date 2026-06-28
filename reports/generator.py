import csv
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional
from jinja2 import Environment, FileSystemLoader

from models.health_result import HealthResult
from models.report import Report

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generates health check reports in JSON, CSV, and HTML formats."""

    def __init__(
        self,
        reports_dir: Path = Path("reports"),
        templates_dir: Path = Path("templates"),
    ):
        """Initializes the report generator.

        Args:
            reports_dir: Path to the directory where reports should be saved.
            templates_dir: Path to the directory where Jinja2 templates reside.
        """
        self.reports_dir = reports_dir
        self.templates_dir = templates_dir

    def generate_report_model(
        self, results: List[HealthResult], execution_time: float
    ) -> Report:
        """Calculates aggregate metrics and returns a Report Pydantic model.

        Args:
            results: List of HealthResult objects from a monitoring cycle.
            execution_time: Total duration of the checks in seconds.

        Returns:
            Report: The populated Report model.
        """
        total = len(results)
        healthy = sum(1 for r in results if r.status == "HEALTHY")
        failed = total - healthy

        avg_latency = (
            sum(r.latency for r in results) / total if total > 0 else 0.0
        )

        slowest = None
        fastest = None
        if results:
            slowest_r = max(results, key=lambda r: r.latency)
            slowest = f"{slowest_r.service_name} ({slowest_r.latency:.4f}s)"
            fastest_r = min(results, key=lambda r: r.latency)
            fastest = f"{fastest_r.service_name} ({fastest_r.latency:.4f}s)"

        return Report(
            total_services=total,
            healthy=healthy,
            failed=failed,
            average_response_time=round(avg_latency, 4),
            slowest_service=slowest,
            fastest_service=fastest,
            execution_time=round(execution_time, 4),
            timestamp=datetime.now(timezone.utc).isoformat(),
            results=results,
        )

    def write_json_report(self, report: Report, filename: str) -> Path:
        """Writes the report as a JSON file.

        Args:
            report: The Report model to save.
            filename: Name of the output JSON file.

        Returns:
            Path: Absolute path to the saved file.
        """
        file_path = self.reports_dir / filename
        try:
            self.reports_dir.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(report.model_dump_json(indent=4))
            logger.info(f"JSON report written to {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Failed to write JSON report to {file_path}: {e}")
            raise

    def write_csv_report(self, report: Report, filename: str) -> Path:
        """Writes check results as a CSV file.

        Args:
            report: The Report model containing results to save.
            filename: Name of the output CSV file.

        Returns:
            Path: Absolute path to the saved file.
        """
        file_path = self.reports_dir / filename
        try:
            self.reports_dir.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "Service Name",
                        "URL",
                        "Status",
                        "HTTP Status Code",
                        "Latency (s)",
                        "Timestamp",
                        "Failure Reason",
                        "Retry Count",
                    ]
                )
                for r in report.results:
                    writer.writerow(
                        [
                            r.service_name,
                            r.url,
                            r.status,
                            r.http_status_code if r.http_status_code is not None else "N/A",
                            f"{r.latency:.4f}",
                            r.timestamp,
                            r.failure_reason or "",
                            r.retry_count,
                        ]
                    )
            logger.info(f"CSV report written to {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Failed to write CSV report to {file_path}: {e}")
            raise

    def write_html_report(self, report: Report, filename: str) -> Path:
        """Renders and writes an HTML report dashboard.

        Args:
            report: The Report model to render.
            filename: Name of the output HTML file.

        Returns:
            Path: Absolute path to the saved file.
        """
        file_path = self.reports_dir / filename
        try:
            self.reports_dir.mkdir(parents=True, exist_ok=True)
            env = Environment(loader=FileSystemLoader(self.templates_dir))
            template = env.get_template("report_template.html")

            # Parse and format the timestamp for readability
            dt = datetime.fromisoformat(report.timestamp.replace("Z", "+00:00"))
            formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S UTC")

            html_content = template.render(
                report=report,
                formatted_time=formatted_time,
            )

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            logger.info(f"HTML report written to {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Failed to write HTML report to {file_path}: {e}")
            raise


class HistoryAggregator:
    """Aggregates local historical JSON reports to produce trend statistics."""

    @staticmethod
    def aggregate_history(reports_dir: Path, days: int) -> dict:
        """Searches reports directory and aggregates checks for the last N days.

        Args:
            reports_dir: Directory where JSON reports are stored.
            days: Lookback window in days.

        Returns:
            dict: Aggregated history metrics including uptime success rate.
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)
        total_runs = 0
        total_checks = 0
        successful_checks = 0
        latencies: List[float] = []
        failures_by_service = {}

        if reports_dir.exists():
            for file_path in reports_dir.glob("report_*.json"):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    ts_str = data.get("timestamp")
                    if not ts_str:
                        continue

                    # Parse timestamp, standardizing Z/UTC offsets
                    ts_str = ts_str.replace("Z", "+00:00")
                    file_ts = datetime.fromisoformat(ts_str)

                    if file_ts.tzinfo is None:
                        file_ts = file_ts.replace(tzinfo=timezone.utc)
                    else:
                        file_ts = file_ts.astimezone(timezone.utc)

                    if file_ts >= cutoff_time:
                        total_runs += 1
                        for res in data.get("results", []):
                            total_checks += 1
                            is_healthy = res.get("status") == "HEALTHY"
                            if is_healthy:
                                successful_checks += 1
                            else:
                                svc_name = res.get("service_name", "Unknown")
                                failures_by_service[svc_name] = (
                                    failures_by_service.get(svc_name, 0) + 1
                                )

                            latency = res.get("latency")
                            if latency is not None:
                                latencies.append(float(latency))

                except Exception as e:
                    logger.warning(
                        f"Error reading historical report {file_path} for aggregation: {e}"
                    )

        success_rate = (
            (successful_checks / total_checks * 100) if total_checks > 0 else 100.0
        )
        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

        return {
            "total_runs": total_runs,
            "total_checks": total_checks,
            "success_rate": round(success_rate, 2),
            "average_latency": round(avg_latency, 4),
            "failures_by_service": failures_by_service,
            "period_days": days,
        }
