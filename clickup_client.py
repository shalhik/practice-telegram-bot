import httpx
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("CLICKUP_API_KEY")
BASE_URL = "https://api.clickup.com/api/v2"

# Проверяем наличие API ключа
if not API_KEY:
    print("⚠️ ОШИБКА: CLICKUP_API_KEY не установлен в переменных окружения!")
    print("Создайте файл .env или установите переменную окружения CLICKUP_API_KEY")

HEADERS = {"Authorization": API_KEY} if API_KEY else {}

async def get_task_details(task_id: str) -> dict:
    """
    Получает полную информацию о задаче из ClickUp.
    Это нужно, потому что Webhook присылает только ID задачи.
    """
    if not API_KEY:
        print(f"get_task_details: API ключ не установлен")
        return {}
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/task/{task_id}", headers=HEADERS)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"get_task_details: API ошибка {response.status_code} - {response.text}")
                return {}
        except Exception as e:
            print(f"get_task_details: Ошибка сети - {str(e)}")
            return {}

async def get_spaces(team_id: str) -> list[dict]:
    """
    Получает пространства (spaces) команды ClickUp.
    """
    if not API_KEY:
        print(f"get_spaces: API ключ не установлен")
        return []
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/team/{team_id}/space", headers=HEADERS)
            if response.status_code == 200:
                data = response.json()
                print(f"Получены spaces: {len(data.get('spaces', []))} штук")
                return data.get("spaces", [])
            else:
                print(f"get_spaces: API ошибка {response.status_code} - {response.text}")
                return []
        except Exception as e:
            print(f"get_spaces: Ошибка сети - {str(e)}")
            return []

async def get_space_lists(space_id: str) -> list[dict]:
    """
    Получает списки (lists) по Space в ClickUp.
    """
    if not API_KEY:
        print(f"get_space_lists: API ключ не установлен")
        return []
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/space/{space_id}/list", headers=HEADERS)
            if response.status_code == 200:
                data = response.json()
                print(f"Получены списки для space {space_id}: {len(data.get('lists', []))} штук")
                return data.get("lists", [])
            else:
                print(f"get_space_lists: API ошибка {response.status_code} - {response.text}")
                return []
        except Exception as e:
            print(f"get_space_lists: Ошибка сети - {str(e)}")
            return []

async def get_lists(team_id: str) -> list[dict]:
    """
    Получает список всех списков (lists) в команде ClickUp.
    """
    if not API_KEY:
        print(f"get_lists: API ключ не установлен")
        return []
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/team/{team_id}/list", headers=HEADERS)
            if response.status_code == 200:
                data = response.json()
                print(f"Получены все списки: {len(data.get('lists', []))} штук")
                return data.get("lists", [])
            else:
                print(f"get_lists: API ошибка {response.status_code} - {response.text}")
                return []
        except Exception as e:
            print(f"get_lists: Ошибка сети - {str(e)}")
            return []

async def get_list_tasks(list_id: str) -> list[dict]:
    """
    Получает задачи списка ClickUp.
    """
    if not API_KEY:
        print(f"get_list_tasks: API ключ не установлен")
        return []
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{BASE_URL}/list/{list_id}/task?archived=false",
                headers=HEADERS,
            )
            if response.status_code == 200:
                data = response.json()
                print(f"Получены задачи списка {list_id}: {len(data.get('tasks', []))} штук")
                return data.get("tasks", [])
            else:
                print(f"get_list_tasks: API ошибка {response.status_code} - {response.text}")
                return []
        except Exception as e:
            print(f"get_list_tasks: Ошибка сети - {str(e)}")
            return []
