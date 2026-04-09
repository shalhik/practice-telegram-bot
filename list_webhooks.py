import httpx

from config import CLICKUP_API_KEY, CLICKUP_TEAM_ID

HEADERS = {"Authorization": CLICKUP_API_KEY}


def list_webhooks() -> None:
    url = f"https://api.clickup.com/api/v2/team/{CLICKUP_TEAM_ID}/webhook"

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.get(url, headers=HEADERS)

        if response.status_code != 200:
            print(f"ERROR: unable to list webhooks status={response.status_code}")
            print(response.text)
            return

        webhooks = response.json().get("webhooks", [])
        if not webhooks:
            print("No webhooks are registered")
            return

        for webhook in webhooks:
            health = webhook.get("health", {}).get("status", "unknown")
            print(f"ID: {webhook.get('id')} | Endpoint: {webhook.get('endpoint')} | Health: {health}")

    except Exception as exc:
        print(f"ERROR: list webhooks request failed: {exc}")


if __name__ == "__main__":
    list_webhooks()