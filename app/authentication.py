import jwt
from fastapi import status
from fastapi.exceptions import HTTPException
from passlib.context import CryptContext

import app.config as config
import app.models as models

configuration = config.get_mail_config()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_hashed_password(password):
    return pwd_context.hash(password)


async def verify_token(token: str):
    try:
        payload = jwt.decode(token, key=configuration.auth_secret,
                             algorithms=configuration.auth_algorithm)
        user = await models.User.get(id=payload.get("id"))

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user


async def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


async def authenticate_user(username, password):
    user = await models.User.get(username=username)

    if user and verify_password(password, user.password):
        return user
    return False


async def token_generator(username: str, password: str):
    user = await authenticate_user(username, password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token_data = {
        "id": user.id,
        "username": user.username
    }

    token = jwt.encode(token_data, key=configuration.auth_secret,
                       algorithm=configuration.auth_algorithm)

    return token
