import json

from flask import Blueprint,current_app,jsonify

from services.common.auth import role_required

director_blueprint = Blueprint("director",__name__)

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