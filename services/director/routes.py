import json
import uuid as uuid_library

from flask import (
    Blueprint,
    current_app,
    jsonify,
    request,
)
from web3 import Web3


from services.common.auth import role_required

director_blueprint = Blueprint("director",__name__)

def bad_request(message):
    return jsonify(
        message=message,
    ),400

def get_json_body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return {}
    return data

def is_valid_uuid(value):
    if not isinstance(value, str):
        return False
    try:
        uuid_library.UUID(value)
        return True
    except ValueError:
        return False

def create_contract_transaction(contract,function_name):
    return {
        "to": contract.address,
        "data": contract.encode_abi(function_name),
    }

def serialize_pending_order(order):
    if order["order_type"] == "BUY":
        return {
            "uuid": order["uuid"],
            "order_type": order["order_type"],
            "name": order["name"],
            "categories": order["categories"],
            "info": order["info"],
            "buying_price": order["buying_price"],
        }

    return {
        "uuid": order["uuid"],
        "order_type": order["order_type"],
        "id": order["id"],
        "selling_price": order["selling_price"],
    }

@director_blueprint.route("/pending_orders",methods=["GET"])
@role_required("director")
def pending_orders():
    redis_client = current_app.extensions["redis_client"]

    stored_orders = redis_client.hvals("orders")

    orders = [
        serialize_pending_order(
            json.loads(stored_order)
        )
        for stored_order in stored_orders
    ]

    return jsonify(orders=orders),200

@director_blueprint.get("/report")
@role_required("director")
def report():
    mongo_database = current_app.extensions[
        "mongo_database"
    ]

    assets_collection = mongo_database[
        "assets"
    ]

    pipeline = [
        {
            "$unwind": "$categories"
        },
        {
            "$group": {
                "_id": "$categories",
                "spent": {
                    "$sum": "$buying_price"
                },
                "earned": {
                    "$sum": {
                        "$cond": [
                            {
                                "$and": [
                                    {
                                        "$ne": [
                                            {
                                                "$type": (
                                                    "$selling_price"
                                                )
                                            },
                                            "missing",
                                        ]
                                    },
                                    {
                                        "$ne": [
                                            {
                                                "$type": (
                                                    "$selling_date"
                                                )
                                            },
                                            "missing",
                                        ]
                                    },
                                ]
                            },
                            "$selling_price",
                            0,
                        ]
                    }
                },
            }
        },
        {
            "$project": {
                "_id": 0,
                "category": "$_id",
                "spent": 1,
                "earned": 1,
            }
        },
        {
            "$sort": {
                "earned": -1,
                "spent": 1,
                "category": 1,
            }
        },
    ]

    statistics = list(
        assets_collection.aggregate(
            pipeline
        )
    )

    return jsonify(
        statistics=statistics
    ), 200

@director_blueprint.post("/decision")
@role_required("director")
def decision():
    data = get_json_body()
    if ("uuid" not in data or data["uuid"] == ""):
        return bad_request(
            "Field uuid is missing."
        )

    order_uuid = data["uuid"]

    redis_client = current_app.extensions["redis_client"]

    if (
            not is_valid_uuid(order_uuid)
            or not redis_client.hexists(
        "orders",
        order_uuid,
    )
            or redis_client.hexists(
        "contracts",
        order_uuid,
    )
    ):
        return bad_request(
            "Invalid uuid."
        )

    if (
        "voters" not in data
        or not isinstance(
            data["voters"],
            list,
        )
        or len(data["voters"]) ==0
    ):
        return bad_request(
            "Field voters is missing."
        )

    voters = data["voters"]

    for voter in voters:
        if(
            not isinstance(voter, str)
            or not Web3.is_address(voter)
            or int(voter,16) == 0
        ):
            return bad_request(
                "Invalid voter address."
            )

    checksum_voters = [
        Web3.to_checksum_address(voter)
        for voter in voters
    ]
    if len(set(checksum_voters)) != len(
            checksum_voters
    ):
        return bad_request(
            "Invalid voter address."
        )

    if len(checksum_voters) % 2 == 0:
        return bad_request(
            "Even number of voters."
        )

    blockchain_client = current_app.extensions["blockchain_client"]

    if not blockchain_client.is_connected():
        raise RuntimeError(
            "Blockchain is not available."
        )

    blockchain_accounts = blockchain_client.eth.accounts

    if(len(blockchain_accounts) == 0):
        raise RuntimeError(
            "No blockchain accounts available."
        )
    director_account = blockchain_accounts[0]

    contract_factory= current_app.extensions["contract_factory"]

    deployment_hash = (
        contract_factory.constructor(
            checksum_voters
        ).transact({
            "from": director_account
        })
    )

    deployment_receipt = (
        blockchain_client.eth
        .wait_for_transaction_receipt(
            deployment_hash
        )
    )

    if (
            deployment_receipt.status != 1
            or deployment_receipt.contractAddress
            is None
    ):
        raise RuntimeError(
            "Contract deployment failed."
        )

    contract = (
        blockchain_client.eth.contract(
            address=(
                deployment_receipt
                .contractAddress
            ),
            abi=current_app.extensions[
                "contract_abi"
            ],
        )
    )

    redis_client.hset(
        "contracts",
        order_uuid,
        contract.address
    )

    approve_transaction = (
        create_contract_transaction(
            contract,
            "voteFor",
        )
    )

    reject_transaction = (
        create_contract_transaction(
            contract,
            "voteAgainst",
        )
    )

    veto_transaction = (
        create_contract_transaction(
            contract,
            "veto",
        )
    )

    return jsonify(
        approve_transaction=(
            approve_transaction
        ),
        reject_transaction=(
            reject_transaction
        ),
        veto_transaction=(
            veto_transaction
        ),
    ), 200