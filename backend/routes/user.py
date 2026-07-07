"""User Routes - Profile, Preferences, Auto-search settings"""

from bson import ObjectId
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from marshmallow import Schema, fields, validate

user_bp = Blueprint("user", __name__)


class ProfileUpdateSchema(Schema):
    name = fields.Str(validate=validate.Length(min=2, max=50))
    notification_email = fields.Email()


@user_bp.route("/profile", methods=["GET"])
@jwt_required()
def get_profile():
    """Get user profile."""
    from app import db
    user_id = get_jwt_identity()
    user = db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({"profile": {
        "id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"],
        "notification_email": user.get("notification_email", user["email"]),
        "created_at": user["created_at"].isoformat() if user.get("created_at") else None,
    }}), 200


@user_bp.route("/profile", methods=["PUT"])
@jwt_required()
def update_profile():
    """Update user profile (name and notification email)."""
    from app import db
    user_id = get_jwt_identity()
    schema = ProfileUpdateSchema()
    errors = schema.validate(request.json)
    if errors:
        return jsonify({"error": "Validation failed", "details": errors}), 400
    data = request.json
    updates = {}
    if "name" in data:
        updates["name"] = data["name"].strip()
    if "notification_email" in data:
        updates["notification_email"] = data["notification_email"].strip().lower()
    if not updates:
        return jsonify({"error": "No valid fields provided"}), 400
    db.users.update_one({"_id": ObjectId(user_id)}, {"$set": updates})
    return jsonify({"message": "Profile updated successfully"}), 200


@user_bp.route("/auto-search/test", methods=["POST"])
@jwt_required()
def test_auto_search():
    """Immediately trigger auto-search for the current user to test it works."""
    from app import db
    from services.scheduler_service import run_auto_search

    user_id = get_jwt_identity()
    user = db.users.find_one({"_id": ObjectId(user_id)})

    if not user:
        return jsonify({"error": "User not found"}), 404
    if not user.get("auto_search", {}).get("enabled"):
        return jsonify({"error": "Enable auto-search first"}), 400
    if not user.get("job_preferences", {}).get("roles"):
        return jsonify({"error": "Set your job preferences first"}), 400

    run_auto_search(user_id)
    return jsonify({"message": "Test run complete — check your email!"}), 200


@jwt_required()
def update_preferences():
    """Update user's job search preferences."""
    from app import db

    user_id = get_jwt_identity()
    data = request.json

    if not data:
        return jsonify({"error": "No data provided"}), 400

    # Validate fields
    allowed_fields = ["roles", "skills", "experience", "locations", "job_types"]
    preferences = {}
    for field in allowed_fields:
        if field in data:
            preferences[field] = data[field]

    if not preferences:
        return jsonify({"error": "No valid preference fields provided"}), 400

    # Update in DB
    db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {f"job_preferences.{k}": v for k, v in preferences.items()}},
    )

    return jsonify({"message": "Preferences updated successfully"}), 200


@user_bp.route("/preferences", methods=["GET"])
@jwt_required()
def get_preferences():
    """Get user's job search preferences."""
    from app import db

    user_id = get_jwt_identity()
    user = db.users.find_one({"_id": ObjectId(user_id)})

    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({"preferences": user.get("job_preferences", {})}), 200


@user_bp.route("/auto-search", methods=["PUT"])
@jwt_required()
def update_auto_search():
    """Enable/disable auto-search and set interval."""
    from app import db, scheduler
    from datetime import datetime, timedelta
    from services.scheduler_service import schedule_user_job, remove_user_job

    user_id = get_jwt_identity()
    data = request.json

    if data is None:
        return jsonify({"error": "No data provided"}), 400

    enabled = data.get("enabled", False)
    interval_hours = data.get("interval_hours", 12)

    # Only daily interval allowed
    if interval_hours != 24:
        return jsonify({"error": "Only 24 hour interval is supported"}), 400

    # Calculate next_run time
    next_run = None
    if enabled:
        next_run = datetime.utcnow() + timedelta(hours=interval_hours)

    # Update DB
    update_fields = {
        "auto_search.enabled": enabled,
        "auto_search.interval_hours": interval_hours,
    }
    if next_run:
        update_fields["auto_search.next_run"] = next_run
    else:
        update_fields["auto_search.next_run"] = None

    db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": update_fields},
    )

    # Manage scheduler
    if enabled:
        from datetime import timezone
        from app import scheduler
        user = db.users.find_one({"_id": ObjectId(user_id)})
        next_run_aware = next_run.replace(tzinfo=timezone.utc) if next_run else None
        schedule_user_job(scheduler, user_id, user, interval_hours, next_run_time=next_run_aware)
        msg = f"Auto-search enabled. Will run every {interval_hours} hours."
    else:
        from app import scheduler
        remove_user_job(scheduler, user_id)
        msg = "Auto-search disabled."

    return jsonify({"message": msg}), 200


@user_bp.route("/auto-search", methods=["GET"])
@jwt_required()
def get_auto_search():
    """Get auto-search settings with next run time."""
    from app import db, scheduler

    user_id = get_jwt_identity()
    user = db.users.find_one({"_id": ObjectId(user_id)})

    if not user:
        return jsonify({"error": "User not found"}), 404

    auto_search = user.get("auto_search", {})

    # Get next run time from scheduler first, fall back to DB
    next_run = None
    if scheduler is not None:
        job_id = f"auto_search_{user_id}"
        try:
            job = scheduler.get_job(job_id)
            if job and job.next_run_time:
                next_run = job.next_run_time.isoformat()
        except Exception:
            pass

    if not next_run and auto_search.get("next_run"):
        next_run = auto_search["next_run"].isoformat() if hasattr(auto_search["next_run"], 'isoformat') else auto_search["next_run"]

    # Build response
    response = {
        "enabled": auto_search.get("enabled", False),
        "interval_hours": auto_search.get("interval_hours", 12),
        "next_run": next_run,
        "last_run": auto_search.get("last_run").isoformat() if auto_search.get("last_run") and hasattr(auto_search.get("last_run"), 'isoformat') else auto_search.get("last_run"),
    }

    return jsonify({"auto_search": response}), 200
