import httpx

from config import CLICKUP_API_KEY

HEADERS = {"Authorization": CLICKUP_API_KEY}


def delete_webhook(webhook_id: str) -> None:
    if not webhook_id:
        print("ERROR: webhook_id is required")
        return

    url = f"https://api.clickup.com/api/v2/webhook/{webhook_id}"

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.delete(url, headers=HEADERS)

        if response.status_code == 200:
            print(f"Webhook {webhook_id} deleted successfully")
            return

        print(f"ERROR: delete failed status={response.status_code}")
        print(response.text)
    except Exception as exc:
        print(f"ERROR: delete request failed: {exc}")


if __name__ == "__main__":
    wid = input("Enter webhook ID to delete: ").strip()
    delete_webhook(wid)