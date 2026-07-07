"""
Job Scraper Service - FIXED VERSION
Focuses on: India-based jobs, posted within last 2 weeks
Platforms: LinkedIn, Indeed, Naukri, Internshala, CutShort, InstaHyre, Google, RemoteOK, FreshersWorld

Key fixes:
- Updated URLs and selectors for each platform
- India-focused searches (Ahmedabad, Gandhinagar, Remote India)
- Only jobs posted in last 14 days
- Valid apply links
"""

import time
import random
import logging
import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)


@dataclass
class Job:
    title: str
    company: str
    location: str
    url: str
    source: str
    description: str = ""
    salary: str = ""
    posted_date: str = ""
    experience: str = ""
    job_type: str = ""
    company_type: str = ""  # Product / Service / Startup / Unknown


# Known product-based companies
PRODUCT_COMPANIES = {
    "google", "microsoft", "amazon", "apple", "meta", "facebook", "netflix",
    "flipkart", "swiggy", "zomato", "razorpay", "phonepe", "paytm", "cred",
    "meesho", "groww", "zerodha", "dream11", "unacademy", "byju", "byjus",
    "ola", "uber", "atlassian", "adobe", "salesforce", "oracle", "sap",
    "intuit", "freshworks", "zoho", "postman", "notion", "slack", "stripe",
    "shopify", "spotify", "twitter", "linkedin", "github", "gitlab",
    "juspay", "browserstack", "cleartax", "chargebee", "lenskart",
    "nykaa", "myntra", "ajio", "dunzo", "rapido", "urban company",
    "sharechat", "moj", "jupiter", "fi", "slice", "smallcase", "upstox",
    "polygon", "hasura", "innovaccer", "druva", "icertis", "darwinbox",
    "yellow.ai", "leadsquared", "clevertap", "moengage", "webengage",
    "whatfix", "mindtickle", "wingify", "hike", "practo", "1mg", "pharmeasy",
    "healthkart", "boat", "noise", "mamaearth", "sugar cosmetics",
    "spinny", "cars24", "cardekho", "delhivery", "shiprocket",
}

# Known service/consulting companies
SERVICE_COMPANIES = {
    "tcs", "tata consultancy", "infosys", "wipro", "hcl", "hcltech",
    "cognizant", "tech mahindra", "capgemini", "accenture", "deloitte",
    "kpmg", "ey", "ernst", "pwc", "pricewaterhouse", "mckinsey",
    "boston consulting", "bain", "mindtree", "ltimindtree", "lti",
    "mphasis", "hexaware", "cyient", "persistent", "zensar",
    "birlasoft", "sonata software", "niit", "mastek", "coforge",
    "happiest minds", "l&t infotech", "larsen", "virtusa", "ust",
    "thoughtworks", "epam", "globant", "nagarro", "publicis sapient",
    "mu sigma", "fractal", "tiger analytics", "latent view",
    "genpact", "atos", "dxc", "ntt data", "fujitsu",
}

# Startup indicators
STARTUP_INDICATORS = {
    "startup", "stealth", "early stage", "seed funded", "series a",
    "series b", "ycombinator", "y combinator",
}


def classify_company_type(company: str) -> str:
    """Classify company as Product/Service/Startup based on name."""
    if not company:
        return "Unknown"
    company_lower = company.lower().strip()

    for name in PRODUCT_COMPANIES:
        if name in company_lower:
            return "Product"

    for name in SERVICE_COMPANIES:
        if name in company_lower:
            return "Service"

    for indicator in STARTUP_INDICATORS:
        if indicator in company_lower:
            return "Startup"

    return "Unknown"


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept-Language": "en-IN,en;q=0.9,hi;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate",
}


