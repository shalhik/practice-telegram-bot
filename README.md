# ClickUp -> Telegram MVP

MVP backend service that receives ClickUp webhooks, filters important tasks, and sends notifications to Telegram chats.

## Stack

- FastAPI + Uvicorn
- aiogram
- SQLAlchemy + Alembic + asyncpg
- httpx
- pydantic
- python-dotenv

## What MVP does

- Receives and validates ClickUp webhook requests by signature
- Filters only important tasks:
  - priority: `High` or `Urgent`
  - tags: `important`, `notify`, `tg`
  - custom field: `telegram_notify = true`
- Sends Telegram notifications for events:
  - `taskCreated`
  - `taskStatusUpdated`
  - `taskPriorityUpdated`
  - `taskDueDateUpdated`
  - `taskAssigneeUpdated`
  - `taskTagUpdated`
- Supports Telegram commands:
  - `/start`
  - `/connect`
  - `/watch`
  - `/unwatch`
  - `/important`
  - `/task <id>`
- Deduplicates webhook events

## Configuration (.env)

Required:

- `DATABASE_URL`
- `TELEGRAM_TOKEN`
- `CLICKUP_API_KEY`
- `CLICKUP_TEAM_ID`
- `CLICKUP_WEBHOOK_SECRET`
- `WEBHOOK_URL`

Example:

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/clickup_db
TELEGRAM_TOKEN=123456789:YOUR_TELEGRAM_BOT_TOKEN
CLICKUP_API_KEY=pk_xxx
CLICKUP_TEAM_ID=123456789
CLICKUP_WEBHOOK_SECRET=your_webhook_secret
WEBHOOK_URL=https://your-domain-or-ngrok/webhook/clickup
```

## Run locally

1. Start PostgreSQL:

```bash
docker compose up -d db
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Apply migrations:

```bash
alembic upgrade head
```

4. Start backend:

```bash
uvicorn main:app --reload
```

5. Start bot:

```bash
python -m Bot.main
```

## Manual webhook setup (MVP)

Webhook registration is manual in this MVP.

1. Make sure `CLICKUP_API_KEY`, `CLICKUP_TEAM_ID`, `WEBHOOK_URL` are set in `.env`.
2. Run:

```bash
python register_webhook.py
```

3. Optional check:

```bash
python list_webhooks.py
```

## Demo flow

1. In Telegram, run `/connect` and subscribe chat to a ClickUp list.
2. Create or update an important task in ClickUp.
3. ClickUp sends webhook to backend.
4. Backend validates signature, filters task, sends notification to subscribed chats.

## Notes

- ClickUp API key must stay on server side only.
- If `.env` was changed, restart running bot/backend processes.
