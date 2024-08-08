import os
import uuid
import secrets
from pathlib import Path

from dotenv import load_dotenv

from fastapi import FastAPI, UploadFile, status, BackgroundTasks
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from sqlmodel import SQLModel, Session
from fastapi.responses import JSONResponse

from model.clean import clean
from model.models import Model

from utils.db import get_task, set_task_uploaded_to, update_task_status, engine
from utils.message import BadError, Error, ResponseErrors, Success
from utils.sqlite_models import Task, TaskStatus
from utils.upload import S3_BUCKET, upload, upload_to_local




load_dotenv()

openapi_path = "/openapi.json" if not os.getenv("ENVIRONMENT") == "PRODUCTION" else None

app = FastAPI(openapi_url=openapi_path)

app.mount('/static', StaticFiles(directory='static'), name="static")

def init_db():
    SQLModel.metadata.create_all(engine)

def init_state():
    with open("state.json", "w") as jf:
        state = AppState(status=TaskStatus.FINISHED, task_id=None)
        jf.write(state.model_dump_json())

def create_token():
    return secrets.token_hex(16)

TOKEN = create_token()

@app.on_event("startup")
def startup():
    init_db()
    init_state()
    print(TOKEN)


if os.getenv("RESTORMER_MAX_FILE_SIZE"):
    MAX_FILE_SIZE = int(os.environ["RESTORMER_MAX_FILE_SIZE"])
else:
    MAX_FILE_SIZE = 250 # in kbs

ALLOWED_FILE_TYPES = ["jpeg", "jpg", "png"]


@app.get('/task')
def task_get(task_id):
    task = get_task(task_id)
    return task
def clean_image_concurrently(task_id: int, model: str) -> None:
    update_task_status(task_id, TaskStatus.PROCESSING)
    task = get_task(task_id)
    if task:
        input_ = Path("static") / task.source

        output_image = clean(input_, model).read()

        update_task_status(task_id, TaskStatus.UPLOADING)
        with open(input_, 'rb') as image:
            input_image = image.read()
        input_uploaded_to = upload(task.source, input_image)
        output_uploaded_to = upload(task.output, output_image)

        set_task_uploaded_to(task_id, input_uploaded_to)
        update_task_status(task_id, TaskStatus.FINISHED)


@app.get("/", response_model=Success)
def read_root(response: Response):
    return Success(details="running")

@app.get("/progress", response_model=AppState)
def get_progress():
    with open("state.json", "r") as jf:
        state = AppState.model_validate_json(jf.read())
    return state
@app.get("/link")
def get_link(task_id):
    task = get_task(task_id)
    link = {"source_link": "", "output_link": ""} # to avoid None
    if task:
        if task.uploaded_to == "s3":
            link["source_link"] = f"https://{S3_BUCKET}.s3.amazonaws.com/{task.source}"
            link["output_link"] = f"https://{S3_BUCKET}.s3.amazonaws.com/{task.output}"
        elif task.uploaded_to == "local":
            link["source_link"] = f"/static/{task.source}"
            link["output_link"] = f"/static/{task.output}"

    return link

@app.post("/clean", status_code=status.HTTP_202_ACCEPTED, response_model=Success, responses={status.HTTP_400_BAD_REQUEST: {"model": BadError }, status.HTTP_406_NOT_ACCEPTABLE: {"model": Error}})
async def clean_image(file: UploadFile, model: Model, background_tasks: BackgroundTasks, response: Response):
    with open('state.json', 'r') as jf:
        state = AppState.model_validate_json(jf.read())
        if state.status != "finished":
            return JSONResponse(ResponseErrors.ALREADY_PROCESSING.value, status.HTTP_406_NOT_ACCEPTABLE)

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

        task = Task(source=source, output=destination)

        with Session(engine) as session:
            session.add(task)
            session.commit()
            session.refresh(task)
            task_id = task.id

        if task_id:
            update_task_status(task_id, TaskStatus.PENDING)
            data = await file.read()
            upload_to_local(source, data)

            background_tasks.add_task(clean_image_concurrently, task_id, model.value)

        return JSONResponse(Success(details="Pending", data={"taskId": task_id}).model_dump(), status.HTTP_202_ACCEPTED)

    return JSONResponse(ResponseErrors.INVALID_CONTENT.value, status.HTTP_400_BAD_REQUEST)
