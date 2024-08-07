from io import BytesIO
import os

from boto3 import client
import botocore.exceptions

from utils import sqlite_models

from . import message
s3 = client("s3")

S3_BUCKET = os.getenv("S3_BUCKET")

def upload(task: sqlite_models.Task, file: BytesIO):
    success, upload_possible = upload_to_s3(task, file)
    if not upload_possible or not success:
        with open(task.output, "wb") as output_file:
            output_file.write(file.read())
        return task.output

def upload_to_s3(task: sqlite_models.Task, file: BytesIO):
    if S3_BUCKET:
        try:
            s3_response = s3.put_object(Bucket=S3_BUCKET, Key=task.task_name, Body=file.read(), ExtraArgs={"ACL": "public-read"})
        except botocore.exceptions.ClientError as err:
            return message.Error(data=err.response["Error"], reason=message.ErrorTypes.S3_ERROR), False

        if s3_response["ResponseMetadata"]["HTTPStatusCode"] == 200:
            return message.Success(data=s3_response), True
        return message.ResponseErrors.UPLOAD_TO_S3_NOT_SUCCESSFUL, False
    return None, False
