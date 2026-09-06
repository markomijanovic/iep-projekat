import os

from pathlib import Path
from datetime import timedelta

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")

DEFAULT_DATABASE_PATH = (
    PROJECT_ROOT
    / "instance"
    / "db.sqlite3"
)


class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{DEFAULT_DATABASE_PATH}",
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    JWT_SECRET_KEY = os.environ[
        "JWT_SECRET_KEY"
    ]

    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        hours=1
    )
