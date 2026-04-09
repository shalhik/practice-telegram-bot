import httpx
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("CLICKUP_API_KEY")
TEAM_ID = "90182601546" 
HEADERS = {"Authorization": API_KEY}

def list_webhooks():
    url = f"https://api.clickup.com/api/v2/team/{TEAM_ID}/webhook"
    with httpx.Client() as client:
        response = client.get(url, headers=HEADERS)
        webhooks = response.json().get('webhooks', [])
        if not webhooks:
            print("У тебя нет зарегистрированных вебхуков!")
        for wh in webhooks:
            print(f"ID: {wh['id']} | Endpoint: {wh['endpoint']} | Health: {wh['health']['status']}")

if __name__ == "__main__":
    list_webhooks()