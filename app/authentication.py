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
        print(payload)
        print(user)

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user
