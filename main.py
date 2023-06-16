from typing import List, Optional, Type

from fastapi import FastAPI
from tortoise import BaseDBAsyncClient
from tortoise.contrib.fastapi import register_tortoise
# signals
from tortoise.signals import post_save

import authentication
import models

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


@app.get("/")
def index():
    return {
        "message": "Hello World"
    }


register_tortoise(
    app,
    db_url="sqlite://database.sqlite3",
    modules={"models": ["models"]},
    generate_schemas=True,
    add_exception_handlers=True
)
