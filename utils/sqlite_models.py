from enum import Enum
from typing import Optional
from botocore.utils import S3EndpointSetter
from pydantic.main import BaseModel
from sqlmodel import Field, SQLModel
from starlette.types import StatefulLifespan

class TaskStatus(str, Enum):
    SCHEDULED = "scheduled"
    PROCESSING = "processing"
    UPLOADING = "uploading"
    FINISHED = "finished"

class Task(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    status: TaskStatus
    source: str
    output: str
