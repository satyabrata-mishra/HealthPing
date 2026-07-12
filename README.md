# HealthPing 📊

HealthPing is a robust, centralized, and concurrent service health monitoring tool designed specifically for CI/CD automation and serverless execution. 

Unlike traditional monitoring suites that run persistent background daemons, HealthPing is built to execute a **single monitoring cycle** synchronously, making it perfect for scheduling via **GitHub Actions**. It concurrently checks endpoints, handles retries, and logs outcomes directly to the console.

---

## 🌟 Features

- **Concurrent Async Monitoring**: Uses `asyncio` and `httpx` to ping all configured endpoints concurrently, adhering to the configured concurrency limit.
- **Robust Retry Handler**: Supports custom retry counts per service, implemented with **exponential backoff** to handle transient network issues or cold starts.
- **Zero-Daemon Architecture**: Fully configured for execution in stateless serverless runners like GitHub Actions.
- **Minimalistic & Simple**: Single-script execution using direct Python configuration instead of complex schema loaders or output reports.

---

## 🏗️ Architecture & Folder Structure

HealthPing is built with a minimal codebase consisting of just the entry point and Python configuration file:

```
HealthPing/
├── .github/
│   └── workflows/
│       └── health-check.yml     # Runs every 15 min on GitHub Actions
├── config.py                    # Target monitoring endpoints & settings
├── main.py                      # Core async ping execution entrypoint
├── pyproject.toml               # Project Configuration Details
├── requirements.txt             # Flat dependency file
├── uv.lock                      # UV environment details
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

---

## ⚙️ Configuration (`config.py`)

All endpoints and global variables are configured directly inside `config.py`:

```python
SERVICES = [
    {
        "name": "VoyageAI Backend",
        "url": "https://voyageai-backend-rg03.onrender.com/",
        "method": "GET",
        "timeout": 60,
        "retries": 3,
        "expected_status": 200,
    }
]

# Global settings
CONCURRENCY = 10
RETRY_DELAY = 2
```

- **`SERVICES`**: A list of service dicts specifying the service `name`, target `url`, request `method` (e.g. GET/POST), timeout threshold in seconds (`timeout`), number of retry attempts (`retries`), and the expected response code (`expected_status`).
- **`CONCURRENCY`**: Maximum number of concurrent outgoing checks.
- **`RETRY_DELAY`**: The base retry delay in seconds for backoff (`base_delay * 2^(attempt - 1)`).

---

## 💻 CLI Usage

HealthPing is executed via a simple Python command:

```bash
# Execute health check cycle
uv run python main.py
```

---

## 🤖 GitHub Actions Integration

HealthPing integrates a workflow under `.github/workflows/health-check.yml`:

- **`health-check.yml`**: Runs every 15 minutes, triggering the health checks in a headless runner, logging outcomes directly to the GitHub Action logs.

---

## 🤝 Contributing

Contributions are welcome! Please submit a PR or open an issue for feature requests.

---

## ✍️ Author

- **Satyabrata Mishra**