def safe_request(url: str, timeout: int = 20) -> Optional[requests.Response]:
    """Make a safe HTTP request with retries."""
    for attempt in range(2):
        try:
            response = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
            if response.status_code == 200:
                return response
            if response.status_code == 403:
                logger.warning(f"Blocked (403) for {url}")
                return None
            logger.warning(f"HTTP {response.status_code} for {url}")
        except requests.Timeout:
            logger.warning(f"Timeout (attempt {attempt+1}) for {url}")
        except requests.ConnectionError:
            logger.warning(f"Connection error for {url}")
        except Exception as e:
            logger.error(f"Request error for {url}: {e}")
            return None
        time.sleep(1)
    return None


def delay():
    """Random delay between requests."""
    time.sleep(random.uniform(2, 4))


# ============================================================
# LINKEDIN - Using public job search (no login needed)
# ============================================================
def scrape_linkedin(roles: list, locations: list) -> list[Job]:
    """Scrape LinkedIn public job listings for India."""
    jobs = []
    search_roles = roles[:4]

    for role in search_roles:
        for location in locations:
            try:
                if location.lower() == "remote":
                    query = quote_plus(f"{role}")
                    # f_WT=2 = Remote, f_E=1,2 = Entry/Associate, f_TPR=r1209600 = past 2 weeks, geoId=102713980 = India
                    url = f"https://www.linkedin.com/jobs/search/?keywords={query}&f_E=1%2C2&f_TPR=r1209600&f_WT=2&geoId=102713980"
                else:
                    query = quote_plus(f"{role}")
                    loc_query = quote_plus(location)
                    url = f"https://www.linkedin.com/jobs/search/?keywords={query}&location={loc_query}%2C+India&f_E=1%2C2&f_TPR=r1209600"

                response = safe_request(url)
                if not response:
                    continue

                soup = BeautifulSoup(response.text, "html.parser")
                cards = soup.find_all("div", class_="base-card")[:6]

                for card in cards:
                    title_el = card.find("h3", class_="base-search-card__title")
                    company_el = card.find("h4", class_="base-search-card__subtitle")
                    location_el = card.find("span", class_="job-search-card__location")
                    link_el = card.find("a", class_="base-card__full-link")
                    time_el = card.find("time")

                    if title_el and company_el and link_el:
                        loc_text = location_el.text.strip() if location_el else location
                        jtype = "Remote" if "remote" in loc_text.lower() else "Work from Office"
                        job_url = link_el.get("href", "")
                        # Clean LinkedIn URL
                        if "?" in job_url:
                            job_url = job_url.split("?")[0]

                        jobs.append(Job(
                            title=title_el.text.strip(),
                            company=company_el.text.strip(),
                            location=loc_text,
                            url=job_url,
                            source="LinkedIn",
                            job_type=jtype,
                            posted_date=time_el.get("datetime", "") if time_el else "",
                        ))
            except Exception as e:
                logger.error(f"[LinkedIn] Error for {role}/{location}: {e}")
            delay()
    return jobs


# ============================================================
# INDEED INDIA - Generate direct search links (site blocks scraping)
# ============================================================
def scrape_indeed(roles: list, locations: list) -> list[Job]:
    """Generate Indeed India direct search links - site blocks automated access."""
    jobs = []
    search_roles = roles[:4]

    for role in search_roles:
        for location in locations:
            query = quote_plus(role)
            if location.lower() == "remote":
                url = f"https://in.indeed.com/jobs?q={query}&fromage=14&remotejob=032b3046-06a3-4876-8dfd-474eb5e7ed11"
                jtype = "Remote"
            else:
                loc = quote_plus(location)
                url = f"https://in.indeed.com/jobs?q={query}&l={loc}&fromage=14"
                jtype = "Work from Office"

            jobs.append(Job(
                title=f"{role} - {location}",
                company="Multiple Companies (Indeed)",
                location=location,
                url=url,
                source="Indeed",
                experience="Fresher",
                job_type=jtype,
                description=f"Click to see all {role} jobs in {location} on Indeed",
            ))
    return jobs


