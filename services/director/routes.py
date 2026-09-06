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