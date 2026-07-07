"""Jobs Routes - Search with progress, Results, History"""

import json
import time
from bson import ObjectId
from flask import Blueprint, Response, jsonify, request, stream_with_context
from flask_jwt_extended import get_jwt_identity, jwt_required

from services.job_scraper import (
    scrape_linkedin, scrape_indeed, scrape_naukri, scrape_naukri_walkin,
    scrape_internshala, scrape_cutshort, scrape_instahyre,
    scrape_google_jobs, scrape_remoteok, scrape_freshersworld, Job,
    classify_company_type, is_relevant_job
)
from services.job_matcher import rank_jobs, remove_duplicates
from services.email_service import send_job_alert_email

jobs_bp = Blueprint("jobs", __name__)


def filter_india_jobs(jobs: list, preferences: dict) -> list:
    """Filter jobs to only include India-based WFO jobs and Remote jobs from India."""
    india_keywords = [
        "india", "ahmedabad", "gandhinagar", "gujarat", "bangalore", "mumbai",
        "delhi", "pune", "hyderabad", "chennai", "kolkata", "noida", "gurgaon",
        "jaipur", "chandigarh", "indore", "surat", "vadodara", "rajkot",
    ]
    user_locations = [loc.lower() for loc in preferences.get("locations", [])]

    filtered = []
    for job in jobs:
        loc_lower = job.location.lower()

        # Remote jobs - keep if India-based or no foreign country mentioned
        if job.job_type == "Remote":
            foreign_countries = ["usa", "us only", "uk", "canada", "australia", "germany", "singapore", "dubai", "uae", "europe", "americas"]
            if any(country in loc_lower for country in foreign_countries):
                continue
            # Keep: India mentioned, generic "remote", or no specific foreign location
            filtered.append(job)
            continue

        # WFO/Walk-in jobs - only keep if in user's preferred locations
        if any(loc in loc_lower for loc in user_locations):
            filtered.append(job)
        elif any(kw in loc_lower for kw in india_keywords[:3]):  # ahmedabad, gandhinagar, gujarat
            filtered.append(job)

    return filtered