# ============================================================
# NAUKRI - Generate direct search links (site is fully JS-rendered)
# ============================================================
def scrape_naukri(roles: list, locations: list) -> list[Job]:
    """Generate Naukri direct search links - site blocks scraping."""
    jobs = []
    search_roles = roles[:5]

    for role in search_roles:
        for location in locations:
            query_slug = role.lower().replace(" ", "-").replace(".", "").replace("/", "-")
            if location.lower() == "remote":
                url = f"https://www.naukri.com/{query_slug}-jobs?experience=0-1&jobAge=14&wfhType=2"
                jtype = "Remote"
            else:
                loc_slug = location.lower().replace(" ", "-")
                url = f"https://www.naukri.com/{query_slug}-jobs-in-{loc_slug}?experience=0-1&jobAge=14"
                jtype = "Work from Office"

            jobs.append(Job(
                title=f"{role} - {location}",
                company="Multiple Companies (Naukri)",
                location=location,
                url=url,
                source="Naukri",
                experience="Fresher / 0-1 yr",
                job_type=jtype,
                description=f"Click to see all {role} jobs in {location} on Naukri",
            ))
    return jobs


# ============================================================
# NAUKRI WALK-IN
# ============================================================
def scrape_naukri_walkin(locations: list) -> list[Job]:
    """Scrape Naukri walk-in jobs specifically."""
    jobs = []
    walkin_searches = [
        "walkin-developer", "walkin-react", "walkin-mern",
        "walkin-frontend", "walkin-software-developer", "walkin-web-developer",
    ]

    for query in walkin_searches:
        for location in locations:
            if location.lower() == "remote":
                continue
            try:
                loc = location.lower().replace(" ", "-")
                url = f"https://www.naukri.com/{query}-jobs-in-{loc}?experience=0-1&jobAge=14"
                response = safe_request(url)
                if not response:
                    continue

                soup = BeautifulSoup(response.text, "html.parser")
                cards = soup.find_all("article", class_="jobTuple")
                if not cards:
                    cards = soup.find_all("div", class_="srp-jobtuple-wrapper")

                for card in cards[:3]:
                    title_el = card.find("a", class_="title") or card.find("a", attrs={"class": lambda c: c and "title" in str(c)})
                    company_el = card.find("a", class_="subTitle")
                    location_el = card.find("li", class_="location")

                    if title_el:
                        job_url = title_el.get("href", "")
                        if job_url and not job_url.startswith("http"):
                            job_url = f"https://www.naukri.com{job_url}"

                        jobs.append(Job(
                            title=title_el.get_text(strip=True),
                            company=company_el.get_text(strip=True) if company_el else "Unknown",
                            location=location_el.get_text(strip=True) if location_el else location,
                            url=job_url,
                            source="Naukri (Walk-in)",
                            experience="Fresher",
                            job_type="Walk-in Interview",
                        ))
            except Exception as e:
                logger.error(f"[Naukri Walk-in] Error: {e}")
            delay()
    return jobs


