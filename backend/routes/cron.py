"""Cron Route - Called by Vercel Cron every hour to run due auto-searches. Also has debug email test route."""

import os
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request

cron_bp = Blueprint("cron", __name__)


@cron_bp.route("/run-searches", methods=["GET"])
def run_scheduled_searches():
    """
    Called by Vercel Cron every hour.
    Checks MongoDB for users whose next_run time has passed and runs their search.
    Secured by CRON_SECRET header.
    """
    # Vercel sends Authorization: Bearer <CRON_SECRET> automatically
    secret = os.getenv("CRON_SECRET", "")
    if secret:
        auth = request.headers.get("authorization", "")
        if auth != f"Bearer {secret}":
            return jsonify({"error": "Unauthorized"}), 401

    from app import db
    from services.scheduler_service import run_auto_search

    if db is None:
        return jsonify({"error": "Database unavailable"}), 503

    now = datetime.now(timezone.utc)

    # Find all users with auto-search enabled whose next_run has passed
    due_users = list(db.users.find({
        "auto_search.enabled": True,
        "auto_search.next_run": {"$lte": now},
        "job_preferences.roles": {"$exists": True, "$ne": []},
    }))

    results = []
    for user in due_users:
        user_id = str(user["_id"])
        try:
            run_auto_search(user_id)
            results.append({"user": user["email"], "status": "ok"})
        except Exception as e:
            results.append({"user": user["email"], "status": "error", "detail": str(e)})

    return jsonify({
        "ran_at": now.isoformat(),
        "users_processed": len(due_users),
        "results": results,
    }), 200


@cron_bp.route("/test-email", methods=["GET"])
def test_email():
    """Debug route — sends a test email to verify Gmail config is working."""
    secret = os.getenv("CRON_SECRET", "")
    if secret:
        auth = request.headers.get("authorization", "")
        if auth != f"Bearer {secret}":
            return jsonify({"error": "Unauthorized"}), 401

    to_email = request.args.get("email")
    if not to_email:
        return jsonify({"error": "Pass ?email=your@email.com"}), 400

    try:
        from app import mail
        from flask_mail import Message
        msg = Message(
            subject="Job Finder AI — Test Email",
            recipients=[to_email],
            body="If you received this, email sending is working correctly!",
        )
        mail.send(msg)
        return jsonify({"status": "ok", "message": f"Test email sent to {to_email}"}), 200
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)}), 500
