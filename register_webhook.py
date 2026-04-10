import logging

from config import CLICKUP_API_KEY, CLICKUP_TEAM_ID, WEBHOOK_URL
from Bot.services import save_webhook_config
from clickup_client import create_webhook

logger = logging.getLogger("webhook_register")

async def register() -> dict:
    api_key = CLICKUP_API_KEY
    team_id = CLICKUP_TEAM_ID

    if not WEBHOOK_URL:
        logger.error("ERROR: WEBHOOK_URL is not set")
        return {"error": "WEBHOOK_URL не задан"}

    if not api_key:
        logger.error("ERROR: CLICKUP_API_KEY is not set")
        return {"error": "CLICKUP_API_KEY не задан"}

    if not team_id:
        logger.error("ERROR: CLICKUP_TEAM_ID is not set")
        return {"error": "CLICKUP_TEAM_ID не задан"}

    try:
        data = await create_webhook(team_id, WEBHOOK_URL)

        if "error" in data:
            return data

        webhook_data = data.get("webhook", {})
        if webhook_data.get("secret"):
            await save_webhook_config(
                webhook_id=webhook_data["id"],
                secret=webhook_data["secret"],
                url=WEBHOOK_URL,
            )
        return data

    except Exception as exc:
        return {"error": str(exc)}


if __name__ == "__main__":
    import asyncio
    asyncio.run(register())