from enum import Enum
from typing import Optional
from sqlmodel import Field, SQLModel

class TaskStatus(str, Enum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    PROCESSING = "processing"
    UPLOADING = "uploading"
    FINISHED = "finished"

class Task(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    source: str
    output: str
    uploaded_to: Optional[str] = None
