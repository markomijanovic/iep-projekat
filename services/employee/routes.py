import re

import json

from uuid import uuid4
from bson import ObjectId

from datetime import datetime
from datetime import timezone

from flask import Blueprint
from flask import current_app
from flask import jsonify
from flask import request

from services.common.auth import role_required



employee_blueprint = Blueprint(
    "employee",
    __name__,
)

COMPARISON_OPERATORS = {
    "eq": "$eq",
    "ne": "$ne",
    "gt": "$gt",
    "gte": "$gte",
    "lt": "$lt",
    "lte": "$lte",
    "in": "$in",
    "nin": "$nin",
}

BUY_ORDER_FIELDS = (
    "name",
    "categories",
    "buying_price",
    "info",
)

SELL_ORDER_FIELDS = (
    "id",
    "selling_price",
)

def find_missing_fields(data, fields):
    for field in fields:
        if field not in data:
            return field

        value = data.get(field)
        if value is None:
            return field

        if(isinstance(value, str) and len(value) == 0):
            return field

    return None

def is_positive_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and value > 0
    )

def save_order(order):
    redis_client = current_app.extensions["redis_client"]

    redis_client.hset(
        "orders",
        order["uuid"],
        json.dumps(order)
    )


def get_json_body():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return {}

    return data


def parse_iso_datetime(value):
    if not isinstance(value, str):
        raise ValueError

    normalized_value = value.replace(
        "Z",
        "+00:00",
    )

    parsed_value = datetime.fromisoformat(
        normalized_value
    )

    if parsed_value.tzinfo is None:
        parsed_value = parsed_value.replace(
            tzinfo=timezone.utc
        )

    return parsed_value.astimezone(
        timezone.utc
    )


def format_iso_datetime(value):
    if value.tzinfo is None:
        value = value.replace(
            tzinfo=timezone.utc
        )

    return (
        value
        .astimezone(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def serialize_asset(asset):
    result = {
        "id": str(asset["_id"]),
        "name": asset["name"],
        "categories": asset["categories"],
        "buying_date": format_iso_datetime(
            asset["buying_date"]
        ),
        "buying_price": asset["buying_price"],
        "info": asset.get("info", {}),
    }

    if "selling_date" in asset:
        result["selling_date"] = (
            format_iso_datetime(
                asset["selling_date"]
            )
        )

    if "selling_price" in asset:
        result["selling_price"] = (
            asset["selling_price"]
        )

    return result


@employee_blueprint.post("/search")
@role_required("employee")
def search():
    data = get_json_body()

    conditions = []

    if "name" in data:
        if not isinstance(data["name"], str):
            return jsonify(
                message="Invalid name."
            ), 400

        conditions.append({
            "name": {
                "$regex": re.escape(data["name"])
            }
        })

    if "category" in data:
        if not isinstance(
            data["category"],
            str,
        ):
            return jsonify(
                message="Invalid category."
            ), 400

        conditions.append({
            "categories": data["category"]
        })

    if "buying_date" in data:
        try:
            buying_date = parse_iso_datetime(
                data["buying_date"]
            )
        except ValueError:
            return jsonify(
                message="Invalid buying date."
            ), 400

        conditions.append({
            "buying_date": {
                "$gt": buying_date
            }
        })

    if "selling_date" in data:
        try:
            selling_date = parse_iso_datetime(
                data["selling_date"]
            )
        except ValueError:
            return jsonify(
                message="Invalid selling date."
            ), 400

        conditions.append({
            "selling_date": {
                "$lt": selling_date
            }
        })

    info_filters = data.get(
        "info_filters",
        [],
    )

    if not isinstance(info_filters, list):
        return jsonify(
            message="Invalid info filter."
        ), 400

    for info_filter in info_filters:
        if not isinstance(info_filter, dict):
            return jsonify(
                message="Invalid info filter."
            ), 400

        field = info_filter.get("field")
        operator = info_filter.get("operator")

        if (
            not isinstance(field, str)
            or operator not in COMPARISON_OPERATORS
            or "value" not in info_filter
        ):
            return jsonify(
                message="Invalid info filter."
            ), 400

        mongo_operator = (
            COMPARISON_OPERATORS[operator]
        )

        conditions.append({
            f"info.{field}": {
                mongo_operator: (
                    info_filter["value"]
                )
            }
        })

    query = {}

    if conditions:
        query = {
            "$and": conditions
        }

    mongo_database = current_app.extensions[
        "mongo_database"
    ]

    assets_collection = mongo_database[
        "assets"
    ]

    assets = assets_collection.find(query)

    return jsonify(
        assets=[
            serialize_asset(asset)
            for asset in assets
        ]
    ), 200

@employee_blueprint.post("/create_buy_order")
@role_required("employee")
def create_buy_order():
    data = get_json_body()

    missing_field = find_missing_fields(data,BUY_ORDER_FIELDS)

    if missing_field is not None:
        return jsonify(
            message=(
                f"Field {missing_field} is missing."
            )
        ),400

    name = data["name"]
    categories = data["categories"]
    buying_price = data["buying_price"]
    info = data["info"]

    if( not isinstance(name, str) or len(name) >256 ):
        return jsonify(
            message="Field name is missing."
        ),400
    if( not isinstance(categories, list) or len(categories) ==0 ):
        return jsonify(
            message="Categories list is empty."
        ),400
    if not all(isinstance(category, str) and 0<len(category) <=256 for category in categories):
        return jsonify(
            message="Categories list is empty."
        ),400
    if not is_positive_number(buying_price):
        return jsonify(
            message="Invalid buying price."
        ),400
    if not isinstance(info, dict):
        return jsonify(
            message="Field info is missing."
        ),400

    order = {
        "uuid": str(uuid4()),
        "order_type":"BUY",
        "name":name,
        "categories": categories,
        "info": info,
        "buying_price": buying_price,
    }

    save_order(order)

    return "",200

@employee_blueprint.post("/create_sell_order")
@role_required("employee")
def create_sell_order():
    data = get_json_body()

    missing_field = find_missing_fields(data,SELL_ORDER_FIELDS)

    if missing_field is not None:
        return jsonify(
            message=(
                f"Field {missing_field} is missing."
            )
        ),400

    asset_id = data["id"]
    selling_price = data["selling_price"]

    if( not isinstance(asset_id, str) or not  ObjectId.is_valid(asset_id) ):
        return jsonify(
            message="Invalid id."
        ),400

    mongo_database = current_app.extensions[
        "mongo_database"
    ]
    assets_collection = mongo_database[
        "assets"
    ]

    assets = assets_collection.find_one({"_id": ObjectId(asset_id)})

    if assets is None:
        return jsonify(
            message="Invalid id."
        ),400
    if not is_positive_number(selling_price):
        return jsonify(
            message="Invalid selling price."
        ),400

    order = {
        "uuid": str(uuid4()),
        "order_type":"SELL",
        "id":asset_id,
        "selling_price":selling_price,
    }

    save_order(order)

    return "",200
