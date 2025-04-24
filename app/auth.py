import time
from jose import jwt, JWTError

from .config import SECRET_KEY, ALGORITHM, TOKEN_EXPIRATION_SECONDS


def create_token(filename: str) -> str:
    exp = int(time.time()) + TOKEN_EXPIRATION_SECONDS
    return jwt.encode({"file": filename, "exp": exp}, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str, filename: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("file") != filename:
            raise JWTError()
    except JWTError:
        raise
