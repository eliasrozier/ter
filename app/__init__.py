from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.secret_key = Config.SECRET_KEY
    app.config.from_object(Config)

    db.init_app(app)

    with app.app_context():
        from . import routes
        db.create_all() # Crée la base de données au démarrage

    return app


app = create_app()
