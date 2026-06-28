# HealthPing 📊

HealthPing is a robust, centralized, and concurrent service health monitoring tool designed specifically for CI/CD automation and serverless execution. 

Unlike traditional monitoring suites that run persistent background daemons, HealthPing is built to execute a **single monitoring cycle** synchronously, making it perfect for scheduling via **GitHub Actions**. It checks endpoints, reports response times, logs issues, and dispatches real-time alerts or scheduled daily/weekly summaries directly through SMTP email.

---

## 🌟 Features

- **Concurrent Async Monitoring**: Uses `asyncio` and `httpx` to ping dozens of endpoints concurrently, adhering to configurable concurrency limits.
- **Robust Retry Handler**: Supports custom retry counts per service, implemented with **exponential backoff**.
- **Comprehensive Reports**: Automatically generates HTML, CSV, and JSON reports detailing latencies, status codes, and failure reasons.
- **Dynamic Trend Aggregation**: Automatically aggregates historical JSON reports to output daily (24h) trend statistics.
- **Professional Alerts**: Generates and sends styled HTML emails for instant outage warnings and periodic reports.
- **Zero-Daemon Architecture**: Fully configured for execution in stateless serverless runners like GitHub Actions.

---

## 🏗️ Architecture & Folder Structure

HealthPing is built using clean architecture, SOLID design principles, and separation of concerns:

```
HealthPing/
├── .github/
│   └── workflows/
│       ├── health-check.yml     # Runs every 10 min, sends unified status email
│       ├── daily-report.yml     # Runs daily, sends 24h summary
│       └── weekly-report.yml    # Runs weekly, sends 7d summary
├── config/
│   ├── services.json            # Target monitoring endpoints
│   ├── settings.json            # Concurrency & file configurations
│   └── email.json               # Non-sensitive SMTP configurations
├── logs/
│   ├── health.log               # Rotating general execution logs
│   └── error.log                # Rotating warning & error logs
├── models/
│   ├── __init__.py
│   ├── service.py               # Target endpoint Schema
│   ├── settings.py              # Global properties Schema
│   ├── health_result.py         # Test outcome Schema
│   ├── report.py                # Combined stats Schema
│   └── email_config.py          # SMTP Settings Schema
├── monitor/
│   ├── __init__.py
│   └── checker.py               # Async checker and Monitoring Engine
├── notifications/
│   ├── __init__.py
│   └── email_sender.py          # SMTP envelope and dispatch logic
├── reports/
│   ├── __init__.py
│   └── generator.py             # CSV/JSON/HTML file writers & History Aggregator
├── templates/
│   ├── report_template.html     # HTML dashboard template
│   ├── email_status.html        # Unified status update template
│   ├── daily_report.html        # Daily summary email template
│   └── weekly_report.html       # Weekly summary email template
├── main.py                      # Orchestrator CLI entrypoint
├── pyproject.toml               # Project Configuration Details
├── requirements.txt             # Flat dependency file
├── uv.lock                      # UV enviornment details
└── README.md
```

---

## 🚀 Installation & Setup

HealthPing recommends using the fast **`uv`** package manager.

### 1. Clone the Repository
```bash
git clone https://github.com/satyabrata-mishra/HealthPing.git
cd HealthPing
```

### 2. Install Dependencies
Using `uv` (creates a `.venv` and syncs packages):
```bash
uv sync
```
Or using standard `pip`:
```bash
pip install -r requirements.txt
```

### 3. Setup Environment Variables
Create a local `.env` file to securely store SMTP server credentials:
```env
SMTP_USERNAME=your-smtp-username@gmail.com
SMTP_PASSWORD=your-smtp-app-password
EMAIL_RECEIVER=receiver-email@gmail.com
```

---

## ⚙️ Configuration

### Services Configuration (`config/services.json`)
Configure the HTTP endpoints you wish to monitor. Supports GET/POST, custom timeouts, retry limits, and expected response codes:
```json
{
    "services": [
        {
            "name": "VoyageAI Backend",
            "url": "https://voyageai-backend-rg03.onrender.com/",
            "method": "GET",
            "timeout": 60,
            "retries": 3,
            "expected_status": 200,
            "enabled": true,
            "notify_on_failure": true
        }
    ]
}
```

### Global Settings (`config/settings.json`)
Manage concurrency constraints, base retry backoffs, log thresholds, and output formats:
```json
{
    "concurrency": 10,
    "default_timeout": 60,
    "retry_delay": 2,
    "log_level": "INFO",
    "generate_html_report": false,
    "generate_csv_report": false,
    "generate_json_report": false
}
```

### Email Settings (`config/email.json`)
Store basic mail route configurations:
```json
{
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "sender_email": "your_email@gmail.com",
    "receiver_email": "receiver@gmail.com"
}
```

---

## 💻 CLI Usage

HealthPing is executed via arguments to specify the run mode:

```bash
# Execute health check cycle and send alerts on failure (Default)
uv run python main.py --mode check

# Run checks, compile stats for the last 24h, and email a daily summary
uv run python main.py --mode daily

# Run checks, compile stats for the last 7 days, and email a weekly summary
uv run python main.py --mode weekly
```
---

## 🤖 GitHub Actions Integration

HealthPing integrates workflows configured under `.github/workflows/`:

1. **`health-check.yml`**: Runs every 10 minutes, triggers checking, and emails failure alerts immediately if endpoints fail.
2. **`daily-report.yml`**: Runs daily to email 24h aggregate trends.

To deploy, configure the following secrets in your GitHub Repository under **Settings > Secrets and variables > Actions**:
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `EMAIL_RECEIVER`

---

## 🗺️ Roadmap
- [ ] Add support for custom request headers and request body options per service check.
- [ ] Add support for webhook alerts (Slack, Discord, Microsoft Teams).
- [ ] Support custom response content assertion (verifying response JSON keys).
- [ ] Configure database integration for historical trends.

---

## 🤝 Contributing
Contributions are welcome! Please submit a PR or open an issue for feature requests.

---

## ✍️ Author

- **Satyabrata Mishra**