from filters import is_important


def test_is_important_by_priority() -> None:
    task = {
        "priority": {"priority": "High"},
        "tags": [],
        "custom_fields": [],
    }
    assert is_important(task) is True


def test_is_important_by_tag() -> None:
    task = {
        "priority": None,
        "tags": [{"name": "notify"}],
        "custom_fields": [],
    }
    assert is_important(task) is True


def test_is_important_by_custom_field_bool_or_string() -> None:
    task_bool = {
        "priority": None,
        "tags": [],
        "custom_fields": [{"name": "telegram_notify", "value": True}],
    }
    task_str = {
        "priority": None,
        "tags": [],
        "custom_fields": [{"name": "telegram_notify", "value": "true"}],
    }

    assert is_important(task_bool) is True
    assert is_important(task_str) is True


def test_is_not_important_when_no_criteria_match() -> None:
    task = {
        "priority": {"priority": "low"},
        "tags": [{"name": "backlog"}],
        "custom_fields": [{"name": "telegram_notify", "value": False}],
    }
    assert is_important(task) is False
