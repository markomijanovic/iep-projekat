import os
import json
import time

from datetime import datetime
from datetime import timezone
from pathlib import Path

from bson import ObjectId
from dotenv import load_dotenv
from pymongo import MongoClient
from redis import Redis
from web3 import Web3


PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")

ONGOING = 0
APPROVED = 1
REJECTED = 2
VETOED = 3

def load_contract_abi():
    default_path = (
        PROJECT_ROOT /
        "blockchain" /
        "build" /
        "InvestmentVoting.abi"
    )

    abi_path = Path(
        os.getenv(
            "CONTRACT_ABI_PATH",
            str(default_path)
        )
    )

    with abi_path.open(
        "r",
        encoding="utf-8"
    ) as f:
        return json.load(f)

def create_clients():
    mongo_client = MongoClient(
        os.environ["MONGO_URI"],
        serverSelectionTimeoutMS=2000,
    )

    mongo_database = mongo_client[
        os.getenv(
            "MONGO_DATABASE",
            "investment-fund"
        )
    ]

    mongo_database["assets"].create_index(
        "order_uuid",
        unique=True,
        sparse=True,
    )

    redis_client = Redis.from_url(
        os.environ["REDIS_URI"],
        decode_responses=True,
        socket_connect_timeout=2,
    )

    blockchain_client = Web3(
        Web3.HTTPProvider(
            os.getenv(
                "BLOCKCHAIN_URL",
                "http://localhost:8545"
            )
        )
    )

    return (
        mongo_database,
        redis_client,
        blockchain_client,
    )

def apply_approved_order(
        order_uuid,
        order,
        mongo_database
):
    assets_collection = mongo_database["assets"]

    current_time = datetime.now(timezone.utc)

    if order["order_type"] == "BUY":
        assets_collection.update_one(
            {
                "order_uuid": order_uuid,
            },
            {
                "$setOnInsert": {
                    "name": order["name"],
                    "categories": order["categories"],
                    "buying_price": order["buying_price"],
                    "buying_date": current_time,
                    "info": order["info"],
                    "order_uuid": order_uuid,
                }
            },
            upsert=True,
        )

        return
    if order["order_type"] == "SELL":
        assets_collection.update_one(
            {
                "_id": ObjectId(
                    order["id"]
                ),
                "last_sell_order_uuid": {
                    "$ne": order_uuid
                },
            },
            {
                "$set": {
                    "selling_price" : order["selling_price"],
                    "selling_date" : current_time,
                    "last_sell_order_uuid" : order_uuid,
                },

            }
        )

        return

    raise ValueError("Unknown order type.")

def remove_finished_order(
        redis_client,
        order_uuid,
):
    pipeline = redis_client.pipeline()

    pipeline.hdel(
        "orders",
        order_uuid
    )

    pipeline.hdel(
        "contracts",
        order_uuid
    )

    pipeline.execute()


def check_contract(
        mongo_database,
        redis_client,
        blockchain_client,
        contract_abi,
):
    contracts = redis_client.hgetall(
        "contracts"
    )

    for order_uuid, contract_address in contracts.items():

        stored_order = redis_client.hget(
            "orders",
            order_uuid
        )

        if stored_order is None:
            redis_client.hdel(
                "contracts",
                order_uuid
            )
            continue

        contract = (
            blockchain_client.eth.contract(
                address=Web3.to_checksum_address(
                    contract_address,
                ),
                abi=contract_abi
            )
        )

        status = (
            contract.functions
            .status()
            .call()
        )

        if status == ONGOING:
            continue

        order = json.loads(stored_order)

        if status == APPROVED:
            apply_approved_order(
                order_uuid,
                order,
                mongo_database,
            )

        if status in (APPROVED, REJECTED, VETOED):
            remove_finished_order(
                redis_client,
                order_uuid,
            )

            print(
                f"Processed order {order_uuid}, "
                f"contract status {status}."
            )

def main():
    mongo_database, redis_client, blockchain_client = create_clients()

    if not blockchain_client.is_connected():
        raise RuntimeError(
            "Blockchain is not available."
        )

    contract_abi = load_contract_abi()

    run_once = (
        os.getenv(
            "CHECKER_RUN_ONCE",
            "false",
        ).lower() == "true"
    )

    interval_seconds = float(
        os.getenv(
            "CHECKER_INTERVAL_SECONDS",
            "2",
        )
    )

    run_duration_seconds = float(
        os.getenv(
            "CHECKER_RUN_DURATION_SECONDS",
            "0",
        )
    )

    if run_once:
        check_contract(
            mongo_database,
            redis_client,
            blockchain_client,
            contract_abi,
        )
        return

    deadline = None

    if run_duration_seconds > 0:
        deadline = (
            time.monotonic()
            + run_duration_seconds
        )

    while True:
        try:
            check_contract(
                mongo_database,
                redis_client,
                blockchain_client,
                contract_abi,
            )
        except Exception as e:
            print(
                f"Checker error: {e}",
                flush=True,
            )

        if (
            deadline is not None
            and time.monotonic() >= deadline
        ):
            return

        time.sleep(interval_seconds)


if __name__ == "__main__":
    main()
