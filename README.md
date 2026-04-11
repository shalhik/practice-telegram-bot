# ClickUp -> Telegram: MVP интеграция

Проект отправляет уведомления в Telegram по важным задачам ClickUp через webhook.

Система состоит из двух частей:
- backend на FastAPI принимает webhook от ClickUp, валидирует подпись, фильтрует события и рассылает уведомления;
- Telegram-бот на aiogram позволяет пользователю подписаться на нужные списки и управлять уведомлениями.

## Стек

- Python 3.11
- FastAPI + Uvicorn
- aiogram
- SQLAlchemy (async) + Alembic + asyncpg
- httpx
- pydantic
- python-dotenv
- PostgreSQL (через Docker Compose)

## Что умеет MVP

- Принимает webhook от ClickUp на endpoint `/webhook/clickup`
- Проверяет подпись webhook (`X-ClickUp-Signature`/`X-Signature`)
- Фильтрует важные задачи по правилам:
  - приоритет `High` или `Urgent`
  - теги `important`, `notify`, `tg`
  - custom field `telegram_notify=true`
- Поддерживает события ClickUp:
  - `taskCreated`
  - `taskStatusUpdated`
  - `taskPriorityUpdated`
  - `taskDueDateUpdated`
  - `taskAssigneeUpdated`
  - `taskTagUpdated`
- Отправляет уведомления только в подписанные Telegram-чаты
- Подавляет дубликаты событий

## Структура запуска

Нужно держать запущенными 3 процесса:
1. backend (FastAPI)
2. bot (aiogram)
3. публичный туннель (например, ngrok), если запускаете локально

## Подготовка окружения

### 1. Установите зависимости

```bash
pip install -r requirements.txt
```

### 2. Поднимите PostgreSQL

```bash
docker compose up -d db
```

### 3. Создайте и заполните `.env`

Обязательные переменные:
- `DATABASE_URL`
- `TELEGRAM_TOKEN`
- `CLICKUP_API_KEY`
- `CLICKUP_TEAM_ID`
- `CLICKUP_WEBHOOK_SECRET`
- `WEBHOOK_URL`

Пример:

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/clickup_db
TELEGRAM_TOKEN=123456789:YOUR_TELEGRAM_BOT_TOKEN
CLICKUP_API_KEY=pk_xxx
CLICKUP_TEAM_ID=123456789
CLICKUP_WEBHOOK_SECRET=your_webhook_secret
WEBHOOK_URL=https://your-domain-or-ngrok/webhook/clickup
```

Важно:
- `WEBHOOK_URL` должен быть публично доступен ClickUp.
- `CLICKUP_WEBHOOK_SECRET` в `.env` должен совпадать с секретом webhook в ClickUp.

## Инициализация БД

Проект работает в режиме migration-first (таблицы создаются миграциями, а не автоматически при старте).

```bash
alembic upgrade head
```

## Запуск проекта

### 1. Запустите backend

```bash
uvicorn main:app --reload
```

### 2. Запустите Telegram-бота

```bash
python -m Bot.main
```

### 3. Если backend локальный, поднимите туннель

Пример с ngrok:

```bash
ngrok http 8000
```

Возьмите публичный URL и укажите его в `WEBHOOK_URL` в формате:

`https://<your-domain>/webhook/clickup`

После изменения `.env` перезапустите backend и bot.

## Регистрация webhook в ClickUp

В MVP webhook регистрируется вручную.

1. Убедитесь, что в `.env` заполнены:
   - `CLICKUP_API_KEY`
   - `CLICKUP_TEAM_ID`
   - `WEBHOOK_URL`
2. Выполните:

```bash
python register_webhook.py
```

3. Проверка списка webhook:

```bash
python list_webhooks.py
```

## Как пользоваться ботом (для конечного пользователя)

### Основные команды

- `/start` - стартовое меню
- `/connect` - выбрать Space и подписаться на нужный List
- `/watch` - включить уведомления в текущем чате
- `/unwatch` - выключить уведомления в текущем чате
- `/important` - показать важные задачи по вашим подпискам
- `/task <task_id>` - показать карточку конкретной задачи

### Типовой сценарий

1. Откройте бота и выполните `/connect`.
2. Выберите Space и List, на который хотите подписаться.
3. В ClickUp создайте или обновите важную задачу.
4. ClickUp отправит webhook в backend.
5. Backend проверит подпись и отправит уведомление в Telegram.

## Логика важности задачи

Задача считается важной, если выполнено хотя бы одно условие:
- priority = `High` или `Urgent`
- есть тег `important`, `notify` или `tg`
- custom field `telegram_notify=true`

## Тесты

```bash
pytest -q
```

Если тесты не запускаются из-за импортов, проверьте, что запускаете команду из корня проекта.

## Частые проблемы и решения

### 401 Unauthorized на webhook

Проверьте:
- совпадает ли `CLICKUP_WEBHOOK_SECRET` с секретом в ClickUp;
- приходит ли корректный заголовок подписи;
- совпадает ли `webhook_id` в payload и в сохраненной конфигурации.

### Бот не отвечает / ошибка токена

Проверьте `TELEGRAM_TOKEN` в `.env` и перезапустите процесс бота.

### Нет уведомлений

Проверьте по порядку:
- есть ли подписка через `/connect`;
- включены ли уведомления (`/watch`);
- важная ли задача по правилам фильтра;
- доходит ли webhook до backend (логи Uvicorn/FastAPI).

### Ошибки БД

Убедитесь, что миграции применены:

```bash
alembic upgrade head
```

## Безопасность

- Не передавайте `CLICKUP_API_KEY` пользователям бота.
- Не публикуйте `.env` в git.
- Используйте только HTTPS webhook URL.
