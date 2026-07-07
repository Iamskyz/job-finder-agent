"""
Email Service - Premium categorized job alert emails.
Categories: Job Type (Remote/WFO/Walk-in) > Role > Company Type (Product/Service/Startup)
"""

import logging
from collections import defaultdict
from datetime import datetime

from flask_mail import Message

logger = logging.getLogger(__name__)


def get_type_color(job_type: str) -> str:
    colors = {
        "Walk-in Interview": "#e74c3c",
        "Work from Office": "#2980b9",
        "Remote": "#27ae60",
        "Hybrid": "#f39c12",
    }
    return colors.get(job_type, "#7f8c8d")


def get_company_type_badge(company_type: str) -> str:
    badges = {
        "Product": ("#8e44ad", "Product Based"),
        "Service": ("#e67e22", "Service Based"),
        "Startup": ("#1abc9c", "Startup"),
        "Unknown": ("#95a5a6", "Other"),
    }
    color, label = badges.get(company_type, ("#95a5a6", "Other"))
    return f'<span style="display:inline-block;background:{color};color:white;padding:2px 7px;border-radius:8px;font-size:9px;font-weight:600;letter-spacing:0.3px;">{label}</span>'


def categorize_by_type_and_role(jobs: list) -> dict:
    """Categorize jobs: Job Type > Role Category > list of jobs."""
    role_keywords = {
        "MERN / Full Stack": ["mern", "full stack", "fullstack", "full-stack"],
        "React / Frontend": ["react", "frontend", "front-end", "front end", "ui developer", "ui/ux"],
        "Node.js / Backend": ["node", "backend", "back-end", "back end", "express", "server"],
        "JavaScript / Web Dev": ["javascript", "web developer", "web dev", "html", "css"],
        "Software Engineer": ["software engineer", "software developer", "associate software", "application developer", "product engineer", "sde"],
        "Other Roles": [],
    }

    # Structure: {job_type: {role_category: [jobs]}}
    categorized = defaultdict(lambda: defaultdict(list))

    for job in jobs:
        title_lower = job.title.lower()
        role_cat = "Other Roles"
        for category, keywords in role_keywords.items():
            if category == "Other Roles":
                continue
            if any(kw in title_lower for kw in keywords):
                role_cat = category
                break
        categorized[job.job_type or "Work from Office"][role_cat].append(job)

    return categorized


def build_job_row(job, index: int) -> str:
    """Build a single job row HTML."""
    company_badge = get_company_type_badge(getattr(job, 'company_type', '') or 'Unknown')
    type_color = get_type_color(job.job_type)

    details = []
    if job.experience:
        details.append(f'<span style="color:#8e44ad;">📋 {job.experience}</span>')
    if job.salary:
        details.append(f'<span style="color:#27ae60;">💰 {job.salary}</span>')
    if job.source:
        details.append(f'<span style="color:#7f8c8d;">📍 {job.source}</span>')

    details_html = ' &nbsp;|&nbsp; '.join(details) if details else ''

    return f"""
    <tr style="border-bottom:1px solid #f0f0f0;{'background:#fafbff;' if index % 2 == 0 else ''}">
        <td style="padding:14px 16px;vertical-align:top;">
            <div style="font-weight:600;color:#1a1a2e;font-size:14px;margin-bottom:4px;">{job.title}</div>
            <div style="color:#444;font-size:13px;margin-bottom:4px;">
                🏢 {job.company} &nbsp; {company_badge}
            </div>
            <div style="color:#666;font-size:12px;margin-bottom:6px;">📍 {job.location}</div>
            <div style="font-size:11px;margin-bottom:4px;">{details_html}</div>
        </td>
        <td style="padding:14px 16px;vertical-align:middle;text-align:right;width:90px;">
            <a href="{job.url}" style="display:inline-block;background:linear-gradient(135deg,#667eea,#764ba2);color:white;padding:8px 14px;text-decoration:none;border-radius:6px;font-size:11px;font-weight:600;">Apply →</a>
        </td>
    </tr>"""


