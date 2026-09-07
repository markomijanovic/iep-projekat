import json

from flask_jwt_extended import JWTManager
from pymongo import MongoClient
from redis import Redis
from web3 import Web3

jwt = JWTManager()

def initialize_data_stores(app):
    mongo_client = MongoClient(
        app.config["MONGO_URI"],
        serverSelectionTimeoutMS=2000,
    )

    mongo_database = mongo_client[
        app.config["MONGO_DATABASE"]
    ]

    redis_client = Redis.from_url(
        app.config["REDIS_URI"],
        decode_responses=True,
        socket_connect_timeout=2,
    )

    blockchain_client = Web3(
        Web3.HTTPProvider(
            app.config["BLOCKCHAIN_URL"]
        )
    )

    with open(
        app.config["CONTRACT_ABI_PATH"],
        "r",
        encoding="utf-8",
    ) as file:
        contract_abi = json.load(file)

    with open(
        app.config["CONTRACT_BYTECODE_PATH"],
        "r",
        encoding="utf-8",
    ) as file:
        contract_bytecode = file.read().strip()

    if not contract_bytecode.startswith("0x"):
        contract_bytecode = (
            f"0x{contract_bytecode}"
        )

    contract_factory = (
        blockchain_client.eth.contract(
            abi=contract_abi,
            bytecode=contract_bytecode,
        )
    )

    app.extensions["mongo_client"] = (
        mongo_client
    )

    app.extensions["mongo_database"] = (
        mongo_database
    )

    app.extensions["redis_client"] = (
        redis_client
    )

    app.extensions["blockchain_client"] = (
        blockchain_client
    )

    app.extensions["contract_abi"] = (
        contract_abi
    )

    app.extensions["contract_factory"] = (
        contract_factory
    )