# ============================================================
# INTERNSHALA - Fresher jobs
# ============================================================
def scrape_internshala(roles: list, locations: list) -> list[Job]:
    """Scrape Internshala fresher jobs based on user's actual roles."""
    jobs = []

    # Convert user roles to Internshala URL slugs
    search_terms = set()
    for role in roles:
        slug = role.lower().replace(".", "").replace("/", "-").replace(" ", "-")
        search_terms.add(slug)
    # Also add common variations
    role_text = " ".join(roles).lower()
    if "react" in role_text:
        search_terms.add("reactjs")
    if "frontend" in role_text or "front-end" in role_text or "front end" in role_text:
        search_terms.add("front-end-development")
    if "node" in role_text:
        search_terms.add("node-js")
    if "mern" in role_text or "full stack" in role_text:
        search_terms.add("mern-stack")
        search_terms.add("full-stack-development")
    if "web" in role_text:
        search_terms.add("web-development")

    for term in list(search_terms)[:6]:
        for location in locations:
            try:
                if location.lower() == "remote":
                    url = f"https://internshala.com/jobs/work-from-home-{term}-jobs"
                else:
                    loc = location.lower().replace(" ", "-")
                    url = f"https://internshala.com/jobs/{term}-jobs-in-{loc}"

                response = safe_request(url)
                if not response:
                    continue

                soup = BeautifulSoup(response.text, "html.parser")

                # Try multiple selectors
                cards = soup.find_all("div", class_="individual_internship")
                if not cards:
                    cards = soup.find_all("div", class_="internship_meta")
                if not cards:
                    cards = soup.find_all("div", attrs={"class": lambda c: c and "individual" in str(c)})

                for card in cards[:5]:
                    title_el = card.find("h3") or card.find("a", class_="job-title-href")
                    company_el = card.find("p", class_="company-name") or card.find("a", class_="link_display_like_text")
                    location_el = card.find("p", class_="location_link") or card.find("span", class_="location_link")
                    link_el = card.find("a", href=True)
                    stipend_el = card.find("span", class_="desktop") or card.find("span", class_="stipend")

                    if title_el:
                        title_text = title_el.get_text(strip=True)
                        loc_text = location_el.get_text(strip=True) if location_el else location

                        job_url = ""
                        if link_el:
                            href = link_el.get("href", "")
                            if href.startswith("/"):
                                job_url = f"https://internshala.com{href}"
                            elif href.startswith("http"):
                                job_url = href

                        jtype = "Remote" if "remote" in loc_text.lower() or "home" in loc_text.lower() else "Work from Office"

                        if title_text:
                            jobs.append(Job(
                                title=title_text,
                                company=company_el.get_text(strip=True) if company_el else "Unknown",
                                location=loc_text,
                                url=job_url,
                                source="Internshala",
                                experience="Fresher",
                                job_type=jtype,
                                salary=stipend_el.get_text(strip=True) if stipend_el else "",
                            ))
            except Exception as e:
                logger.error(f"[Internshala] Error: {e}")
            delay()
    return jobs


# ============================================================
# CUTSHORT
# ============================================================
def scrape_cutshort(roles: list) -> list[Job]:
    """Scrape CutShort for developer jobs in India based on user's roles."""
    jobs = []
    # Convert user roles to search terms
    search_terms = set()
    for role in roles:
        slug = role.lower().replace(".", "").replace(" ", "-")
        search_terms.add(slug)

    # Build role keywords for title matching
    role_keywords = set()
    for role in roles:
        for word in role.lower().replace(".", "").split():
            if len(word) > 2:
                role_keywords.add(word)

    for term in list(search_terms)[:5]:
        try:
            url = f"https://cutshort.io/jobs?q={term}&exp=0-2&city=ahmedabad,remote"
            response = safe_request(url)
            if not response:
                continue

            soup = BeautifulSoup(response.text, "html.parser")
            # CutShort renders via JS, try to get any job links
            links = soup.find_all("a", href=True)

            for link in links:
                href = link.get("href", "")
                if "/job/" in href and href.startswith("/"):
                    title_text = link.get_text(strip=True)
                    if title_text and len(title_text) > 5 and any(kw in title_text.lower() for kw in role_keywords):
                        job_url = f"https://cutshort.io{href}"
                        jobs.append(Job(
                            title=title_text,
                            company="See CutShort",
                            location="India",
                            url=job_url,
                            source="CutShort",
                            experience="0-2 years",
                            job_type="Work from Office",
                        ))
        except Exception as e:
            logger.error(f"[CutShort] Error: {e}")
        delay()
    return jobs


