from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager


db = SQLAlchemy()

jwt = JWTManager()


def create_app():

    app = Flask(__name__)


    app.config["JWT_SECRET_KEY"] = "CHANGE_THIS_SECRET"


    db.init_app(app)

    jwt.init_app(app)


    return app