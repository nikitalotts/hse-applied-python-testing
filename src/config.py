import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')
load_dotenv(dotenv_path=dotenv_path, encoding='utf-8')


class Settings(BaseSettings):
    DB_HOST: str = os.getenv("DB_HOST")
    DB_NAME: str = os.getenv("DB_NAME")
    DB_PASS: str = os.getenv("DB_PASS")
    DB_PORT: str = os.getenv("DB_PORT")
    DB_USER: str = os.getenv("DB_USER")
    DATABASE_URL: str = (f"postgresql+asyncpg://"
     f"{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}@{os.getenv('DB_HOST')}:"
     f"{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY")
    PASSWORD_SECRET_KEY: str = os.getenv("PASSWORD_SECRET_KEY")
    MESSAGE_BROKER_URL: str = os.getenv("MESSAGE_BROKER_URL")
    LINK_TTL_IN_DAYS: int = int(os.getenv("LINK_TTL_IN_DAYS"))
    CODE_GENERATION_ATTEMPTS: int = int(os.getenv("CODE_GENERATION_ATTEMPTS"))
    CODE_GENERATION_SECRET: str = os.getenv("CODE_GENERATION_SECRET")
    SHORT_CODE_LENGTH: int = int(os.getenv("SHORT_CODE_LENGTH"))
    SITE_IP: str = os.getenv("SITE_IP")
