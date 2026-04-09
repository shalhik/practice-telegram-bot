from typing import Literal, Optional

from pydantic import BaseModel, Field

class ClickUpWebhook(BaseModel):
    # Ограничиваем список событий согласно ТЗ
    event: Literal[
        "taskCreated", 
        "taskStatusUpdated", 
        "taskPriorityUpdated", 
        "taskDueDateUpdated", 
        "taskAssigneeUpdated", 
        "taskTagUpdated"
    ]
    task_id: str = Field(min_length=1)
    webhook_id: str = Field(min_length=1)
    id: Optional[str] = None
    team_id: Optional[str] = None