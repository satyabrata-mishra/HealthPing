import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional
from jinja2 import Environment, FileSystemLoader

from models.email_config import EmailConfiguration
from models.report import Report
from models.health_result import HealthResult

logger = logging.getLogger(__name__)


class EmailSender:
    """Prepares and dispatches HTML email notifications and reports via SMTP."""

    def __init__(
        self,
        config: EmailConfiguration,
        templates_dir: Path = Path("templates"),
    ):
        """Initializes the email sender.

        Args:
            config: EmailConfiguration settings.
            templates_dir: Path to Jinja2 templates folder.
        """
        self.config = config
        self.templates_dir = templates_dir
        self.env = Environment(loader=FileSystemLoader(templates_dir))

    def _send_email(self, subject: str, html_body: str) -> None:
        """Internal helper to configure SMTP connection and send mail.

        Args:
            subject: Subject line for the email.
            html_body: Rendered HTML body content.
        """
        if not self.config.is_valid_for_sending:
            logger.warning(
                "Email configuration is incomplete (missing server, port, "
                "sender, or receiver). Skipping sending email."
            )
            return

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.config.sender_email
        msg["To"] = self.config.receiver_email
        msg.attach(MIMEText(html_body, "html"))

        try:
            logger.info(
                f"Connecting to SMTP server at {self.config.smtp_server}:{self.config.smtp_port}..."
            )
            if self.config.smtp_port == 465:
                server = smtplib.SMTP_SSL(
                    self.config.smtp_server, self.config.smtp_port, timeout=15
                )
            else:
                server = smtplib.SMTP(
                    self.config.smtp_server, self.config.smtp_port, timeout=15
                )
                server.starttls()

            if self.config.smtp_username and self.config.smtp_password:
                logger.info(f"Authenticating SMTP user: {self.config.smtp_username}...")
                server.login(self.config.smtp_username, self.config.smtp_password)

            logger.info(f"Dispatching email: '{subject}' to <{self.config.receiver_email}>")
            server.sendmail(
                self.config.sender_email, self.config.receiver_email, msg.as_string()
            )
            server.quit()
            logger.info("Email delivered successfully.")
        except Exception as e:
            logger.error(f"Failed to dispatch SMTP email: {e}", exc_info=True)
            raise

    def send_status_update(self, report: Report) -> None:
        """Sends a single combined status email listing both healthy and failed services.

        Args:
            report: The latest Report model containing all execution results.
        """
        try:
            template = self.env.get_template("email_status.html")
            html_body = template.render(report=report)
            
            if report.failed > 0:
                subject = f"\u274c HealthPing Status: Outage Detected ({report.failed} Failed)"
            else:
                subject = f"\u2705 HealthPing Status: All Services Online"
                
            self._send_email(subject, html_body)
        except Exception as e:
            logger.error(f"Could not construct/send unified status update email: {e}")

    def send_summary_report(self, report: Report, history: Optional[dict] = None, is_weekly: bool = False) -> None:
        """Sends a periodic summary status report email.

        Args:
            report: The latest Report model.
            history: Optional dictionary of aggregated metrics.
            is_weekly: True for weekly template, False for daily.
        """
        template_name = "weekly_report.html" if is_weekly else "daily_report.html"
        report_label = "Weekly" if is_weekly else "Daily"
        
        try:
            template = self.env.get_template(template_name)
            html_body = template.render(report=report, history=history)
            subject = f"\U0001f4ca HealthPing {report_label} Status Summary"
            self._send_email(subject, html_body)
        except Exception as e:
            logger.error(f"Could not construct/send {report_label.lower()} summary report: {e}")
