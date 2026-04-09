import httpx

from config import CLICKUP_API_KEY, CLICKUP_TEAM_ID, WEBHOOK_URL

HEADERS = {"Authorization": CLICKUP_API_KEY}


def register() -> None:
    if not WEBHOOK_URL:
        print("ERROR: WEBHOOK_URL is not set in environment")
        return

    url = f"https://api.clickup.com/api/v2/team/{CLICKUP_TEAM_ID}/webhook"
    payload = {
        "endpoint": WEBHOOK_URL,
        "events": [
            "taskCreated",
            "taskStatusUpdated",
            "taskPriorityUpdated",
            "taskTagUpdated",
            "taskDueDateUpdated",
            "taskAssigneeUpdated",
        ],
    }

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.post(url, headers=HEADERS, json=payload)

        if response.status_code != 200:
            print(f"ERROR: registration failed status={response.status_code}")
            print(response.text)
            return

        data = response.json()
        webhook = data.get("webhook", {})
        webhook_id = webhook.get("id", "unknown")
        secret = webhook.get("secret", "")

        print("Webhook registered successfully")
        print(f"Webhook ID: {webhook_id}")
        if secret:
            print("Add this line to .env:")
            print(f"CLICKUP_WEBHOOK_SECRET={secret}")
        else:
            print("WARNING: ClickUp response did not include webhook secret")

    except Exception as exc:
        print(f"ERROR: registration request failed: {exc}")


if __name__ == "__main__":
    register()