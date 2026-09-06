import os
from flask import Flask,jsonify

from services.auth.config import Config
from services.auth.extensions import db,jwt
from services.auth.routes import auth_blueprint


#application factory pattern
def create_app():
    app = Flask(__name__)
    app.json.sort_keys = False


    app.config.from_object(Config)

    db.init_app(app)
    jwt.init_app(app)

    app.register_blueprint(auth_blueprint)


    @app.get("/health")
    def health():
        return jsonify(status="ok"),200

    return app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0",
            port=port,
            debug=True,
    )
