from typing import Optional
from sqlmodel import Session, select, create_engine

from utils.core import AppState

from .sqlite_models import Task, TaskStatus

engine = create_engine("sqlite:///./db.sqlite")

def get_task(task_id) -> Optional[Task]:
    with Session(engine) as session:
        query = select(Task).where(Task.id == task_id)
        task = session.exec(query).first()
    return task

def update_task_status(task_id: int, status: TaskStatus):
    with open('state.json', "w") as jsonfile:
        data = AppState(task_id=task_id, status=status)
        jsonfile.write(data.model_dump_json())

def set_task_uploaded_to(task_id, place: str):
    with Session(engine) as session:
        query = select(Task).where(Task.id == task_id)
        task = session.exec(query).first()
        if task:
            task.uploaded_to = place
            session.commit()
