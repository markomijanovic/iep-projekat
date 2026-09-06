import os

from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")

class Config:
    JWT_SECRET_KEY = os.environ[
        "JWT_SECRET_KEY"
    ]

    MONGO_URI = os.getenv(
        "MONGO_URI"
    )

    MONGO_DATABASE = os.getenv(
        "MONGO_DATABASE",
        "investment_fund"
    )

    REDIS_URI = os.getenv(
        "REDIS_URI"
    )
