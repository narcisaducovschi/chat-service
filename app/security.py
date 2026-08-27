from jose import jwt, JWTError
from app.config import settings

def decode_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token , settings.secret_key , algorithms=[settings.algorithm])
        return payload
    except JWTError:
        return None
        