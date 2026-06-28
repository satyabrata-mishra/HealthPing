import asyncio
import time
import logging
from datetime import datetime, timezone
from typing import List, Optional
import httpx

from models.service import Service
from models.settings import Settings
from models.health_result import HealthResult

logger = logging.getLogger(__name__)


class HealthChecker:
    """Performs asynchronous health checks on services with retries and exponential backoff."""

    def __init__(self, client: httpx.AsyncClient, retry_delay: float = 2.0):
        """Initializes the health checker.

        Args:
            client: The httpx AsyncClient instance to make requests with.
            retry_delay: The base retry delay in seconds for backoff.
        """
        self.client = client
        self.retry_delay = retry_delay

    async def check_service(self, service: Service) -> HealthResult:
        """Checks the health of a single service, performing retries on failure.

        Args:
            service: The Service model to check.

        Returns:
            HealthResult: The result of the health check.
        """
        max_retries = service.retries
        timeout = service.timeout

        last_status_code: Optional[int] = None
        last_failure_reason: Optional[str] = None
        latency = 0.0
        retry_count = 0

        for attempt in range(max_retries + 1):
            retry_count = attempt
            if attempt > 0:
                # Exponential backoff delay: base_delay * 2^(attempt - 1)
                backoff = self.retry_delay * (2 ** (attempt - 1))
                logger.info(
                    f"Retrying check for '{service.name}' (attempt {attempt}/{max_retries}) "
                    f"in {backoff:.2f}s..."
                )
                await asyncio.sleep(backoff)

            start_time = time.monotonic()
            timestamp = datetime.now(timezone.utc).isoformat()

            try:
                headers = service.headers or {}
                if "User-Agent" not in headers:
                    headers["User-Agent"] = "HealthPing/1.0.0"

                logger.debug(f"Sending health check to '{service.name}' ({service.url})")
                
                # Make HTTP call using client
                response = await self.client.request(
                    method=service.method.upper(),
                    url=str(service.url),
                    timeout=timeout,
                    json=service.payload if service.method.upper() == "POST" else None,
                    headers=headers,
                )

                latency = time.monotonic() - start_time
                last_status_code = response.status_code

                if response.status_code == service.expected_status:
                    logger.info(
                        f"Service '{service.name}' is healthy. Status: {response.status_code}. "
                        f"Latency: {latency:.4f}s"
                    )
                    return HealthResult(
                        service_name=service.name,
                        url=str(service.url),
                        status="HEALTHY",
                        http_status_code=response.status_code,
                        latency=latency,
                        timestamp=timestamp,
                        failure_reason=None,
                        retry_count=retry_count,
                    )
                else:
                    last_failure_reason = (
                        f"Expected status {service.expected_status}, "
                        f"got {response.status_code}"
                    )
                    logger.warning(
                        f"Service '{service.name}' returned unexpected status "
                        f"{response.status_code} on attempt {attempt}: {last_failure_reason}"
                    )

            except httpx.TimeoutException as e:
                latency = time.monotonic() - start_time
                last_status_code = None
                last_failure_reason = f"Request timed out after {timeout}s: {e}"
                logger.warning(
                    f"Timeout checking service '{service.name}' on attempt {attempt}: {e}"
                )

            except httpx.HTTPError as e:
                latency = time.monotonic() - start_time
                last_status_code = None
                last_failure_reason = f"HTTP request failed: {e}"
                logger.warning(
                    f"HTTP error checking service '{service.name}' on attempt {attempt}: {e}"
                )

            except Exception as e:
                latency = time.monotonic() - start_time
                last_status_code = None
                last_failure_reason = f"Unexpected error: {str(e)}"
                logger.error(
                    f"Unexpected error checking service '{service.name}' on attempt {attempt}: {e}",
                    exc_info=True,
                )

        # If we got here, all attempts failed
        logger.error(
            f"Service '{service.name}' health check failed. "
            f"Reason: {last_failure_reason}. Retries: {retry_count}"
        )
        return HealthResult(
            service_name=service.name,
            url=str(service.url),
            status="FAILED",
            http_status_code=last_status_code,
            latency=latency,
            timestamp=datetime.now(timezone.utc).isoformat(),
            failure_reason=last_failure_reason or "All checks failed",
            retry_count=retry_count,
        )


class MonitoringEngine:
    """Manages concurrent execution of health checks across multiple services."""

    def __init__(self, settings: Settings):
        """Initializes the monitoring engine with global settings.

        Args:
            settings: Global HealthPing settings.
        """
        self.settings = settings
        self.semaphore = asyncio.Semaphore(settings.concurrency)

    async def run_checks(self, services: List[Service]) -> List[HealthResult]:
        """Runs checks for all enabled services concurrently.

        Args:
            services: List of services to check.

        Returns:
            List[HealthResult]: Results of all executed health checks.
        """
        enabled_services = [s for s in services if s.enabled]
        if not enabled_services:
            logger.info("No enabled services found to check.")
            return []

        logger.info(
            f"Starting health check cycle for {len(enabled_services)} services "
            f"(concurrency limit: {self.settings.concurrency})..."
        )

        # Configure default timeout in AsyncClient
        limits = httpx.Limits(max_connections=self.settings.concurrency)
        async with httpx.AsyncClient(
            timeout=self.settings.default_timeout, limits=limits
        ) as client:
            checker = HealthChecker(client, retry_delay=float(self.settings.retry_delay))

            async def worker(service: Service) -> HealthResult:
                # Restrict concurrent checks with a semaphore
                async with self.semaphore:
                    return await checker.check_service(service)

            # Schedule all workers concurrently
            tasks = [worker(s) for s in enabled_services]
            results = await asyncio.gather(*tasks)

        logger.info("Finished health check cycle.")
        return list(results)
