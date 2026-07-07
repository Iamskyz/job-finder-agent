"""
Job Matcher Service
Ranks jobs by relevance using TF-IDF + custom boosting.
No limit on results - returns ALL matched jobs.
"""

import logging
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)


def build_profile_text(preferences: dict) -> str:
    """Build text representation of user profile."""
    parts = [
        f"Roles: {' '.join(preferences.get('roles', []))}",
        f"Skills: {' '.join(preferences.get('skills', []))}",
        f"Experience: {preferences.get('experience', '')}",
        f"Locations: {' '.join(preferences.get('locations', []))}",
    ]
    return " ".join(parts)


def build_job_text(job) -> str:
    """Build text representation of a job."""
    parts = [job.title, job.company, job.location, job.description, job.experience, job.job_type]
    return " ".join(p for p in parts if p)


def rank_jobs(jobs: list, preferences: dict) -> list:
    """
    Rank ALL jobs by relevance. No limit.
    Boosts: walk-in, WFO, fresher, location match, skill match.
    """
    if not jobs:
        return []

    user_text = build_profile_text(preferences)
    job_texts = [build_job_text(job) for job in jobs]
    all_texts = [user_text] + job_texts

    try:
        vectorizer = TfidfVectorizer(stop_words="english", max_features=5000)
        tfidf_matrix = vectorizer.fit_transform(all_texts)
        user_vector = tfidf_matrix[0:1]
        job_vectors = tfidf_matrix[1:]
        similarities = cosine_similarity(user_vector, job_vectors)[0]
    except Exception as e:
        logger.error(f"TF-IDF error: {e}")
        return jobs  # Return unsorted if matching fails

    # Custom boosting
    target_skills = [s.lower() for s in preferences.get("skills", [])]
    target_roles = [r.lower() for r in preferences.get("roles", [])]
    target_locations = [l.lower() for l in preferences.get("locations", [])]

    boosted_scores = []
    for job, score in zip(jobs, similarities):
        boost = 0
        text = build_job_text(job).lower()

        # Skill match boost
        for skill in target_skills:
            if skill in text:
                boost += 0.04

        # Role match boost
        for role in target_roles:
            if role in text:
                boost += 0.06

        # Location match boost
        for loc in target_locations:
            if loc in text:
                boost += 0.12

        # Fresher/entry level boost
        if any(t in text for t in ["fresher", "entry level", "0-1", "junior", "graduate", "trainee"]):
            boost += 0.2

        # Walk-in interview boost (highest priority)
        if any(t in text for t in ["walk-in", "walkin", "walk in"]):
            boost += 0.3

        # Work from Office boost
        if any(t in text for t in ["work from office", "wfo", "on-site", "onsite"]):
            boost += 0.15

        # MERN specific boost
        if any(t in text for t in ["mern", "react", "node.js", "nodejs", "mongodb", "express"]):
            boost += 0.1

        boosted_scores.append((job, score + boost))

    # Sort by score
    boosted_scores.sort(key=lambda x: x[1], reverse=True)
    ranked = [job for job, _ in boosted_scores]

    logger.info(f"Ranked {len(ranked)} jobs (no limit)")
    return ranked


def remove_duplicates(jobs: list) -> list:
    """Remove duplicate jobs based on title + company."""
    seen = set()
    unique = []
    for job in jobs:
        key = f"{job.title.lower().strip()}|{job.company.lower().strip()}"
        if key not in seen:
            seen.add(key)
            unique.append(job)
    logger.info(f"Dedup: {len(jobs)} -> {len(unique)} jobs")
    return unique
