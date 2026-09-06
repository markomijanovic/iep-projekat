from services.auth.app import create_app
from services.auth.extensions import db
from services.auth.models import User

DIRECTOR_DATA = {
    "forename": "Scrooge",
    "surname": "McDuck",
    "email": "onlymoney@gmail.com",
    "password": "evenmoremoney",
}

def initialize_database():
    app = create_app()

    with app.app_context():
        db.create_all()

        director=db.session.execute(
            db.select(User).where(
                User.email==DIRECTOR_DATA['email']
            )
        ).scalar_one_or_none()

        if director is not None:
            print("Director already exists.")
            return

        director = User(
            forename=DIRECTOR_DATA['forename'],
            surname=DIRECTOR_DATA['surname'],
            email=DIRECTOR_DATA['email'],
            role="director"
        )

        director.set_password(DIRECTOR_DATA['password'])

        db.session.add(director)
        db.session.commit()

        print("Database initialized.")
        print("Initial director created.")

if __name__ == "__main__":
    initialize_database()