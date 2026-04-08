import httpx
import os
from dotenv import load_dotenv

load_dotenv()

# Твои данные из .env
API_KEY = os.getenv("CLICKUP_API_KEY")
# Твой адрес из ngrok (ОБЯЗАТЕЛЬНО добавь /webhook/clickup в конце)
WEBHOOK_URL = "https://centralistic-unstrewn-lianne.ngrok-free.dev/webhook/clickup"
# Твой ID команды (из URL браузера)
TEAM_ID = "90182602228" 

HEADERS = {"Authorization": API_KEY}

def register():
    url = f"https://api.clickup.com/api/v2/team/{TEAM_ID}/webhook"
    
    # Какие события мы хотим слушать? (Согласно ТЗ: создание, смена статуса, приоритета)
    payload = {
        "endpoint": WEBHOOK_URL,
        "events": [
            "taskCreated", 
            "taskStatusUpdated", 
            "taskPriorityUpdated",
            "taskTagUpdated"
        ]
    }
    
    print(f"Попытка регистрации вебхука на адрес: {WEBHOOK_URL}...")
    
    with httpx.Client() as client:
        response = client.post(url, headers=HEADERS, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Успех! Вебхук зарегистрирован.")
            print(f"ID вебхука: {data['webhook']['id']}")
        else:
            print(f"❌ Ошибка: {response.status_code}")
            print(response.text)

if __name__ == "__main__":
    register()