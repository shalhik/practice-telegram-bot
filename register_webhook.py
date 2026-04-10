import logging

from config import CLICKUP_API_KEY, CLICKUP_TEAM_ID, WEBHOOK_URL
from Bot.services import save_webhook_config
from clickup_client import create_webhook

logger = logging.getLogger("webhook_register")

async def register(override_api_key: str = None, override_team_id: str = None) -> dict:
    api_key = override_api_key or CLICKUP_API_KEY
    team_id = override_team_id or CLICKUP_TEAM_ID
    
    if not WEBHOOK_URL:
        logger.error("ERROR: WEBHOOK_URL is not set")
        return {"error": "WEBHOOK_URL не задан "}

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
                api_key=api_key,
                team_id=team_id
            )
        return data

    except Exception as exc:
        return {"error": str(exc)}


if __name__ == "__main__":
    import asyncio
    asyncio.run(register())