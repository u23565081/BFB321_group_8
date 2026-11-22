import os

from dotenv import load_dotenv


load_dotenv()


class BaseConfig:
    SECRET_KEY = os.getenv("SECRET_KEY", "development-only-change-me")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    JSON_SORT_KEYS = False
    ITEMS_PER_PAGE = 10
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


class MySQLDatabaseURL:
    """Validate on access so importing the pytest configuration needs no MySQL."""

    def __get__(self, instance, owner):
        value = os.getenv("DATABASE_URL", "").strip()
        if not value.startswith("mysql+pymysql://"):
            raise RuntimeError(
                "Copy .env.example to .env and set DATABASE_URL to your MySQL database"
            )
        return value


class DevelopmentConfig(BaseConfig):
    DEBUG = os.getenv("FLASK_DEBUG", "0").strip().lower() in {"1", "true", "yes", "on"}
    SQLALCHEMY_DATABASE_URI = MySQLDatabaseURL()


class TestingConfig(BaseConfig):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


class ProductionConfig(BaseConfig):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = MySQLDatabaseURL()

    @classmethod
    def validate(cls):
        # Accessing the descriptor validates the required MySQL URL.
        _ = cls.SQLALCHEMY_DATABASE_URI
        if cls.SECRET_KEY == "development-only-change-me":
            raise RuntimeError("SECRET_KEY must be changed in production.")


CONFIGS = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}

