import asyncio
import logging

import httpx

from config import CLICKUP_API_KEY  # дефолтный ключ из .env

logger = logging.getLogger("clickup_client")
BASE_URL = "https://api.clickup.com/api/v2"


async def get_headers() -> dict:
    from Bot.services import get_webhook_config_from_db

    cfg = await get_webhook_config_from_db()
    api_key = cfg.api_key if cfg and cfg.api_key else CLICKUP_API_KEY

    if not api_key:
        logger.error("get_headers: API ключ не найден ни в БД, ни в .env")
        return {}

    logger.info(
        "Using ClickUp API key: source=%s, prefix=%s..., len=%s",
        "db" if cfg and cfg.api_key else "env",
        api_key[:6],
        len(api_key),
    )

    return {"Authorization": api_key}

async def get_spaces(team_id: str) -> list[dict]:
    headers = await get_headers()
    if not headers:
        return []

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(f"{BASE_URL}/team/{team_id}/space", headers=headers)
            if response.status_code == 200:
                data = response.json()
                logger.info("Получены spaces: %s штук", len(data.get("spaces", [])))
                return data.get("spaces", [])
            else:
                logger.error("get_spaces: API ошибка %s - %s", response.status_code, response.text)
                return []
        except Exception as e:
            logger.error("get_spaces: Ошибка сети - %s", str(e))
            return []


async def get_space_lists(space_id: str) -> list[dict]:
    headers = await get_headers()
    if not headers:
        return []

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(f"{BASE_URL}/space/{space_id}/list", headers=headers)
            if response.status_code == 200:
                data = response.json()
                logger.info(
                    "Получены списки для space %s: %s штук",
                    space_id,
                    len(data.get("lists", [])),
                )
                return data.get("lists", [])
            else:
                logger.error("get_space_lists: API ошибка %s - %s", response.status_code, response.text)
                return []
        except Exception as e:
            logger.error("get_space_lists: Ошибка сети - %s", str(e))
            return []


async def get_lists(team_id: str) -> list[dict]:
    headers = await get_headers()
    if not headers:
        return []

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(f"{BASE_URL}/team/{team_id}/list", headers=headers)
            if response.status_code == 200:
                data = response.json()
                logger.info("Получены все списки: %s штук", len(data.get("lists", [])))
                return data.get("lists", [])
            else:
                logger.error("get_lists: API ошибка %s - %s", response.status_code, response.text)
                return []
        except Exception as e:
            logger.error("get_lists: Ошибка сети - %s", str(e))
            return []


async def get_list_tasks(list_id: str) -> list[dict]:
    headers = await get_headers()
    if not headers:
        return []

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(f"{BASE_URL}/list/{list_id}/task?archived=false", headers=headers)
            if response.status_code == 200:
                data = response.json()
                logger.info(
                    "Получены задачи списка %s: %s штук",
                    list_id,
                    len(data.get("tasks", [])),
                )
                return data.get("tasks", [])
            else:
                logger.error("get_list_tasks: API ошибка %s - %s", response.status_code, response.text)
                return []
        except Exception as e:
            logger.error("get_list_tasks: Ошибка сети - %s", str(e))
            return []


async def get_task_details(task_id: str, retries: int = 3) -> dict:
    if not task_id:
        logger.warning("Task details requested without task_id")
        return {}

    headers = await get_headers()
    if not headers:
        return {}

    async with httpx.AsyncClient(timeout=10.0) as client:
        for attempt in range(1, retries + 1):
            try:
                response = await client.get(f"{BASE_URL}/task/{task_id}", headers=headers)

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


async def create_webhook(team_id: str, endpoint_url: str) -> dict:
    headers = await get_headers()
    if not headers:
        return {"error": "API ключ не найден"}

    url = f"{BASE_URL}/team/{team_id}/webhook"
    payload = {
        "endpoint": endpoint_url,
        "events": [
            "taskCreated",
            "taskStatusUpdated",
            "taskPriorityUpdated",
            "taskTagUpdated",
            "taskDueDateUpdated",
            "taskAssigneeUpdated",
        ],
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                return response.json()
            return {"error": response.text, "code": response.status_code}
        except Exception as e:
            logger.error("create_webhook: Ошибка сети - %s", str(e))
            return {"error": str(e)}


async def list_webhooks(team_id: str) -> list[dict]:
    headers = await get_headers()
    if not headers:
        return []

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(f"{BASE_URL}/team/{team_id}/webhook", headers=headers)
            return response.json().get("webhooks", []) if response.status_code == 200 else []
        except Exception as e:
            logger.error("list_webhooks: %s", e)
            return []


async def delete_webhook(webhook_id: str) -> bool:
    headers = await get_headers()
    if not headers:
        return False

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.delete(f"{BASE_URL}/webhook/{webhook_id}", headers=headers)
            return response.status_code == 200
        except Exception as e:
            logger.error("delete_webhook: %s", e)
            return False


async def run_delete():
    webhook_id = input("Введите ID вебхука для удаления: ").strip()
    if not webhook_id:
        print("Ошибка: ID вебхука обязателен.")
        return

    print(f"⏳ Удаление вебхука {webhook_id}...")
    success = await delete_webhook(webhook_id)

    if success:
        print(f"Вебхук {webhook_id} успешно удален.")
    else:
        print(f"Не удалось удалить вебхук. Проверьте логи в clickup_client.")


if __name__ == "__main__":
    asyncio.run(run_delete())