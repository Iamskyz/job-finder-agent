"""Authentication Routes - Signup, Login, Logout"""

import bcrypt
from bson import ObjectId
from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    get_jwt_identity,
    jwt_required,
)
from marshmallow import Schema, fields, validate

auth_bp = Blueprint("auth", __name__)


class SignupSchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=2, max=50))
    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=validate.Length(min=6, max=100))


class LoginSchema(Schema):
    email = fields.Email(required=True)
    password = fields.Str(required=True)


@auth_bp.route("/signup", methods=["POST"])
def signup():
    """Register a new user."""
    from app import db
    from models.user import create_user_document

    schema = SignupSchema()
    errors = schema.validate(request.json)
    if errors:
        return jsonify({"error": "Validation failed", "details": errors}), 400

    data = request.json
    name = data["name"].strip()
    email = data["email"].strip().lower()
    password = data["password"]

    # Check if user exists
    if db.users.find_one({"email": email}):
        return jsonify({"error": "Email already registered"}), 409

    # Hash password
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    # Create user
    user_doc = create_user_document(name, email, password_hash)
    result = db.users.insert_one(user_doc)

    # Generate token
    token = create_access_token(identity=str(result.inserted_id))

    return jsonify({
        "message": "Account created successfully",
        "token": token,
        "user": {"id": str(result.inserted_id), "name": name, "email": email},
    }), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    """Login user and return JWT token."""
    from app import db

    schema = LoginSchema()
    errors = schema.validate(request.json)
    if errors:
        return jsonify({"error": "Validation failed", "details": errors}), 400

    data = request.json
    email = data["email"].strip().lower()
    password = data["password"]

    # Find user
    user = db.users.find_one({"email": email})
    if not user:
        return jsonify({"error": "Invalid email or password"}), 401

    # Verify password
    if not bcrypt.checkpw(password.encode("utf-8"), user["password"].encode("utf-8")):
        return jsonify({"error": "Invalid email or password"}), 401

    # Generate token
    token = create_access_token(identity=str(user["_id"]))

    return jsonify({
        "message": "Login successful",
        "token": token,
        "user": {
            "id": str(user["_id"]),
            "name": user["name"],
            "email": user["email"],
            "notification_email": user.get("notification_email", user["email"]),
            "job_preferences": user.get("job_preferences", {}),
            "auto_search": user.get("auto_search", {}),
        },
    }), 200


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def get_current_user():
    """Get current authenticated user."""
    from app import db

    user_id = get_jwt_identity()
    user = db.users.find_one({"_id": ObjectId(user_id)})

    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "user": {
            "id": str(user["_id"]),
            "name": user["name"],
            "email": user["email"],
            "notification_email": user.get("notification_email", user["email"]),
            "job_preferences": user.get("job_preferences", {}),
            "auto_search": user.get("auto_search", {}),
        }
    }), 200
