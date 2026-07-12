import asyncio
import logging
import time
import httpx
from config import SERVICES, CONCURRENCY, RETRY_DELAY

# Configure simple console logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("healthping")

async def check_service(semaphore: asyncio.Semaphore, client: httpx.AsyncClient, service: dict) -> bool:
    """Checks the health of a single service, performing retries on failure."""
    name = service["name"]
    url = service["url"]
    method = service.get("method", "GET").upper()
    timeout = service.get("timeout", 20)
    retries = service.get("retries", 3)
    expected_status = service.get("expected_status", 200)
    headers = service.get("headers") or {}
    payload = service.get("payload")

    if "User-Agent" not in headers:
        headers["User-Agent"] = "HealthPing/1.0.0"

    async with semaphore:
        for attempt in range(retries + 1):
            if attempt > 0:
                # Exponential backoff delay
                backoff = RETRY_DELAY * (2 ** (attempt - 1))
                logger.info(
                    f"Retrying check for '{name}' (attempt {attempt}/{retries}) in {backoff:.2f}s..."
                )
                await asyncio.sleep(backoff)

            start_time = time.monotonic()
            try:
                logger.debug(f"Sending health check to '{name}' ({url})")
                response = await client.request(
                    method=method,
                    url=url,
                    timeout=timeout,
                    json=payload if method == "POST" else None,
                    headers=headers,
                )
                latency = time.monotonic() - start_time

                if response.status_code == expected_status:
                    logger.info(
                        f"Service '{name}' is HEALTHY. Status: {response.status_code}. Latency: {latency:.4f}s"
                    )
                    return True
                else:
                    logger.warning(
                        f"Service '{name}' returned status {response.status_code} (expected {expected_status}) on attempt {attempt}"
                    )
            except httpx.TimeoutException as e:
                logger.warning(f"Timeout checking service '{name}' on attempt {attempt}: {e}")
            except httpx.HTTPError as e:
                logger.warning(f"HTTP error checking service '{name}' on attempt {attempt}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error checking service '{name}' on attempt {attempt}: {e}", exc_info=True)

        logger.error(f"Service '{name}' health check FAILED after {retries} retries.")
        return False

async def main() -> None:
    """Main function executing all checks concurrently."""
    logger.info(f"Starting health check cycle for {len(SERVICES)} services (concurrency limit: {CONCURRENCY})...")
    
    semaphore = asyncio.Semaphore(CONCURRENCY)
    limits = httpx.Limits(max_connections=CONCURRENCY)
    
    start_time = time.monotonic()
    async with httpx.AsyncClient(limits=limits) as client:
        tasks = [check_service(semaphore, client, svc) for svc in SERVICES]
        results = await asyncio.gather(*tasks)
    
    elapsed = time.monotonic() - start_time
    healthy_count = sum(1 for r in results if r)
    failed_count = len(SERVICES) - healthy_count
    
    logger.info(
        f"Finished health check cycle. Status: {healthy_count} healthy, {failed_count} failed. "
        f"Elapsed time: {elapsed:.2f}s"
    )

if __name__ == "__main__":
    asyncio.run(main())