# ============================================================
# INSTAHYRE
# ============================================================
def scrape_instahyre(roles: list, locations: list) -> list[Job]:
    """Scrape InstaHyre for developer jobs."""
    jobs = []
    search_terms = ["react", "mern", "nodejs", "frontend", "full-stack", "javascript"]

    for term in search_terms:
        try:
            url = f"https://www.instahyre.com/search-jobs/?designation={term}&experience=0-2&location=ahmedabad"
            response = safe_request(url)
            if not response:
                continue

            soup = BeautifulSoup(response.text, "html.parser")
            # InstaHyre also renders via JS, extract what we can
            cards = soup.find_all("div", class_="job-card")
            if not cards:
                # Try finding any job-related content
                links = soup.find_all("a", href=True)
                for link in links:
                    href = link.get("href", "")
                    text = link.get_text(strip=True)
                    if "/job/" in href and text and len(text) > 5:
                        job_url = href if href.startswith("http") else f"https://www.instahyre.com{href}"
                        jobs.append(Job(
                            title=text,
                            company="See InstaHyre",
                            location="India",
                            url=job_url,
                            source="InstaHyre",
                            experience="0-2 years",
                            job_type="Work from Office",
                        ))

            for card in cards[:5]:
                title_el = card.find("h3") or card.find("a")
                company_el = card.find("div", class_="company-name") or card.find("p")
                location_el = card.find("span", class_="location")

                if title_el:
                    loc_text = location_el.get_text(strip=True) if location_el else "India"
                    jtype = "Remote" if "remote" in loc_text.lower() else "Work from Office"
                    link = card.find("a", href=True)
                    job_url = link.get("href", "") if link else ""
                    if job_url and not job_url.startswith("http"):
                        job_url = f"https://www.instahyre.com{job_url}"

                    jobs.append(Job(
                        title=title_el.get_text(strip=True),
                        company=company_el.get_text(strip=True) if company_el else "Unknown",
                        location=loc_text,
                        url=job_url,
                        source="InstaHyre",
                        experience="0-2 years",
                        job_type=jtype,
                    ))
        except Exception as e:
            logger.error(f"[InstaHyre] Error: {e}")
        delay()
    return jobs


# ============================================================
# GOOGLE JOBS - Direct search links
# ============================================================
def scrape_google_jobs(roles: list, locations: list) -> list[Job]:
    """Generate Google Jobs search links for each role/location."""
    jobs = []
    search_roles = roles[:5]

    for role in search_roles:
        for location in locations:
            try:
                if location.lower() == "remote":
                    query = f"{role} remote India fresher"
                else:
                    query = f"{role} {location} fresher"

                encoded_query = quote_plus(query)
                # Google Jobs direct link - always works
                google_jobs_url = f"https://www.google.com/search?q={encoded_query}+jobs&ibp=htl;jobs&htichips=date_posted:week"

                jtype = "Remote" if location.lower() == "remote" else "Work from Office"

                jobs.append(Job(
                    title=f"{role} - {location}",
                    company="Multiple Companies (Google Jobs)",
                    location=location,
                    url=google_jobs_url,
                    source="Google Jobs",
                    job_type=jtype,
                    experience="Fresher",
                    description=f"Click to see all {role} jobs in {location} on Google Jobs",
                ))
            except Exception as e:
                logger.error(f"[Google Jobs] Error: {e}")
    return jobs


