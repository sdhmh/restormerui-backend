from enum import Enum
from typing import List, Dict, Optional, Union
from pydantic import BaseModel

class ErrorTypes(str, Enum):
    BIG_FILE_SIZE = "BIG_FILE_SIZE"
    UPLOAD_TO_S3_NOT_SUCCESSFUL = "UPLOAD_TO_S3_NOT_SUCCESSFUL"
    S3_ERROR = "S3_ERROR"
    ALREADY_PROCESSING = "ALREADY_PROCESSING"

class BadErrorTypes(str, Enum):
    INVALID_CONTENT = "INVALID_CONTENT"

class Message(BaseModel):
    type: str
    details: Optional[str] = None
    data: Optional[Union[Dict, List[Dict]]] = {}

class Info(Message):
    type: str = "info"

class Success(Message):
    type: str = "success"

class Error(Message):
    reason: ErrorTypes
    type: str = "error"
    details: Optional[str] = "An Error Occured!"

class BadError(Message):
    reason: BadErrorTypes
    type: str = "error"
    details: Optional[str] = "A Bad Error Occured!"

class ResponseErrors(dict, Enum):
    ALREADY_PROCESSING = Error(reason=ErrorTypes.ALREADY_PROCESSING).model_dump()
    BIG_FILE_SIZE = Error(reason=ErrorTypes.BIG_FILE_SIZE).model_dump()
    UPLOAD_TO_S3_NOT_SUCCESSFUL = Error(reason=ErrorTypes.UPLOAD_TO_S3_NOT_SUCCESSFUL).model_dump()
    S3_ERROR = Error(reason=ErrorTypes.S3_ERROR).model_dump()
    INVALID_CONTENT = BadError(reason=BadErrorTypes.INVALID_CONTENT).model_dump()