def build_premium_email_html(user_name: str, jobs: list) -> str:
    """Build premium categorized HTML email."""
    date_str = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    categorized = categorize_by_type_and_role(jobs)

    # Stats
    type_counts = defaultdict(int)
    company_type_counts = defaultdict(int)
    source_counts = defaultdict(int)
    for job in jobs:
        type_counts[job.job_type or "Unknown"] += 1
        company_type_counts[getattr(job, 'company_type', '') or "Unknown"] += 1
        source_counts[job.source] += 1

    # Type badges HTML
    type_badges = ""
    for jtype, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
        color = get_type_color(jtype)
        type_badges += f'<span style="display:inline-block;background:{color};color:white;padding:5px 12px;border-radius:14px;font-size:12px;margin:3px 4px;font-weight:500;">{jtype}: {count}</span>'

    # Company type badges
    ct_badges = ""
    ct_colors = {"Product": "#8e44ad", "Service": "#e67e22", "Startup": "#1abc9c", "Unknown": "#95a5a6"}
    for ct, count in sorted(company_type_counts.items(), key=lambda x: x[1], reverse=True):
        color = ct_colors.get(ct, "#95a5a6")
        label = "Product Based" if ct == "Product" else "Service Based" if ct == "Service" else ct
        ct_badges += f'<span style="display:inline-block;background:{color}22;color:{color};padding:4px 10px;border-radius:12px;font-size:11px;margin:2px 3px;border:1px solid {color}44;font-weight:500;">{label}: {count}</span>'

    source_list = " | ".join([f"{src}: {cnt}" for src, cnt in sorted(source_counts.items(), key=lambda x: x[1], reverse=True)])

    # Build categorized sections
    sections_html = ""
    job_type_order = ["Remote", "Work from Office", "Walk-in Interview", "Hybrid"]

    for jtype in job_type_order:
        if jtype not in categorized:
            continue
        roles_dict = categorized[jtype]
        type_color = get_type_color(jtype)
        total_in_type = sum(len(v) for v in roles_dict.values())

        # Job type header
        sections_html += f"""
        <div style="margin-top:28px;">
            <div style="background:{type_color};padding:14px 20px;border-radius:10px 10px 0 0;">
                <h2 style="margin:0;color:white;font-size:17px;font-weight:700;">
                    {'🏠' if jtype == 'Remote' else '🏢' if jtype == 'Work from Office' else '🚶' if jtype == 'Walk-in Interview' else '🔄'} {jtype} Jobs
                </h2>
                <span style="color:rgba(255,255,255,0.85);font-size:12px;">{total_in_type} positions found</span>
            </div>
        """

        # Role subcategories within this job type
        for role_cat, role_jobs in sorted(roles_dict.items(), key=lambda x: len(x[1]), reverse=True):
            if not role_jobs:
                continue

            # Group by company type within role
            by_company_type = defaultdict(list)
            for j in role_jobs:
                by_company_type[getattr(j, 'company_type', '') or 'Unknown'].append(j)

            rows_html = ""
            idx = 0
            for ct in ["Product", "Startup", "Service", "Unknown"]:
                if ct not in by_company_type:
                    continue
                ct_jobs = by_company_type[ct]
                for job in ct_jobs:
                    rows_html += build_job_row(job, idx)
                    idx += 1

            sections_html += f"""
            <div style="background:white;border:1px solid #e8e8e8;border-top:none;padding:0;">
                <div style="background:#f8f9ff;padding:10px 18px;border-bottom:1px solid #eee;">
                    <span style="font-weight:600;color:#333;font-size:13px;">💼 {role_cat}</span>
                    <span style="color:#888;font-size:11px;margin-left:8px;">({len(role_jobs)} jobs)</span>
                </div>
                <table style="width:100%;border-collapse:collapse;">
                    {rows_html}
                </table>
            </div>
            """

        sections_html += "</div>"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
    <body style="margin:0;padding:0;background:#f4f4f8;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
        <div style="max-width:720px;margin:0 auto;padding:20px;">

            <!-- Header -->
            <div style="background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);padding:32px;border-radius:14px 14px 0 0;text-align:center;">
                <h1 style="color:white;margin:0;font-size:28px;font-weight:800;">🚀 Job Finder AI</h1>
                <p style="color:rgba(255,255,255,0.85);margin:10px 0 0 0;font-size:14px;">Your personalized India-based job matches</p>
            </div>

            <!-- Summary Card -->
            <div style="background:white;padding:24px;border-left:1px solid #e8e8e8;border-right:1px solid #e8e8e8;">
                <p style="margin:0 0 6px 0;color:#333;font-size:16px;">Hi <strong>{user_name}</strong> 👋</p>
                <p style="margin:0 0 16px 0;color:#666;font-size:13px;">
                    We found <strong style="color:#667eea;font-size:18px;">{len(jobs)}</strong> jobs matching your profile!
                </p>

                <!-- Job Type Breakdown -->
                <div style="background:#f8f9ff;padding:14px 18px;border-radius:10px;border:1px solid #e8e8f8;margin-bottom:12px;">
                    <p style="margin:0 0 8px 0;font-size:11px;color:#555;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;">By Job Type</p>
                    <div>{type_badges}</div>
                </div>

                <!-- Company Type Breakdown -->
                <div style="background:#fdf8f3;padding:14px 18px;border-radius:10px;border:1px solid #f0e8e0;margin-bottom:12px;">
                    <p style="margin:0 0 8px 0;font-size:11px;color:#555;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;">By Company Type</p>
                    <div>{ct_badges}</div>
                </div>

                <p style="margin:0;font-size:11px;color:#999;">Sources: {source_list} &nbsp;|&nbsp; {date_str}</p>
            </div>

            <!-- Categorized Job Sections -->
            <div style="background:#fafafa;padding:4px 20px 24px 20px;border:1px solid #e8e8e8;border-top:none;">
                {sections_html}
            </div>

            <!-- Footer -->
            <div style="background:#1a1a2e;padding:24px;border-radius:0 0 14px 14px;text-align:center;">
                <p style="margin:0 0 8px 0;color:#ccc;font-size:12px;font-weight:500;">
                    Powered by Job Finder AI Agent
                </p>
                <p style="margin:0;color:#888;font-size:10px;">
                    Sources: LinkedIn, Indeed, Naukri, Internshala, CutShort, InstaHyre, Google Jobs, RemoteOK, FreshersWorld<br>
                    <span style="color:#667eea;">Disable auto-search in your dashboard to stop these emails</span>
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    return html


def send_job_alert_email(user_email: str, user_name: str, jobs: list) -> bool:
    """Send job alert email to user."""
    from app import mail
    from services.job_scraper import classify_company_type

    if not jobs:
        logger.info("No jobs to send")
        return False

    try:
        # Ensure all jobs have company_type classified
        for job in jobs:
            if not getattr(job, 'company_type', ''):
                job.company_type = classify_company_type(job.company)

        html_content = build_premium_email_html(user_name, jobs)

        plain_text = f"Hi {user_name},\n\nWe found {len(jobs)} jobs matching your profile.\nPlease view this email in an HTML-compatible email client to see the full job list.\n\nJob Finder AI\n"

        msg = Message(
            subject=f"Job Finder AI - {len(jobs)} New Job Matches ({datetime.now().strftime('%d %b %Y')})",
            recipients=[user_email],
            html=html_content,
            body=plain_text,
        )
        msg.reply_to = "noreply@jobfinderai.com"

        mail.send(msg)
        logger.info(f"Email sent to {user_email} with {len(jobs)} jobs")
        return True

    except Exception as e:
        logger.error(f"Email send failed for {user_email}: {e}")
        return False