# ============================================================
# REMOTEOK - API (only India-friendly remote jobs)
# ============================================================
def scrape_remoteok(roles: list = None) -> list[Job]:
    """Scrape RemoteOK API - filter based on user's actual roles."""
    jobs = []
    try:
        url = "https://remoteok.com/api"
        headers = {**HEADERS, "Accept": "application/json"}
        response = requests.get(url, headers=headers, timeout=20)
        if response.status_code != 200:
            return jobs

        data = response.json()

        # Build keywords from user's roles
        relevant_keywords = set()
        if roles:
            for role in roles:
                for word in role.lower().replace(".", "").replace("/", " ").split():
                    if len(word) > 2 and word not in {"the", "and", "for", "jobs", "developer", "engineer"}:
                        relevant_keywords.add(word)
            # Always include the full role names too
            for role in roles:
                relevant_keywords.add(role.lower())
        else:
            relevant_keywords = {
                "react", "node", "frontend", "backend", "mern", "full stack",
                "javascript", "web developer", "software engineer",
            }

        for item in data[1:80]:
            title = item.get("position", "")
            tags = [t.lower() for t in item.get("tags", [])]
            title_lower = title.lower()
            company = item.get("company", "Unknown")
            location = item.get("location", "Remote")

            # Skip if explicitly US/UK only
            loc_lower = location.lower()
            if any(x in loc_lower for x in ["us only", "usa only", "uk only", "europe only", "north america"]):
                continue

            if any(kw in title_lower or any(kw in tag for tag in tags) for kw in relevant_keywords):
                job_url = item.get("url", "")
                if not job_url:
                    job_url = f"https://remoteok.com{item.get('slug', '')}"
                if not job_url.startswith("http"):
                    job_url = f"https://remoteok.com{job_url}"

                jobs.append(Job(
                    title=title,
                    company=company,
                    location="Remote (Global)",
                    url=job_url,
                    source="RemoteOK",
                    salary=str(item.get("salary_min", "")) if item.get("salary_min") else "",
                    posted_date=item.get("date", "")[:10] if item.get("date") else "",
                    job_type="Remote",
                ))
    except Exception as e:
        logger.error(f"[RemoteOK] Error: {e}")
    return jobs


# ============================================================
# FRESHERSWORLD
# ============================================================
def scrape_freshersworld(roles: list, locations: list) -> list[Job]:
    """Scrape FreshersWorld for fresher/walk-in jobs based on user's roles."""
    jobs = []

    # Convert user roles to URL slugs
    searches = set()
    for role in roles:
        slug = role.lower().replace(".", "").replace("/", "-").replace(" ", "-")
        searches.add(slug)

    for search in list(searches)[:5]:
        for location in locations:
            if location.lower() == "remote":
                continue
            try:
                loc = location.lower().replace(" ", "-")
                url = f"https://www.freshersworld.com/jobs/jobsearch/{search}-jobs-in-{loc}-for-freshers"
                response = safe_request(url)
                if not response:
                    continue

                soup = BeautifulSoup(response.text, "html.parser")
                cards = soup.find_all("div", class_="job-container")
                if not cards:
                    cards = soup.find_all("div", class_="job-list")

                for card in cards[:4]:
                    title_el = card.find("span", class_="wrap-title") or card.find("a", class_="job-title")
                    company_el = card.find("h3", class_="company-name") or card.find("span", class_="company-name")
                    location_el = card.find("span", class_="job-location")
                    link_el = card.find("a", href=True)

                    if title_el:
                        title_text = title_el.get_text(strip=True)
                        jtype = "Walk-in Interview" if "walk" in title_text.lower() else "Work from Office"

                        job_url = ""
                        if link_el:
                            href = link_el.get("href", "")
                            if href.startswith("http"):
                                job_url = href
                            elif href.startswith("/"):
                                job_url = f"https://www.freshersworld.com{href}"

                        jobs.append(Job(
                            title=title_text,
                            company=company_el.get_text(strip=True) if company_el else "Unknown",
                            location=location_el.get_text(strip=True) if location_el else location,
                            url=job_url,
                            source="FreshersWorld",
                            experience="Fresher",
                            job_type=jtype,
                        ))
            except Exception as e:
                logger.error(f"[FreshersWorld] Error: {e}")
            delay()
    return jobs


