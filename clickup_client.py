import asyncio
import logging

import httpx

from config import CLICKUP_API_KEY

logger = logging.getLogger("clickup_client")
BASE_URL = "https://api.clickup.com/api/v2"
HEADERS = {"Authorization": CLICKUP_API_KEY}


async def get_task_details(task_id: str, retries: int = 3) -> dict:
    if not task_id:
        logger.warning("Task details requested without task_id")
        return {}

    async with httpx.AsyncClient(timeout=10.0) as client:
        for attempt in range(1, retries + 1):
            try:
                response = await client.get(f"{BASE_URL}/task/{task_id}", headers=HEADERS)

                if response.status_code == 200:
                    return response.json()

                if response.status_code in {429, 500, 502, 503, 504}:
                    retry_after = response.headers.get("Retry-After")
                    if retry_after and retry_after.isdigit():
                        wait_time = int(retry_after)
                    else:
                        wait_time = min(2 ** (attempt - 1), 8)

                    logger.warning(
                        "ClickUp API temporary error status=%s task_id=%s attempt=%s/%s wait=%ss",
                        response.status_code,
                        task_id,
                        attempt,
                        retries,
                        wait_time,
                    )
                    if attempt < retries:
                        await asyncio.sleep(wait_time)
                        continue

                if response.status_code == 404:
                    logger.info("ClickUp task not found task_id=%s", task_id)
                    return {}

                logger.error(
                    "ClickUp API returned non-retryable status=%s task_id=%s body=%s",
                    response.status_code,
                    task_id,
                    response.text,
                )
                return {}

            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                wait_time = min(2 ** (attempt - 1), 8)
                logger.warning(
                    "ClickUp network error task_id=%s attempt=%s/%s wait=%ss error=%s",
                    task_id,
                    attempt,
                    retries,
                    wait_time,
                    exc,
                )
                if attempt < retries:
                    await asyncio.sleep(wait_time)
                    continue
                return {}

            except Exception:
                logger.exception("Unexpected ClickUp client error task_id=%s", task_id)
                return {}

    return {}