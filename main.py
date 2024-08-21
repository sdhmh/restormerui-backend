import os
from typing_extensions import Annotated
import uuid
import secrets
from pathlib import Path

from dotenv import load_dotenv

from fastapi import Depends, FastAPI, HTTPException, UploadFile, status, BackgroundTasks
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel, Session


from model.clean import clean
from model.models import Model

from utils.auth import Token, User, UserInRuntime, authenticate_user, create_access_token, decode_access_token
from utils.core import AppState
from utils.db import get_task, set_task_uploaded_to, update_task_status, engine
from utils.message import BadError, Error, ResponseErrors, Success
from utils.sqlite_models import Task, TaskStatus
from utils.upload import S3_BUCKET, upload, upload_to_local


origin_regex = os.getenv("CORS_ORIGIN", "http://localhost:3000")

openapi_path = "/openapi.json" if not os.getenv("ENVIRONMENT") == "PRODUCTION" else None

app = FastAPI(openapi_url=openapi_path)

app.add_middleware(CORSMiddleware, allow_origin_regex=origin_regex, allow_credentials=True, allow_headers=["*"], allow_methods=["GET", "POST"])

app.mount('/static', StaticFiles(directory='static'), name="static")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
# Init functions
def init_db():
    SQLModel.metadata.create_all(engine)

def init_state():
    with open("state.json", "w") as jf:
        state = AppState(status=TaskStatus.FINISHED, task_id=None)
        jf.write(state.model_dump_json())

def create_token(size):
    return secrets.token_hex(size)

temp_user = UserInRuntime(username=create_token(8), password=create_token(32))

@app.on_event("startup")
def startup():
    init_db()
    init_state()
    print(f"Use this token to login: {temp_user}")

MAX_FILE_SIZE = os.getenv("RESTORMER_MAX_FILE_SIZE", 250)

ALLOWED_FILE_TYPES = ["jpeg", "jpg", "png"]

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

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Couldn't validate credentials", headers={"WWW-Authenticate": "Bearer"})
    user = decode_access_token(token)
    if not user:
        raise credentials_exception
    return user

@app.get("/health", response_model=Success)
def check_health(response: Response):
    return Success(details="running")

@app.post("/token", response_model=Token)
def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    user = authenticate_user(temp_user, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Username or Password", headers={"WWW-Authenticate": "Bearer"})
    access_token = create_access_token(user.username)
    return Token(access_token=access_token, token_type="bearer")

@app.get("/progress", response_model=AppState)
def get_progress(current_user: Annotated[User, Depends(get_current_user)]):
    with open("state.json", "r") as jf:
        state = AppState.model_validate_json(jf.read())
    return state
@app.get("/link")
def get_link(task_id: int, current_user: Annotated[User, Depends(get_current_user)]):
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
async def clean_image(file: UploadFile, model: Model, background_tasks: BackgroundTasks, response: Response, current_user: Annotated[User, Depends(get_current_user)]):
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
