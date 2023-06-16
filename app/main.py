from typing import List, Optional, Type

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from tortoise import BaseDBAsyncClient
from tortoise.contrib.fastapi import register_tortoise
# signals
from tortoise.signals import post_save

import app.authentication as authentication
import app.emails as emails
import app.models as models

app = FastAPI()


@post_save(models.User)
async def create_business(
    sender: Type[models.User],
    instance: models.User,
    created: bool,
    using_db: Optional[BaseDBAsyncClient],
    update_fields: List[str]
) -> None:

    if created:
        business_obj = await models.Business.create(
            business_name=instance.username,
            owner=instance
        )
        await models.business_pydantic.from_tortoise_orm(business_obj)
        await emails.send_email(
            emails.EmailSchema(email=[instance.email]),
            instance
        )


@app.post("/registration")
async def user_registrations(user: models.user_pydanticIn):
    user_info = user.dict(exclude_unset=True)
    user_info["password"] = authentication.get_hashed_password(
        user_info["password"])
    user_obj = await models.User.create(**user_info)
    new_user = await models.user_pydantic.from_tortoise_orm(user_obj)
    return {
        "status": "ok",
        "data": f"Hello {new_user.username}, thanks for choosing services. \
            Please check your email inbox and click on the link to confirm \
                your registration."
    }

templates = Jinja2Templates(directory="app/templates")


@app.get("/verification", response_class=HTMLResponse)
async def email_verification(request: Request, token: str):
    user = await authentication.verify_token(token)
    print(user.is_verified)
    if user and not user.is_verified:
        user.is_verified = True
        await user.save()
        return templates.TemplateResponse("verification.html",
                                          {
                                              "request": request,
                                              "username": user.username
                                          })
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid token or expired token",
        headers={"WWW-Authenticate": "Bearer"}
    )

register_tortoise(
    app,
    db_url="sqlite://database.sqlite3",
    modules={"models": ["app.models"]},
    generate_schemas=True,
    add_exception_handlers=True
)
