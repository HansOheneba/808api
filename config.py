import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    ENV = os.getenv("FLASK_ENV", "production")
    PORT = int(os.getenv("PORT", 5000))
    SECRET_KEY = os.getenv("SECRET_KEY", "default-secret-key")
    MYSQL_HOST = os.getenv("MYSQL_HOST")
    MYSQL_USER = os.getenv("MYSQL_USER")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
    MYSQL_DB = os.getenv("MYSQL_DB")
    # RESEND_API_KEY = os.getenv("RESEND_API_KEY")
    # RESEND_VERIFIED_DOMAIN = os.getenv("VERIFIED_DOMAIN")
    # ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