# ============================================================
# RELEVANCE FILTER - Remove jobs that don't match user's roles
# ============================================================
def is_relevant_job(job: Job, preferences: dict) -> bool:
    """Check if a job is relevant to user's selected roles and skills."""
    roles = preferences.get("roles", [])
    skills = preferences.get("skills", [])

    if not roles:
        return True

    title_lower = job.title.lower()
    desc_lower = job.description.lower()
    combined = f"{title_lower} {desc_lower}"

    # Build keywords from user's roles
    role_keywords = set()
    for role in roles:
        # Split role into meaningful words
        words = role.lower().replace(".", "").replace("/", " ").split()
        for word in words:
            if len(word) > 2 and word not in {"the", "and", "for", "jobs", "job"}:
                role_keywords.add(word)

    # Build keywords from skills
    skill_keywords = set()
    for skill in skills:
        skill_keywords.add(skill.lower().replace(".", "").strip())
        # Also add individual words for multi-word skills
        for word in skill.lower().replace(".", "").split():
            if len(word) > 2:
                skill_keywords.add(word)

    # Check if job title contains at least one role keyword
    role_match = any(kw in combined for kw in role_keywords)

    # Check if job title contains at least one skill keyword
    skill_match = any(kw in combined for kw in skill_keywords)

    # Irrelevant job indicators - titles that clearly don't match tech roles
    irrelevant_keywords = [
        "sales", "marketing", "business development", "bde", "telecaller",
        "hr ", "human resource", "accountant", "finance", "banking",
        "teacher", "faculty", "professor", "nurse", "doctor", "medical",
        "driver", "delivery boy", "peon", "clerk", "receptionist",
        "security", "guard", "housekeeping", "cook", "chef",
        "civil engineer", "mechanical", "electrical engineer",
        "pharmaceutical", "pharma", "chemical", "biotechnology",
        "content writer", "copywriter", "graphic design",
        "data entry", "back office", "office assistant", "admin",
        "customer support", "customer service", "bpo", "call center",
    ]

    # If title contains irrelevant keywords AND doesn't match roles/skills, reject
    has_irrelevant = any(kw in title_lower for kw in irrelevant_keywords)
    if has_irrelevant and not role_match and not skill_match:
        return False

    # Must match at least one role or skill keyword
    return role_match or skill_match


# ============================================================
# MAIN SCRAPER
# ============================================================
def scrape_all_jobs(preferences: dict) -> list[Job]:
    """Scrape all platforms based on user preferences."""
    roles = preferences.get("roles", [])
    locations = preferences.get("locations", [])
    job_types = preferences.get("job_types", [])

    if not roles:
        return []

    # Only include RemoteOK if user wants Remote jobs
    wants_remote = "remote" in [l.lower() for l in locations] or "Remote" in job_types

    all_jobs = []
    errors = []

    scrapers = [
        ("LinkedIn", lambda: scrape_linkedin(roles, locations)),
        ("Indeed", lambda: scrape_indeed(roles, locations)),
        ("Naukri", lambda: scrape_naukri(roles, locations)),
        ("Internshala", lambda: scrape_internshala(roles, locations)),
        ("CutShort", lambda: scrape_cutshort(roles)),
        ("InstaHyre", lambda: scrape_instahyre(roles, locations)),
        ("Google Jobs", lambda: scrape_google_jobs(roles, locations)),
        ("FreshersWorld", lambda: scrape_freshersworld(roles, locations)),
    ]

    # Only add RemoteOK if user wants remote jobs
    if wants_remote:
        scrapers.append(("RemoteOK", lambda: scrape_remoteok(roles)))

    for name, scraper in scrapers:
        try:
            result = scraper()
            all_jobs.extend(result)
            logger.info(f"{name}: {len(result)} jobs")
        except Exception as e:
            errors.append(f"{name}: {e}")
            logger.error(f"{name} failed: {e}")

    if errors:
        logger.warning(f"Scraping errors: {errors}")

    # Remove jobs with empty/invalid URLs
    valid_jobs = [j for j in all_jobs if j.url and (j.url.startswith("http") or j.url.startswith("https"))]

    # Filter out irrelevant jobs
    relevant_jobs = [j for j in valid_jobs if is_relevant_job(j, preferences)]
    logger.info(f"Relevance filter: {len(valid_jobs)} -> {len(relevant_jobs)} jobs")

    # Filter out remote jobs if user didn't select Remote
    if not wants_remote:
        relevant_jobs = [j for j in relevant_jobs if j.job_type != "Remote"]

    # Classify company types
    for job in relevant_jobs:
        job.company_type = classify_company_type(job.company)

    logger.info(f"Total final jobs: {len(relevant_jobs)}")
    return relevant_jobs
