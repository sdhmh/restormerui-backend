import os
from pathlib import Path
from typing import Tuple, Union

from boto3 import client
import botocore.exceptions



from . import message
s3 = client("s3")

S3_BUCKET = os.getenv("S3_BUCKET")
LOCAL_BUCKET = Path("static")

def upload(filename: str, file_data: bytes):
    upload_possible, success = upload_to_s3(filename, file_data)
    print(success, upload_possible)
    if not success:
        print("here")
        upload_to_local(filename, file_data)
        return "local"
    print("no i am here")
    return "s3"

def upload_to_s3(filename: str, file: bytes) -> Tuple[Union[None, message.ResponseErrors, message.Error, message.Success], bool]:
    if S3_BUCKET:
        try:
            s3_response = s3.put_object(Bucket=S3_BUCKET, Key=filename, Body=file, ACL="public-read")
        except botocore.exceptions.ClientError as err:
            return message.Error(data=err.response["Error"], reason=message.ErrorTypes.S3_ERROR), False

        if s3_response["ResponseMetadata"]["HTTPStatusCode"] == 200:
            return message.Success(data=s3_response), True
        return message.ResponseErrors.UPLOAD_TO_S3_NOT_SUCCESSFUL, False
    return None, False

def upload_to_local(filename: str, file_data: bytes):
    with open(LOCAL_BUCKET / filename, 'wb') as outfile:
        outfile.write(file_data)
