import asyncio
import hashlib
import hmac
import json
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

SECRET = os.getenv("CLICKUP_WEBHOOK_SECRET", "")
URL = "http://localhost:8000/webhook/clickup"


def sign_body(body: bytes) -> str:
    return hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()


async def send(client: httpx.AsyncClient, payload: dict, signature: str) -> httpx.Response:
    body = json.dumps(payload, separators=(",", ":")).encode()
    headers = {
        "X-Signature": signature,
        "Content-Type": "application/json",
    }
    return await client.post(URL, content=body, headers=headers)


async def test_webhook() -> None:
    if not SECRET:
        print("ERROR: CLICKUP_WEBHOOK_SECRET is not set")
        return

    valid_payload = {
        "id": "test_evt_123",
        "event": "taskPriorityUpdated",
        "task_id": "86ex6e7c7",
        "webhook_id": "test_wh_1",
    }
    valid_body = json.dumps(valid_payload, separators=(",", ":")).encode()
    valid_signature = sign_body(valid_body)

    invalid_payload = {
        "id": "test_evt_124",
        "event": "unknownEvent",
        "task_id": "86ex6e7c7",
        "webhook_id": "test_wh_1",
    }
    invalid_body = json.dumps(invalid_payload, separators=(",", ":")).encode()
    invalid_signature = sign_body(invalid_body)

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await send(client, valid_payload, valid_signature)
        print(f"VALID PAYLOAD: {response.status_code} {response.text}")

        response = await send(client, valid_payload, "wrong-signature")
        print(f"BAD SIGNATURE: {response.status_code} (expected 401)")

        response = await send(client, invalid_payload, invalid_signature)
        print(f"INVALID EVENT: {response.status_code} (expected 400)")


if __name__ == "__main__":
    asyncio.run(test_webhook())