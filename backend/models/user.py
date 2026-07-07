"""User Model - MongoDB Schema"""

from datetime import datetime


def create_user_document(name, email, password_hash):
    """Create a new user document for MongoDB."""
    return {
        "name": name,
        "email": email,
        "notification_email": email,
        "password": password_hash,
        "created_at": datetime.utcnow(),
        "job_preferences": {
            "roles": [],
            "skills": [],
            "experience": "0-1 years",
            "locations": [],
            "job_types": ["Work from Office", "Remote", "Walk-in", "Hybrid"],
        },
        "auto_search": {
            "enabled": False,
            "interval_hours": 24,
            "last_run": None,
            "job_id": None,
        },
        "search_history": [],
    }


def create_search_result_document(user_id, jobs, search_type="manual"):
    """Create a search result document."""
    return {
        "user_id": user_id,
        "search_type": search_type,
        "jobs_found": len(jobs),
        "timestamp": datetime.utcnow(),
    }
