# flask-api/app/routes/auth.py

from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity
)
from datetime import datetime, timedelta
import bcrypt, os, hashlib

from app import db
from app.models import User, RefreshToken

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()

    # Validate
    for field in ["username", "email", "password"]:
        if not data or not data.get(field):
            return jsonify({"error": f"'{field}' is required"}), 400

    if User.query.filter_by(username=data["username"]).first():
        return jsonify({"error": "Username already taken"}), 400
    if User.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "Email already registered"}), 400

    
    hashed = bcrypt.hashpw(data["password"].encode(), bcrypt.gensalt())

    user = User(
        username      = data["username"],
        email         = data["email"],
        password_hash = hashed.decode()
    )
    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "Account created", "user": user.to_dict()}), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    user = User.query.filter_by(username=data.get("username")).first()

    if not user or not bcrypt.checkpw(
        data.get("password", "").encode(),
        user.password_hash.encode()
    ):
        return jsonify({"error": "Invalid credentials"}), 401

    
    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))
    expires_days = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRES_DAYS", 7))
    token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()

    db.session.add(RefreshToken(
        user_id    = user.id,
        token_hash = token_hash,
        expires_at = datetime.utcnow() + timedelta(days=expires_days)
    ))
    db.session.commit()

    return jsonify({
        "access_token":  access_token,
        "refresh_token": refresh_token,
        "user":          user.to_dict()
    }), 200


@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)   
def refresh():
    """
    Exchange a refresh token for a new access token.
    This is how users stay logged in without re-entering their password.
    """
    user_id       = get_jwt_identity()
    access_token  = create_access_token(identity=user_id)
    return jsonify({"access_token": access_token}), 200


@auth_bp.route("/logout", methods=["DELETE"])
@jwt_required(refresh=True)
def logout():
    """Revoke the refresh token — user must log in again after this."""
    
    return jsonify({"message": "Logged out"}), 200