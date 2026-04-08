import httpx
from dotenv import load_dotenv, find_dotenv
import os
import json

load_dotenv()
API_KEY = os.getenv("CLICKUP_API_KEY")
LIST_ID = "901817248908"

headers = {"Authorization": API_KEY}

response = httpx.get(f"https://api.clickup.com/api/v2/list/{LIST_ID}/task", headers=headers)
tasks = response.json()["tasks"]

def is_important(task):
    # проверяем приоритет
    priority = task.get("priority")
    if priority and priority.get("priority") in ["urgent", "high"]:
        return True
    
    # проверяем теги
    tags = [tag.get("name", "").lower() for tag in task.get("tags", [])]
    if any(tag in ["important", "notify", "tg"] for tag in tags):
        return True
    
    return False

for task in tasks:
    important = is_important(task)
    print(f"{task['name']} — важная: {important}")