# flask-api/app/__init__.py

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from datetime import timedelta

# These are created here at module level so any file can do:
# from app import db, jwt
db  = SQLAlchemy()
jwt = JWTManager()


def create_app():
    """
    App factory — builds and returns a configured Flask app.
    Called by run.py on startup, and by pytest fixtures in tests.
    """
    app = Flask(__name__)
    _load_config(app)
    _init_extensions(app)
    _register_blueprints(app)
    return app


def _load_config(app):
    """Read all config from environment variables."""
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        f"mysql+mysqldb://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
        f"@{os.getenv('DB_HOST', 'mysql')}:{os.getenv('DB_PORT', '3306')}"
        f"/{os.getenv('DB_NAME')}"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # JWT config
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY")
    app.config["JWT_ACCESS_TOKEN_EXPIRES"]  = timedelta(
        minutes=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES_MINUTES", 15))
    )
    
    app.config["REDIS_URL"] = os.getenv("REDIS_URL", "redis://redis:6379/0")


def _init_extensions(app):  #adds external extensions which is basically like connecting extensions to this main file.
    db.init_app(app)
    jwt.init_app(app)


def _register_blueprints(app):
    from app.routes.auth    import auth_bp
    from app.routes.reviews import reviews_bp
    from app.routes.history import history_bp

    app.register_blueprint(auth_bp,    url_prefix="/api/auth")
    app.register_blueprint(reviews_bp, url_prefix="/api/reviews")
    app.register_blueprint(history_bp, url_prefix="/api/history")