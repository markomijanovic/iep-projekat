import os

from flask import Flask, jsonify

from pymongo.errors import PyMongoError
from redis.exceptions import RedisError

from services.director.config import Config
from services.director.extensions import (initialize_data_stores)
from services.director.extensions import jwt
from services.director.routes import (director_blueprint)

def create_app():
    app = Flask(__name__)
    app.json.sort_keys = False
    app.config.from_object(Config)

    jwt.init_app(app)
    initialize_data_stores(app)

    app.register_blueprint(director_blueprint)

    @app.get("/health")
    def health():
        try:
            mongo_client = app.extensions[
                "mongo_client"
            ]

            redis_client = app.extensions[
                "redis_client"
            ]

            mongo_client.admin.command("ping")
            redis_client.ping()

        except (PyMongoError, RedisError):
            return jsonify(
                status="error"
            ), 503

        return jsonify(
            status="ok",
            mongodb="ok",
            redis="ok",
        ), 200

    return app


app = create_app()

if __name__ == "__main__":
    port = int(
        os.getenv("PORT", "5002")
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=True,
    )