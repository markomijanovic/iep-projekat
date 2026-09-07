from functools import wraps

from flask import jsonify
from flask_jwt_extended import get_jwt
from flask_jwt_extended import (verify_jwt_in_request)

def role_required(required_role):
    def decorator(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()

            claims = get_jwt()

            if claims.get("role") != required_role:
                return jsonify(
                    msg=(
                        "Missing "
                        "Authorization Header"
                    )
                ), 401

            return function(*args, **kwargs)
        return wrapper
    return decorator
