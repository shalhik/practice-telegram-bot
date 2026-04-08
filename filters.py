"""
Модуль для определения важности задач.
Согласно разделу 3 ТЗ.
"""

def is_important(task: dict) -> bool:
    # 1. Проверяем приоритет (High или Urgent)
    # В ClickUp API приоритет — это объект. Нам нужно поле 'priority' внутри него.
    priority_obj = task.get("priority")
    if priority_obj:
        # Приводим к нижнему регистру, чтобы избежать ошибок сравнения
        p_name = str(priority_obj.get("priority", "")).lower()
        if p_name in ["high", "urgent"]:
            return True

    # 2. Проверяем теги (important, notify, tg)
    # Нам нужно достать список имен всех тегов
    tags = [tag.get("name", "").lower() for tag in task.get("tags", [])]
    important_tags = {"important", "notify", "tg"}
    # Если хотя бы один тег из задачи есть в нашем списке — задача важная
    if any(tag in important_tags for tag in tags):
        return True

    # 3. Проверяем Custom Field (telegram_notify == True)
    custom_fields = task.get("custom_fields", [])
    for field in custom_fields:
        if field.get("name") == "telegram_notify":
            # Важно: ClickUp может вернуть строку "true" или булево True
            value = field.get("value")
            if value is True or value == "true":
                return True

    return False