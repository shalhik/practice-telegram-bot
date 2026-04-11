import hashlib
import hmac
import json

import pytest
from fastapi import HTTPException

import main


@pytest.mark.asyncio
async def test_verify_signature_accepts_valid_signature_from_db_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_secret() -> str:
        return "db-secret"

    monkeypatch.setattr(main, "get_webhook_secret_from_db", fake_secret)

    body = json.dumps({"event": "taskCreated", "task_id": "1", "webhook_id": "w1"}).encode()
    signature = hmac.new(b"db-secret", body, hashlib.sha256).hexdigest()

    await main.verify_signature({"X-Signature": signature}, body)


@pytest.mark.asyncio
async def test_verify_signature_rejects_missing_signature(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_secret() -> str:
        return "db-secret"

    monkeypatch.setattr(main, "get_webhook_secret_from_db", fake_secret)

    with pytest.raises(HTTPException) as exc_info:
        await main.verify_signature({}, b"{}")

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_verify_signature_rejects_invalid_signature(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_secret() -> str:
        return "db-secret"

    monkeypatch.setattr(main, "get_webhook_secret_from_db", fake_secret)

    body = b"{}"
    with pytest.raises(HTTPException) as exc_info:
        await main.verify_signature({"X-Signature": "bad"}, body)

    assert exc_info.value.status_code == 401


def test_build_event_id_uses_payload_id_when_present() -> None:
    payload = {"id": "evt-123", "event": "taskCreated"}
    assert main.build_event_id(payload) == "evt-123"


def test_build_event_id_is_deterministic_when_no_id() -> None:
    payload_a = {"event": "taskCreated", "task_id": "123", "x": {"a": 1, "b": 2}}
    payload_b = {"x": {"b": 2, "a": 1}, "task_id": "123", "event": "taskCreated"}

    assert main.build_event_id(payload_a) == main.build_event_id(payload_b)
