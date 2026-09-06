import os

from flask_jwt_extended import JWTManager
from pymongo import MongoClient, mongo_client
from redis import Redis

jwt = JWTManager()

def initialize_data_stores(app):
    mongo_client = MongoClient(
        app.config["MONGO_URI"],
        serverSelectionTimeoutMS=2000,
    )

    mongo_database = mongo_client[app.config["MONGO_DATABASE"]]

    redis_client = Redis.from_url(
        app.config["REDIS_URI"],
        decode_responses=True,
        socket_connect_timeout=2,
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