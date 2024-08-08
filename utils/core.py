from typing import Optional
from pydantic import BaseModel

from utils.sqlite_models import TaskStatus

class AppState(BaseModel):
    status: TaskStatus
    task_id: Optional[int]
