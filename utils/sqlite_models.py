from enum import Enum
from typing import Optional, Union
from pathlib import Path
from sqlmodel import Field, SQLModel

class TaskStatus(str, Enum):
    SCHEDULED = "scheduled"
    PROCESSING = "processing"
    UPLOADING = "uploading"
    FINISHED = "finished"

class Task(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    status: TaskStatus
    source: Union[Path, str]
    output: Union[Path, str]
