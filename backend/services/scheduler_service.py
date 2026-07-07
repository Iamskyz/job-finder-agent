"""
Scheduler Service
Manages auto-search jobs for users using APScheduler.
"""

import logging
from datetime import datetime, timedelta

from bson import ObjectId

logger = logging.getLogger(__name__)


def run_auto_search(user_id: str):
    """Execute auto-search for a specific user."""
    from app import db, app
    from services.job_scraper import scrape_all_jobs
    from services.job_matcher import rank_jobs, remove_duplicates
    from services.email_service import send_job_alert_email

    try:
        with app.app_context():
            user = db.users.find_one({"_id": ObjectId(user_id)})
            if not user:
                logger.error(f"Auto-search: User {user_id} not found")
                return

            if not user.get("auto_search", {}).get("enabled", False):
                logger.info(f"Auto-search disabled for user {user_id}")
                return

            preferences = user.get("job_preferences", {})
            if not preferences.get("roles"):
                logger.warning(f"Auto-search: No roles set for user {user_id}")
                return

            logger.info(f"Running auto-search for {user['email']}...")

            all_jobs = scrape_all_jobs(preferences)
            if not all_jobs:
                logger.info(f"Auto-search: No jobs found for {user['email']}")
                return

            unique_jobs = remove_duplicates(all_jobs)

            from routes.jobs import filter_india_jobs
            india_jobs = filter_india_jobs(unique_jobs, preferences)

            ranked_jobs = rank_jobs(india_jobs, preferences) if india_jobs else []
            if not ranked_jobs:
                logger.info(f"Auto-search: No India-based jobs found for {user['email']}")
                return

            send_job_alert_email(user.get("notification_email", user["email"]), user["name"], ranked_jobs)

            next_run = datetime.utcnow() + timedelta(
                hours=user.get("auto_search", {}).get("interval_hours", 24)
            )
            db.users.update_one(
                {"_id": ObjectId(user_id)},
                {
                    "$set": {
                        "auto_search.last_run": datetime.utcnow(),
                        "auto_search.next_run": next_run,
                    },
                    "$push": {
                        "search_history": {
                            "$each": [{"timestamp": datetime.utcnow(), "jobs_found": len(ranked_jobs), "type": "auto"}],
                            "$slice": -20,
                        }
                    },
                },
            )
            logger.info(f"Auto-search complete for {user['email']}: {len(ranked_jobs)} jobs sent")
    except Exception as e:
        logger.error(f"Auto-search failed for user {user_id}: {e}")


def schedule_user_job(scheduler, user_id: str, user: dict, interval_hours: float, next_run_time=None):
    """Schedule or reschedule auto-search for a user."""
    if scheduler is None:
        logger.info("Scheduler not available (serverless environment)")
        return
    job_id = f"auto_search_{user_id}"

    try:
        scheduler.remove_job(job_id)
    except Exception:
        pass

    scheduler.add_job(
        run_auto_search,
        "interval",
        hours=interval_hours,
        id=job_id,
        args=[user_id],
        replace_existing=True,
        next_run_time=next_run_time,
    )
    logger.info(f"Scheduled auto-search for {user.get('email', user_id)} every 2min (TEST), next run: {next_run_time}")


def remove_user_job(scheduler, user_id: str):
    """Remove auto-search job for a user."""
    if scheduler is None:
        return
    job_id = f"auto_search_{user_id}"
    try:
        scheduler.remove_job(job_id)
        logger.info(f"Removed auto-search job for {user_id}")
    except Exception:
        pass


def restore_all_scheduled_jobs(scheduler, db):
    """Restore all auto-search jobs on server startup, preserving original next_run time."""
    from datetime import timezone
    try:
        users = db.users.find({"auto_search.enabled": True})
        count = 0
        for user in users:
            user_id = str(user["_id"])
            auto_search = user.get("auto_search", {})
            interval = auto_search.get("interval_hours", 12)

            # Preserve stored next_run; if it's in the past, run immediately
            stored_next_run = auto_search.get("next_run")
            now = datetime.utcnow().replace(tzinfo=timezone.utc)
            if stored_next_run:
                if stored_next_run.tzinfo is None:
                    stored_next_run = stored_next_run.replace(tzinfo=timezone.utc)
                next_run_time = stored_next_run if stored_next_run > now else now
            else:
                next_run_time = now

            schedule_user_job(scheduler, user_id, user, interval, next_run_time=next_run_time)
            count += 1
        logger.info(f"Restored {count} auto-search jobs")
    except Exception as e:
        logger.error(f"Failed to restore scheduled jobs: {e}")
