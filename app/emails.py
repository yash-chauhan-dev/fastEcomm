from typing import List

import jwt
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema
from jinja2 import Environment, PackageLoader, select_autoescape
from pydantic import BaseModel, EmailStr

import app.config as config
import app.models as models

env = Environment(
    loader=PackageLoader("app", "templates"),
    autoescape=select_autoescape(["html", "xml"])
)

mail_conf = config.get_mail_config()

conf = ConnectionConfig(
    MAIL_USERNAME=mail_conf.mail_username,
    MAIL_PASSWORD=mail_conf.mail_password,
    MAIL_PORT=mail_conf.mail_port,
    MAIL_SERVER=mail_conf.mail_server,
    MAIL_STARTTLS=mail_conf.mail_tls,
    MAIL_SSL_TLS=mail_conf.mail_ssl_tls,
    MAIL_FROM=mail_conf.mail_from,
    USE_CREDENTIALS=True
)


class EmailSchema(BaseModel):
    email: List[EmailStr]


async def send_email(email: EmailSchema, instance: models.User):
    token_data = {
        "id": instance.id,
        "username": instance.username
    }

    token = jwt.encode(token_data, key=mail_conf.auth_secret,
                       algorithm=mail_conf.auth_algorithm)

    template = env.get_template("email.html")
    html = template.render(
        {
            "app_host": mail_conf.app_host,
            "token": token
        }
    )

    message = MessageSchema(
        subject="EasyShop Account Verification Email",
        recipients=email.email,
        body=html,
        subtype="html"
    )

    fm = FastMail(conf)
    await fm.send_message(message=message)
