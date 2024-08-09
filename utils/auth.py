import os
from datetime import timedelta, datetime
from typing import Optional, Union
from pydantic import BaseModel
from jose import JWTError, jwt

from dotenv import load_dotenv

load_dotenv()

SECRET_KEY=os.environ["SECRET"]
TOKEN_EXPIRE_MINS = 30
ALGORITHM = "HS256"
class User(BaseModel):
    username: str

class UserInRuntime(User):
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None


def verify_password(plain_password, real_pass):
    return plain_password == real_pass

def authenticate_user(user: UserInRuntime, username: str, password: str):
    if username != user.username or password != user.password:
        return False
    return User(username=user.username)

def create_access_token(user: str):
    to_encode = {"sub": user, "exp": 0}
    expires_delta = timedelta(minutes=TOKEN_EXPIRE_MINS)
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Union[TokenData, bool]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: Optional[str] = payload.get("sub")
        if not username:
            return False
        token_data = TokenData(username=username)
    except JWTError:
        return False
    return token_data
