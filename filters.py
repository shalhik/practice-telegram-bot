"""
Модуль для определения важности задач.
Согласно разделу 3 ТЗ.
"""

def is_important(task: dict) -> bool:
    # 1. Проверяем приоритет (High или Urgent)
    priority_obj = task.get("priority")
    if priority_obj:
        p_name = str(priority_obj.get("priority", "")).lower()
        if p_name in ["high", "urgent"]:
            print(f"✅ Задача важна: приоритет {p_name}")
            return True

    # 2. Проверяем теги (important, notify, tg)
    tags = [tag.get("name", "").lower() for tag in task.get("tags", [])]
    important_tags = {"important", "notify", "tg"}
    if any(tag in important_tags for tag in tags):
        print(f"✅ Задача важна: тег найден в {tags}")
        return True

    # 3. Проверяем Custom Field (telegram_notify == True)
    custom_fields = task.get("custom_fields", [])
    for field in custom_fields:
        if field.get("name") == "telegram_notify":
            value = field.get("value")
            if value is True or value == "true":
                print(f"✅ Задача важна: custom field telegram_notify={value}")
                return True

    print(f"⏭️ Задача не важна (приоритет={priority_obj}, теги={tags})")
    return False