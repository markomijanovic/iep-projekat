import os

from flask import Flask,jsonify
from pymongo.errors import PyMongoError
from redis.exceptions import RedisError

from services.employee.config import Config
from services.employee.extensions import (initialize_data_stores)
from services.employee.extensions import jwt

from services.employee.routes import (employee_blueprint)

def create_app():
    app = Flask(__name__)

    app.config.from_object(Config)

    jwt.init_app(app)
    initialize_data_stores(app)

    app.register_blueprint(employee_blueprint)

    @app.get("/health")
    def health():
        try:
            mongo_client = app.extensions["mongo_client"]

            redis_client = app.extensions["redis_client"]

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
    port = int(os.getenv("PORT", 5001))
    app.run(
        host="0.0.0.0",
        port=port,
        debug=True,
    )