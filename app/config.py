from pydantic import BaseSettings, Field


class MailConfig(BaseSettings):
    mail_username: str = Field(..., env="MAIL_HOST_USERNAME")
    mail_password: str = Field(..., env="MAIL_HOST_PASSWORD")
    mail_port: int = Field(..., env="MAIL_PORT")
    mail_server: str = Field(..., env="MAIL_SERVER")
    mail_ssl_tls: bool = Field(..., env="MAIL_SSL_TLS")
    mail_tls: bool = Field(..., env="MAIL_TLS")
    mail_from: str = Field(..., env="MAIL_FROM")
    auth_secret: str = Field(..., env="AUTH_SECRET")
    auth_algorithm: str = Field(..., env="AUTH_ALGORITHM")
    app_host: str = Field(..., env="APP_HOST")

    class Config:
        env_file = ".env"


def get_mail_config():
    return MailConfig()
