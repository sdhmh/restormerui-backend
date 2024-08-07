import os
from pathlib import Path
from typing import Optional
import uuid

from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import Select
from sqlalchemy.orm.util import _DeStringifyAnnotation
from sqlmodel import create_engine, SQLModel, Session, select
from starlette.responses import JSONResponse

from utils import Error, BadError, ErrorTypes, Success, Task, TaskStatus, upload, ResponseErrors
from model import clean, Model

load_dotenv()

app = FastAPI()

engine = create_engine("sqlite://")

SQLModel.metadata.create_all(engine)

if os.getenv("RESTORMER_MAX_FILE_SIZE"):
    MAX_FILE_SIZE = int(os.environ["RESTORMER_MAX_FILE_SIZE"])
else:
    MAX_FILE_SIZE = 250 # in kbs

ALLOWED_FILE_TYPES = ["jpeg", "jpg", "png"]


def get_task(task_id) -> Optional[Task]:
    with Session(engine) as session:
        query = select(Task).where(Task.id == task_id)
        task_out = session.exec(query)
        task = task_out.first()
    return task

async def clean_image_concurrently(task_id: int, file: UploadFile, model: Model):
    output_image = clean.clean_image(await file.read(), model.value)
    task = get_task(task_id)
    if task:
        upload(task, output_image)

@app.get("/", response_model=Success)
def read_root(response: Response):
    return Success(details="running")


@app.post("/clean", status_code=status.HTTP_202_ACCEPTED, response_model=Success, responses={status.HTTP_400_BAD_REQUEST: {"model": BadError }, status.HTTP_406_NOT_ACCEPTABLE: {"model": Error}})
async def clean_image(file: UploadFile, model: Model, response: Response):
    if file.size:
        if file.size > MAX_FILE_SIZE * 1024:
            return JSONResponse(ResponseErrors.BIG_FILE_SIZE.value, status.HTTP_406_NOT_ACCEPTABLE)

        if not file.content_type:
            return JSONResponse(ResponseErrors.INVALID_CONTENT.value, status.HTTP_406_NOT_ACCEPTABLE)

        ext = file.content_type.split("/")[1]

        if ext not in ALLOWED_FILE_TYPES:
            return JSONResponse(ResponseErrors.INVALID_CONTENT.value, status.HTTP_406_NOT_ACCEPTABLE)

        filename = str(uuid.uuid4())
        if file.filename:
            filepath = Path(file.filename)
            filename = f"{filepath.stem}_{uuid.uuid4()}"

        source = f"{filename}.{ext}"
        destination = f"{filename}_processed.{ext}"

        task = Task(source=source, output=destination, status=TaskStatus.SCHEDULED)

        with Session(engine) as session:
            session.add(task)
            session.commit()

        return JSONResponse(Success(details="Task Scheduled"), status.HTTP_202_ACCEPTED)
        # task.local_output = "This is test"
        # with Session(engine) as ses:
        #     query = select(sqlite_models.Task)
        #     test = ses.exec(query)
        #     print("test", test.fetchall())
        #     ses.add(task)
        #     ses.commit()
        #     query = select(sqlite_models.Task)
        #     test = ses.exec(query)
        #     print("test", test.fetchall())

        # print(task.model_dump())

    return JSONResponse(ResponseErrors.INVALID_CONTENT.value, status.HTTP_400_BAD_REQUEST)
