from werkzeug.security import generate_password_hash, check_password_hash

from services.auth.extensions import db

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    forename = db.Column(db.String(256), nullable=False)
    surname = db.Column(db.String(256), nullable=False)
    email = db.Column(db.String(256), nullable=False,unique=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role=db.Column(db.String(16), nullable=False,default='employee')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def public_data(self):
        return {
            "forename": self.forename,
            "surname": self.surname,
            "email": self.email,
            "role": self.role
        }