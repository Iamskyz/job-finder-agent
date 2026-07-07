"""
Job Finder AI Agent - Backend Application
Flask + MongoDB + JWT Auth + APScheduler
"""

import os
from datetime import timedelta

from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from pymongo import MongoClient

load_dotenv()

# Flask App
app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "change-this-secret")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=7)

# Mail Config
app.config["MAIL_SERVER"] = os.getenv("MAIL_SERVER", "smtp.gmail.com")
app.config["MAIL_PORT"] = int(os.getenv("MAIL_PORT", 587))
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")
app.config["MAIL_DEFAULT_SENDER"] = os.getenv("MAIL_DEFAULT_SENDER")

# CORS - support multiple frontend origins
_frontend_urls = [u.strip() for u in os.getenv("FRONTEND_URL", "http://localhost:5173").split(",") if u.strip()]
CORS(app, origins=_frontend_urls, supports_credentials=True)

jwt = JWTManager(app)
mail = Mail(app)

# MongoDB
try:
    mongo_client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017/jobfinder"))
    mongo_client.admin.command("ping")
    db = mongo_client.get_default_database()
    print("[OK] MongoDB connected successfully!")
except Exception as e:
    print(f"[ERROR] MongoDB connection failed: {e}")
    db = None

# Scheduler — disabled on Vercel (serverless has no persistent process)
# On Render/Railway/local it runs normally
IS_VERCEL = os.getenv("VERCEL") == "1"

scheduler = None
if not IS_VERCEL:
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        scheduler = BackgroundScheduler()
        scheduler.start()
        if db is not None:
            from services.scheduler_service import restore_all_scheduled_jobs
            restore_all_scheduled_jobs(scheduler, db)
        print("[OK] Scheduler started")
    except Exception as e:
        print(f"[WARN] Scheduler failed to start: {e}")
        scheduler = None
else:
    print("[INFO] Vercel environment — scheduler disabled (use a cron service for auto-search)")

# Register Routes
from routes.auth import auth_bp
from routes.jobs import jobs_bp
from routes.user import user_bp

app.register_blueprint(auth_bp, url_prefix="/api/auth")
app.register_blueprint(jobs_bp, url_prefix="/api/jobs")
app.register_blueprint(user_bp, url_prefix="/api/user")


@app.route("/api/health")
def health():
    db_status = "connected" if db is not None else "disconnected"
    scheduler_status = "disabled (serverless)" if IS_VERCEL else ("running" if scheduler else "stopped")
    return {"status": "ok", "message": "Job Finder API is running", "database": db_status, "scheduler": scheduler_status}


if __name__ == "__main__":
    app.run(debug=True, port=5000)
