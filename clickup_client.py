import httpx
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("CLICKUP_API_KEY")
BASE_URL = "https://api.clickup.com/api/v2"
HEADERS = {"Authorization": API_KEY}

async def get_task_details(task_id: str) -> dict:
    """
    Получает полную информацию о задаче из ClickUp.
    Это нужно, потому что Webhook присылает только ID задачи.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/task/{task_id}", headers=HEADERS)
        if response.status_code == 200:
            return response.json()
        return {}