@jobs_bp.route("/search", methods=["POST"])
@jwt_required()
def search_jobs():
    """Search jobs with progress updates via SSE."""
    from app import db

    user_id = get_jwt_identity()
    user = db.users.find_one({"_id": ObjectId(user_id)})

    if not user:
        return jsonify({"error": "User not found"}), 404

    preferences = user.get("job_preferences", {})
    if not preferences.get("roles"):
        return jsonify({"error": "Please set your job preferences first (roles are required)"}), 400

    roles = preferences.get("roles", [])
    locations = preferences.get("locations", [])
    job_types = preferences.get("job_types", [])
    wants_remote = "remote" in [l.lower() for l in locations] or "Remote" in job_types

    try:
        all_jobs = []

        # Scrape from each platform
        platforms = [
            ("LinkedIn", lambda: scrape_linkedin(roles[:5], locations)),
            ("Indeed", lambda: scrape_indeed(roles[:5], locations)),
            ("Naukri", lambda: scrape_naukri(roles[:5], locations)),
            ("Naukri Walk-in", lambda: scrape_naukri_walkin(locations)),
            ("Internshala", lambda: scrape_internshala(roles, locations)),
            ("CutShort", lambda: scrape_cutshort(roles)),
            ("InstaHyre", lambda: scrape_instahyre(roles, locations)),
            ("Google Jobs", lambda: scrape_google_jobs(roles, locations)),
            ("FreshersWorld", lambda: scrape_freshersworld(roles, locations)),
        ]

        if wants_remote:
            platforms.append(("RemoteOK", lambda: scrape_remoteok(roles)))

        for name, scraper in platforms:
            try:
                jobs = scraper()
                all_jobs.extend(jobs)
            except Exception:
                pass

        if not all_jobs:
            return jsonify({
                "message": "No jobs found. Try broadening your search.",
                "jobs_found": 0,
                "jobs": [],
            }), 200

        # Remove duplicates
        unique_jobs = remove_duplicates(all_jobs)

        # Filter to India only
        india_jobs = filter_india_jobs(unique_jobs, preferences)

        # Filter out irrelevant jobs
        relevant_jobs = [j for j in india_jobs if is_relevant_job(j, preferences)]

        # Filter out remote jobs if user didn't select Remote
        if not wants_remote:
            relevant_jobs = [j for j in relevant_jobs if j.job_type != "Remote"]

        # Rank jobs
        ranked_jobs = rank_jobs(relevant_jobs, preferences) if relevant_jobs else []

        # Classify company types
        for j in ranked_jobs:
            if not j.company_type:
                j.company_type = classify_company_type(j.company)

        # Convert to dict
        jobs_data = [
            {
                "title": j.title,
                "company": j.company,
                "location": j.location,
                "url": j.url,
                "source": j.source,
                "experience": j.experience,
                "job_type": j.job_type,
                "salary": j.salary,
                "posted_date": j.posted_date,
                "company_type": j.company_type,
            }
            for j in ranked_jobs
        ]

        # Send email
        email_sent = send_job_alert_email(user.get("notification_email", user["email"]), user["name"], ranked_jobs)

        # Save to history
        from datetime import datetime
        db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$push": {
                "search_history": {
                    "$each": [{
                        "timestamp": datetime.utcnow(),
                        "jobs_found": len(ranked_jobs),
                        "type": "manual",
                    }],
                    "$slice": -20,
                }
            }},
        )

        return jsonify({
            "message": f"Found {len(ranked_jobs)} jobs! {'Email sent.' if email_sent else 'Email failed.'}",
            "jobs_found": len(ranked_jobs),
            "email_sent": email_sent,
            "jobs": jobs_data,
        }), 200

    except Exception as e:
        return jsonify({"error": f"Search failed: {str(e)}"}), 500


