import re

from flask import Blueprint
from flask import jsonify
from flask import request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from sqlalchemy.exc import IntegrityError

from services.auth.extensions import db
from services.auth.models import User

auth_blueprint = Blueprint(
    'auth',
    __name__
)

EMAIL_PATTERN = re.compile(
    r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
)

REQUIRED_REGISTERED_FIELDS = [
    'forename',
    'surname',
    'email',
    'password',
]

LOGIN_FIELDS = (
    "email",
    "password",
)

def bad_request(message):
    return jsonify(message=message), 400

def get_json_body():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return {}

    return data

def find_invalid_required_fields(data,fields):
    for field in fields:
        value = data.get(field)

        if(
            not isinstance(value, str)
            or len(value) == 0
            or len(value) > 256
        ):
            return field

    return None

@auth_blueprint.route('/register',methods=['POST'])
def register():
    data = get_json_body()

    if data is None:
        data = {}

    invalid_field = find_invalid_required_fields(data,REQUIRED_REGISTERED_FIELDS)

    if invalid_field is not None:
        return bad_request(
            f"Field {invalid_field} is missing."
        )


    email = data['email'].lower()

    if not EMAIL_PATTERN.fullmatch(email):
        return bad_request("Invalid email.")

    password = data['password']

    if len(password) < 8:
        return bad_request(f"Invalid password.")

    existing_user = db.session.execute(
        db.select(User).where(User.email == email)
    ).scalar_one_or_none()

    if existing_user is not None:
        return bad_request(
            "Email already exists."
        )

    user = User(
        forename=data['forename'],
        surname=data['surname'],
        email=email,
        role="employee",
    )

    user.set_password(password)

    db.session.add(user)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()

        return bad_request(
            "Email already exists."
        )

    return "",200

@auth_blueprint.route('/login',methods=['POST'])
def login():
    data = get_json_body()

    invalid_field = find_invalid_required_fields(data,LOGIN_FIELDS)

    if invalid_field is not None:
        return bad_request(
            f"Field {invalid_field} is missing."
        )

    email = data['email'].lower()

    if not EMAIL_PATTERN.fullmatch(email):
        return bad_request("Invalid email.")

    user = db.session.execute(
        db.select(User).where(User.email == email)
    ).scalar_one_or_none()

    if (
            user is None
            or not user.check_password(data['password'])
    ):
        return bad_request("Invalid credentials.")

    access_token = create_access_token(
        identity=user.email,
        additional_claims=user.public_data(),
    )

    return jsonify(accessToken=access_token),200

@auth_blueprint.route('/delete',methods=['POST'])
@jwt_required()
def delete():
    email = get_jwt_identity()

    user = db.session.execute(
        db.select(User).where(
            User.email == email
        )
    ).scalar_one_or_none()

    if user is None:
        return bad_request("Unknown user.")

    db.session.delete(user)
    db.session.commit()

    return "",200
