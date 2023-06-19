import secrets
from datetime import datetime
from typing import List, Optional, Type

import jwt
from fastapi import (Depends, FastAPI, File, HTTPException, Request,
                     UploadFile, status)
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from PIL import Image
from tortoise import BaseDBAsyncClient
from tortoise.contrib.fastapi import register_tortoise
from tortoise.signals import post_save

import app.authentication as authentication
import app.config as config
import app.emails as emails
import app.models as models

configuration = config.get_mail_config()

app = FastAPI()

oauth2_schema = OAuth2PasswordBearer(tokenUrl='token')

app.mount("/app/static", StaticFiles(directory="app/static"), name="static")


@app.post('/token')
async def generate_token(request_form: OAuth2PasswordRequestForm = Depends()):
    token = await authentication.token_generator(
        request_form.username, request_form.password)
    return {"access_token": token, "token_type": "bearer"}


async def get_current_user(token: str = Depends(oauth2_schema)):
    try:
        payload = jwt.decode(token, key=configuration.auth_secret,
                             algorithms=configuration.auth_algorithm)
        user = await models.User.get(id=payload.get("id"))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW_Authentication": "Bearer"}
        )
    return await user


@app.post("/user/me")
async def user_login(user: models.user_pydanticIn = Depends(get_current_user)):
    business = await models.Business.get(owner=user)
    logo = business.logo
    logo_path = configuration.app_host + "app/static/images" + logo

    return {
        "status": "ok",
        "data": {
            "username": user.username,
            "email": user.email,
            "verified": user.is_verified,
            "joined_date": user.join_date.strftime("%b %d %Y"),
            "logo": logo_path
        }
    }


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


@app.post("/upload/profile")
async def create_upload_file(
        file: UploadFile = File(...),
        user: models.user_pydantic = Depends(get_current_user)):
    FILEPATH = "app/static/images/"
    filename = file.filename
    # test.png -> ["test", "png"]
    extension = filename.split(".")[1]

    if extension not in ["png", "jpg"]:
        return {"status": "error", "detail": "File extension not allowed"}

    token_name = secrets.token_hex(10) + "." + extension
    generate_name = FILEPATH + token_name
    file_content = await file.read()

    with open(generate_name, "wb") as file_pointer:
        file_pointer.write(file_content)

    # PILLOW
    img = Image.open(generate_name)
    img = img.resize(size=(200, 200))
    img.save(generate_name)

    file.close()

    business = await models.Business.get(owner=user)
    owner = await business.owner

    if owner == user:
        business.logo = token_name
        await business.save()

    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated to perform this action",
            headers={"WWW-Authenticate": "Bearer"}
        )

    file_url = "localhost:8000/" + generate_name

    return {
        "status": "ok",
        "filename": file_url
    }


@app.post("/upload/product/{id}")
async def create_upload_product_file(
        id: int,
        file: UploadFile = File(...),
        user: models.user_pydantic = Depends(get_current_user)):
    FILEPATH = "app/static/images/"
    filename = file.filename
    # test.png -> ["test", "png"]
    extension = filename.split(".")[1]

    if extension not in ["png", "jpg"]:
        return {"status": "error", "detail": "File extension not allowed"}

    token_name = secrets.token_hex(10) + "." + extension
    generate_name = FILEPATH + token_name
    file_content = await file.read()

    with open(generate_name, "wb") as file_pointer:
        file_pointer.write(file_content)

    # PILLOW
    img = Image.open(generate_name)
    img = img.resize(size=(200, 200))
    img.save(generate_name)

    file.close()

    product = await models.Product.get(id=id)
    business = await product.business
    owner = await business.owner

    if owner == user:
        product.product_image = token_name
        await product.save()

    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated to perform this action",
            headers={"WWW-Authenticate": "Bearer"}
        )

    file_url = "localhost:8000/" + generate_name

    return {
        "status": "ok",
        "filename": file_url
    }

# CRUD Functionality


@app.post("/product")
async def add_new_product(product: models.product_pydanticIn,
                          user: models.user_pydantic = Depends(
                              get_current_user)
                          ):
    product = product.dict(exclude_unset=True)

    # to avoid division error by zero
    if product["original_price"] > 0:
        product["percentage_discount"] = (
            (product["original_price"] - product["new_price"]) /
            product["original_price"]
        ) * 100
        product_obj = await models.Product.create(**product, business=user)
        product_obj = (
            await models.product_pydantic.from_tortoise_orm(product_obj)
        )

        return {
            "status": "ok",
            "data": product_obj
        }
    else:
        return {
            "status": "error"
        }


@app.get("/products")
async def get_products():
    response = (
        await models.product_pydantic.from_queryset(models.Product.all())
    )
    return {
        "status": "ok",
        "data": response
    }


@app.get("/product/{id}")
async def get_product(id: int):
    product = await models.Product.get(id=id)
    business = await product.business
    owner = await business.owner
    response = (
        await models.product_pydantic.from_queryset_single(
            models.Product.get(id=id)
        )
    )

    return {
        "status": "ok",
        "data": {
            "product_details": response,
            "business_details": {
                "name": business.business_name,
                "city": business.city,
                "region": business.region,
                "description": business.business_description,
                "logo": business.logo,
                "owner_id": owner.id,
                "email": owner.email,
                "join_date": owner.join_date.strftime("%b %d %Y")
            }
        }
    }


@app.delete("product/{id}")
async def delete_product(id: int,
                         user: models.user_pydantic = Depends(get_current_user)
                         ):
    product = await models.Product.get(id=id)
    business = await product.business
    owner = await business.owner

    if user == owner:
        product.delete()

    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated to perform this action",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return {
        "status": "ok"
    }


@app.put("/product/{id}")
async def update_product(id: int,
                         update_info: models.product_pydanticIn,
                         user: models.user_pydantic = Depends(get_current_user)
                         ):
    product = await models.Product.get(id=id)
    business = await product.business
    owner = await business.owner

    update_info = update_info.dict(exclude_unset=True)
    update_info["date+published"] = datetime.utcnow()

    if user == owner and update_info["original_price"] != 0:
        update_info["percentage_discount"] = (
            (update_info["original_price"] - update_info["new_price"]
             ) / update_info["original_price"]
        )*100

        product = await models.Product.update_from_dict(update_info)
        await product.save()
        response = await models.product_pydantic.from_tortoise_orm(product)
        return {
            "status": "ok",
            "data": response
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated to perform this action or \
                invalid user input",
            headers={"WWW-Authenticate": "Bearer"}
        )


@app.put("/business/{id}")
async def update_business(id: int,
                          update_business: models.business_pydanticIn,
                          user: models.user_pydantic = Depends(
                              get_current_user)
                          ):
    update_business = update_business.dict()

    business = await models.Business.get(id=id)
    business_owner = await business.owner

    if user == business_owner:
        await business.update_from_dict(update_business)
        business.save()
        response = await models.business_pydantic.from_tortoise_orm(business)
        return {
            "status": "ok", "data": response
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated to perform this action\
                  or invalid user input",
            headers={"WWW-Authenticate": "Bearer"}
        )

register_tortoise(
    app,
    db_url="sqlite://database.sqlite3",
    modules={"models": ["app.models"]},
    generate_schemas=True,
    add_exception_handlers=True
)
