# Job Finder AI Agent

AI-powered job search platform. Set your preferences, search 10 platforms at once, and receive categorized job alerts via email — automatically.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React + Tailwind CSS + Vite |
| Backend | Flask + Flask-JWT + APScheduler |
| Database | MongoDB Atlas |
| Email | Gmail SMTP (Flask-Mail) |
| AI Matching | TF-IDF + Cosine Similarity (scikit-learn) |
| Deployment | Vercel (frontend + backend) |

## Features

- JWT authentication (signup/login)
- Job preferences — roles, skills, locations, experience, job types
- 10 platforms — LinkedIn, Indeed, Naukri, Internshala, CutShort, InstaHyre, Google Jobs, RemoteOK, FreshersWorld
- AI ranking with TF-IDF cosine similarity
- Categorized HTML email alerts (by job type → role → company type)
- Auto-search with configurable interval (1–72 hours)
- Search history (manual + auto)
- Profile — separate notification email from login email
- India-only filter (WFO + Remote India)

## Project Structure

```
job-finder-agent/
├── backend/
│   ├── api/
│   │   └── index.py          # Vercel serverless entry point
│   ├── models/user.py
│   ├── routes/
│   │   ├── auth.py
│   │   ├── jobs.py
│   │   └── user.py
│   ├── services/
│   │   ├── job_scraper.py
│   │   ├── job_matcher.py
│   │   ├── email_service.py
│   │   └── scheduler_service.py
│   ├── app.py
│   ├── requirements.txt
│   ├── vercel.json
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── context/AuthContext.jsx
│   │   └── pages/
│   │       ├── Landing.jsx
│   │       ├── Login.jsx
│   │       ├── Signup.jsx
│   │       └── Dashboard.jsx
│   ├── vercel.json
│   ├── .env.example
│   └── package.json
├── .gitignore
└── README.md
```

## Local Setup

### 1. MongoDB Atlas

1. Go to https://cloud.mongodb.com → create free cluster
2. Create a database user
3. Whitelist `0.0.0.0/0` in Network Access
4. Copy the connection string

### 2. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Mac/Linux
pip install -r requirements.txt

cp .env.example .env          # then fill in your values
python app.py
```

### 3. Frontend

```bash
cd frontend
npm install
# create frontend/.env with:
# VITE_API_URL=http://localhost:5000/api
npm run dev
```

### 4. Gmail App Password

1. Enable 2-Step Verification at https://myaccount.google.com/security
2. Generate App Password at https://myaccount.google.com/apppasswords
3. Use the 16-char password as `MAIL_PASSWORD` in `.env`

---

## Deployment on Vercel

> Both frontend and backend deploy to Vercel separately.

### Step 1 — Deploy Backend

1. Push this repo to GitHub
2. Go to https://vercel.com → **Add New Project**
3. Import your GitHub repo
4. Set **Root Directory** to `backend`
5. Framework: **Other**
6. Add these Environment Variables:

| Variable | Value |
|----------|-------|
| `MONGO_URI` | Your MongoDB Atlas URI |
| `JWT_SECRET_KEY` | Any random secret string |
| `MAIL_SERVER` | `smtp.gmail.com` |
| `MAIL_PORT` | `587` |
| `MAIL_USERNAME` | Your Gmail address |
| `MAIL_PASSWORD` | Your Gmail App Password |
| `MAIL_DEFAULT_SENDER` | Your Gmail address |
| `FRONTEND_URL` | Your Vercel frontend URL (add after frontend deploy) |
| `VERCEL` | `1` |
| `CRON_SECRET` | Any random secret string (secures the cron endpoint) |

7. Deploy → copy the backend URL (e.g. `https://job-finder-backend.vercel.app`)

### Step 2 — Deploy Frontend

1. Go to https://vercel.com → **Add New Project** again
2. Import the same repo
3. Set **Root Directory** to `frontend`
4. Framework: **Vite**
5. Add Environment Variable:

| Variable | Value |
|----------|-------|
| `VITE_API_URL` | `https://your-backend.vercel.app/api` |

6. Deploy

### Step 3 — Update CORS

Go back to your **backend** Vercel project → Settings → Environment Variables → update `FRONTEND_URL` to your frontend Vercel URL → **Redeploy**.

> **Auto-Search on Vercel:** The backend `vercel.json` includes a cron job that calls `GET /api/cron/run-searches` every hour. Vercel checks MongoDB for users whose `next_run` time has passed and only runs their search — so a user with a 12h interval only gets searched every 12h. Add `CRON_SECRET` to your Vercel backend env vars to secure the endpoint.

---

## API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/auth/signup` | No | Create account |
| POST | `/api/auth/login` | No | Login |
| GET | `/api/auth/me` | Yes | Get current user |
| GET | `/api/user/profile` | Yes | Get profile |
| PUT | `/api/user/profile` | Yes | Update name / notification email |
| PUT | `/api/user/preferences` | Yes | Update job preferences |
| GET | `/api/user/preferences` | Yes | Get preferences |
| PUT | `/api/user/auto-search` | Yes | Enable/disable auto-search |
| GET | `/api/user/auto-search` | Yes | Get auto-search status |
| POST | `/api/jobs/search` | Yes | Search jobs + send email |
| GET | `/api/jobs/search-stream` | Yes | Search with SSE progress |
| GET | `/api/jobs/history` | Yes | Get search history |
| GET | `/api/health` | No | Health check |

## Environment Variables Reference

### Backend (`backend/.env`)

```env
MONGO_URI=mongodb+srv://<user>:<pass>@cluster.mongodb.net/jobfinder
JWT_SECRET_KEY=your-random-secret
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=you@gmail.com
MAIL_PASSWORD=your-16-char-app-password
MAIL_DEFAULT_SENDER=you@gmail.com
FRONTEND_URL=http://localhost:5173
CRON_SECRET=your-random-cron-secret
# VERCEL=1   ← set this in Vercel dashboard, not locally
```

### Frontend (`frontend/.env`)

```env
VITE_API_URL=http://localhost:5000/api
```
