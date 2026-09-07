import os

from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")

class Config:

    BLOCKCHAIN_URL = os.getenv("BLOCKCHAIN_URL","http://127.0.0.1:8545")

    CONTRACT_ABI_PATH = os.getenv(
        "CONTRACT_ABI_PATH",
        str(
            PROJECT_ROOT
            / "blockchain"
            / "build"
            / "InvestmentVoting.abi"
        )
    )
    CONTRACT_BYTECODE_PATH = os.getenv(
        "CONTRACT_BYTECODE_PATH",
        str(
            PROJECT_ROOT
            / "blockchain"
            / "build"
            / "InvestmentVoting.bin"
        ),
    )

    JWT_SECRET_KEY = os.environ[
        "JWT_SECRET_KEY"
    ]

    MONGO_URI = os.environ[
        "MONGO_URI"
    ]

    MONGO_DATABASE = os.getenv(
        "MONGO_DATABASE",
        "investment_fund",
    )

    REDIS_URI = os.environ[
        "REDIS_URI"
    ]