@jobs_bp.route("/search-stream", methods=["GET"])
@jwt_required()
def search_jobs_stream():
    """Search jobs with real-time progress via Server-Sent Events."""
    from app import db

    user_id = get_jwt_identity()
    user = db.users.find_one({"_id": ObjectId(user_id)})

    if not user:
        return jsonify({"error": "User not found"}), 404

    preferences = user.get("job_preferences", {})
    if not preferences.get("roles"):
        return jsonify({"error": "Please set your job preferences first"}), 400

    roles = preferences.get("roles", [])
    locations = preferences.get("locations", [])
    job_types = preferences.get("job_types", [])
    wants_remote = "remote" in [l.lower() for l in locations] or "Remote" in job_types

    def generate():
        all_jobs = []
        platforms = [
            ("LinkedIn", lambda: scrape_linkedin(roles[:5], locations)),
            ("Indeed", lambda: scrape_indeed(roles[:5], locations)),
            ("Naukri", lambda: scrape_naukri(roles[:5], locations)),
            ("Naukri Walk-in", lambda: scrape_naukri_walkin(locations)),
            ("Internshala", lambda: scrape_internshala(roles, locations)),
            ("CutShort", lambda: scrape_cutshort(roles)),
            ("InstaHyre", lambda: scrape_instahyre(roles, locations)),
            ("Google Jobs", lambda: scrape_google_jobs(roles, locations)),
            ("FreshersWorld", lambda: scrape_freshersworld(roles, locations)),
        ]

        if wants_remote:
            platforms.append(("RemoteOK", lambda: scrape_remoteok(roles)))

        total = len(platforms)

        for i, (name, scraper) in enumerate(platforms):
            progress = int(((i) / (total + 2)) * 100)
            yield f"data: {json.dumps({'type': 'progress', 'platform': name, 'progress': progress, 'step': i+1, 'total_steps': total+2, 'message': f'Searching {name}...'})}\n\n"

            try:
                jobs = scraper()
                all_jobs.extend(jobs)
                yield f"data: {json.dumps({'type': 'platform_done', 'platform': name, 'found': len(jobs), 'total_so_far': len(all_jobs)})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type': 'platform_error', 'platform': name, 'error': str(e)})}\n\n"

        # Processing step
        yield f"data: {json.dumps({'type': 'progress', 'progress': 85, 'step': total+1, 'total_steps': total+2, 'message': 'AI matching & filtering India jobs...'})}\n\n"

        unique_jobs = remove_duplicates(all_jobs)
        india_jobs = filter_india_jobs(unique_jobs, preferences)

        # Filter out irrelevant jobs
        relevant_jobs = [j for j in india_jobs if is_relevant_job(j, preferences)]

        # Filter out remote jobs if user didn't select Remote
        if not wants_remote:
            relevant_jobs = [j for j in relevant_jobs if j.job_type != "Remote"]

        ranked_jobs = rank_jobs(relevant_jobs, preferences) if relevant_jobs else []

        # Email step
        yield f"data: {json.dumps({'type': 'progress', 'progress': 95, 'step': total+2, 'total_steps': total+2, 'message': f'Sending {len(ranked_jobs)} jobs to your email...'})}\n\n"

        email_sent = send_job_alert_email(user.get("notification_email", user["email"]), user["name"], ranked_jobs)

        # Save history
        from datetime import datetime
        db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$push": {
                "search_history": {
                    "$each": [{
                        "timestamp": datetime.utcnow(),
                        "jobs_found": len(ranked_jobs),
                        "type": "manual",
                    }],
                    "$slice": -20,
                }
            }},
        )

        # Final result - classify companies
        for j in ranked_jobs:
            if not j.company_type:
                j.company_type = classify_company_type(j.company)

        jobs_data = [
            {
                "title": j.title,
                "company": j.company,
                "location": j.location,
                "url": j.url,
                "source": j.source,
                "experience": j.experience,
                "job_type": j.job_type,
                "salary": j.salary,
                "company_type": j.company_type,
            }
            for j in ranked_jobs
        ]

        yield f"data: {json.dumps({'type': 'complete', 'progress': 100, 'jobs_found': len(ranked_jobs), 'email_sent': email_sent, 'jobs': jobs_data, 'message': f'Done! Found {len(ranked_jobs)} India-based jobs.'})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@jobs_bp.route("/history", methods=["GET"])
@jwt_required()
def get_search_history():
    """Get user's search history."""
    from app import db

    user_id = get_jwt_identity()
    user = db.users.find_one({"_id": ObjectId(user_id)})

    if not user:
        return jsonify({"error": "User not found"}), 404

    history = user.get("search_history", [])
    for item in history:
        if "timestamp" in item:
            item["timestamp"] = item["timestamp"].isoformat()

    return jsonify({"history": history}), 200


@jobs_bp.route("/platforms", methods=["GET"])
def get_platforms():
    """Get list of supported job platforms."""
    platforms = [
        {"id": "linkedin", "name": "LinkedIn", "priority": "high"},
        {"id": "indeed", "name": "Indeed", "priority": "high"},
        {"id": "naukri", "name": "Naukri", "priority": "high"},
        {"id": "internshala", "name": "Internshala", "priority": "high"},
        {"id": "cutshort", "name": "CutShort", "priority": "medium"},
        {"id": "instahyre", "name": "InstaHyre", "priority": "medium"},
        {"id": "google_jobs", "name": "Google Jobs", "priority": "high"},
        {"id": "glassdoor", "name": "Glassdoor", "priority": "medium"},
        {"id": "remoteok", "name": "RemoteOK", "priority": "medium"},
        {"id": "freshersworld", "name": "FreshersWorld", "priority": "medium"},
    ]
    return jsonify({"platforms": platforms}), 200
