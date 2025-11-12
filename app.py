# app.py
import os
import smtplib
import time
import re
import urllib.parse
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# -------------------------
# CHROME / SELENIUM SETUP
# -------------------------
chrome_options = Options()
# preserve your original flags (matching your working setup)
chrome_options.add_argument("headless")
chrome_options.add_argument("no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
time.sleep(1)

# -------------------------
# ROLE/KEYWORD LIST (from you)
# -------------------------
# Using exact phrases & additional keywords for flexible matching (case-insensitive)
ROLE_PHRASES = [
    "Full Stack Developer Python","Full Stack Python Developer","Python Full Stack Engineer",
    "React Python Developer","MERN Stack Developer Python","Full Stack Web Developer (React + Python)",
    "Django React Developer","Flask React Developer","Backend Developer Python",
    "Frontend Developer React","React JS Django","React JS Flask","Python REST API Developer",
    "React Redux Django","React Hooks Django","React Frontend with Python Backend",
    "REST API Python React","FastAPI React Developer","Full Stack Intern Python React",
    "Python Full Stack Internship","Full Stack Developer Intern (Python + React)",
    "Web Development Internship Python React","Entry Level Full Stack Developer Python",
    "Junior Python Developer React","Software Developer Trainee Python React",
    "Fresher Full Stack Python Developer","Campus Hiring Python React Developer",
    "React Django","React Flask","React FastAPI","Python + React","REST API + React",
    "PostgreSQL Django React","MongoDB Express React Python","React Node Django",
    "Full Stack","Python","React","Django","Flask","FastAPI","REST API",
    "Internship","Fresher","Trainee","Entry Level","Remote","Hybrid",
    "Backend","Frontend","Web Developer","MERN","PostgreSQL",
    # Data / ML / AI roles included
    "Data Analyst (Python + SQL)","Junior Data Analyst (Excel + Power BI)",
    "Business Data Analyst (Tableau + Python)","Financial Data Analyst (Excel + Python)",
    "Marketing Data Analyst (Google Analytics + SQL)","Data Visualization Specialist (Power BI / Tableau)",
    "Data Reporting Analyst (SQL + Excel)","Data Insights Analyst (Python + Dashboarding)",
    "Operations Data Analyst","Product Data Analyst",
    "Data Scientist (Python + Machine Learning)","Applied Data Scientist",
    "Junior Data Scientist (Pandas + Scikit-learn)","Data Science Engineer (ML + AI)",
    "Research Data Scientist (Deep Learning)","Business Data Scientist (Predictive Analytics)",
    "Data Science Specialist (NLP + LLMs)","AI Data Scientist (Generative AI + Python)",
    "Full Stack Data Scientist (Data + ML + Deployment)","Machine Learning Data Scientist",
    "Machine Learning Engineer (Python + TensorFlow)","ML Engineer (NLP + Computer Vision)",
    "Deep Learning Engineer (PyTorch + Transformers)","Applied ML Engineer",
    "AI/ML Developer (Python + MLOps)","ML Research Engineer (Deep Learning + LLMs)",
    "Machine Learning Specialist (Model Optimization)","ML Operations Engineer (MLOps + Cloud)",
    "ML Backend Engineer (API + Model Serving)","ML Data Engineer",
    "AI Engineer (Python + LLMs)","Artificial Intelligence Developer",
    "Generative AI Engineer (OpenAI + LangChain)","AI Research Scientist",
    "AI Developer (Chatbot + NLP)","AI Solutions Engineer (ML + Cloud)",
    "AI Software Engineer (Deep Learning + APIs)","Applied AI Engineer (Computer Vision + NLP)",
    "AI/ML Architect","AI Product Engineer"
]

# Normalized keyword set for flexible matching (lowercase)
KEYWORDS = list({p.lower() for p in ROLE_PHRASES})

# EXCLUDE (senior / unrelated stacks)
EXCLUDE_KEYWORDS = [
    "php","laravel","wordpress","drupal",".net","c#","java","spring","hibernate",
    "senior","lead","manager","3 year","3 years","4 year","4 years","5 year","5 years","5+"
]
EXCLUDE_LOWER = [e.lower() for e in EXCLUDE_KEYWORDS]

# Experience acceptance phrases (we will accept if job text contains any of these)
ACCEPT_EXPS = [
    "fresher", "freshers", "intern", "internship", "trainee", "entry level", "0-1", "0 - 1",
    "0-2", "0 - 2", "0 to 1", "0 to 2", "<2 years", "below 2", "1 year", "1 yrs", "1-2"
]
ACCEPT_LOWER = [a.lower() for a in ACCEPT_EXPS]

# -------------------------
# Helper functions
# -------------------------
def looks_relevant(title, snippet=""):
    """
    Decide if a job title/snippet is relevant:
    - contains at least one KEYWORD and one of (python/react/data/ml/ai)
    - does not contain excluded keywords (senior/java/php etc.)
    - experience matches fresher/trainee/<2 years by checking title/snippet
    """
    text = (title + " " + snippet).lower()

    # exclude if any exclude token present
    if any(ex in text for ex in EXCLUDE_LOWER):
        return False

    # must contain at least one important token (python/react/data/ml/ai or listed keyphrases)
    must_have = ["python", "react", "data", "ml", "ai", "django", "flask", "fastapi", "rest api", "full stack"]
    if not any(token in text for token in must_have):
        return False

    # also allow if any KEYWORDS exact phrase in text
    if any(k in text for k in KEYWORDS):
        pass  # good
    # ensure experience is acceptable (fresher/trainee/<2 years)
    if any(a in text for a in ACCEPT_LOWER):
        return True

    # if explicit numeric experience > 2 years detected -> reject
    # matches patterns like "3 year", "4 years", "5+"
    if re.search(r"\b([3-9]|[1-9]\d)\+?\s*(year|years|yrs|yr)\b", text):
        return False

    # fallback: if nothing about experience mentioned, be conservative and accept only if 'intern'/'fresher' present
    return any(a in text for a in ACCEPT_LOWER)

def normalize_job(job):
    # ensure keys and strip spaces
    return {
        "title": job.get("title","").strip(),
        "company": job.get("company","").strip(),
        "link": job.get("link","").strip()
    }

def dedupe_jobs(jobs):
    seen = set()
    unique = []
    for j in jobs:
        title = j.get("title","").lower()
        comp = j.get("company","").lower()
        link = j.get("link","")
        key = (title, comp, link)
        if key in seen:
            continue
        seen.add(key)
        unique.append(j)
    return unique

# -------------------------
# Site-specific fetchers
# (best-effort selectors; tweak after running for each portal)
# -------------------------

def fetch_infopark_jobs(pages=3):
    jobs = []
    for page in range(1, pages+1):
        url = f"https://infopark.in/companies/job-search?page={page}"
        try:
            driver.get(url); time.sleep(1)
            soup = BeautifulSoup(driver.page_source, "html.parser")
            rows = soup.select("table tr")[1:]
            for row in rows:
                cols = row.find_all("td")
                if len(cols) < 3:
                    continue
                title = cols[1].get_text(strip=True)
                company = cols[2].get_text(strip=True)
                link_el = row.find("a", href=True)
                job_link = link_el["href"] if link_el else ""
                if job_link and not job_link.startswith("http"):
                    job_link = "https://infopark.in" + job_link
                if looks_relevant(title):
                    jobs.append({"title": title, "company": company, "link": job_link})
        except Exception as e:
            print(f"⚠️ Infopark fetch error page {page}: {e}")
    return jobs

def fetch_technopark_jobs(pages=3):
    jobs = []
    # Technopark site structure can vary; using table fallback similar to Infopark
    for page in range(1, pages+1):
        url = f"https://technopark.in/job-search?page={page}"
        try:
            driver.get(url); time.sleep(1)
            soup = BeautifulSoup(driver.page_source, "html.parser")
            # try multiple selector patterns
            rows = soup.select("table tr")
            if not rows or len(rows) <= 1:
                # fallback: look for list items/cards
                rows = soup.select("div.job, li.job, .job-card, .career-item")
            for row in rows[1:]:
                title = ""
                company = ""
                link = ""
                # try td pattern
                if row.name == "tr":
                    cols = row.find_all("td")
                    if len(cols) >= 3:
                        title = cols[1].get_text(strip=True)
                        company = cols[2].get_text(strip=True)
                        a = row.find("a", href=True)
                        link = a["href"] if a else ""
                else:
                    # card/list style
                    title_el = row.select_one("h2, h3, .title, .job-title, a")
                    comp_el = row.select_one(".company, .company-name")
                    a = row.find("a", href=True)
                    title = title_el.get_text(strip=True) if title_el else ""
                    company = comp_el.get_text(strip=True) if comp_el else ""
                    link = a["href"] if a else ""
                if link and not link.startswith("http"):
                    link = urllib.parse.urljoin(url, link)
                if title and looks_relevant(title):
                    jobs.append({"title": title, "company": company or "Technopark", "link": link})
        except Exception as e:
            print(f"⚠️ Technopark fetch error page {page}: {e}")
    return jobs

def fetch_cyberpark_jobs(pages=3):
    jobs = []
    # Cyberpark (Kozhikode) and similar sites often use cards
    for page in range(1, pages+1):
        url = f"https://cyberparks.in/careers?page={page}"
        try:
            driver.get(url); time.sleep(1)
            soup = BeautifulSoup(driver.page_source, "html.parser")
            # try common patterns
            cards = soup.select(".job-card, .career-card, .job, li.job, .listing")
            if not cards:
                cards = soup.select("a[href*='career'], a[href*='job'], .job-listing")
            for c in cards:
                title_el = c.select_one("h3, h2, .job-title, a")
                comp_el = c.select_one(".company, .company-name")
                a = c.find("a", href=True)
                title = title_el.get_text(strip=True) if title_el else c.get_text(strip=True)[:120]
                company = comp_el.get_text(strip=True) if comp_el else "Cyberpark"
                link = a["href"] if a else ""
                if link and not link.startswith("http"):
                    link = urllib.parse.urljoin(url, link)
                if title and looks_relevant(title):
                    jobs.append({"title": title, "company": company, "link": link})
        except Exception as e:
            print(f"⚠️ Cyberpark fetch error page {page}: {e}")
    return jobs

def fetch_smartcity_jobs(pages=3):
    jobs = []
    # SmartCity Kochi careers page often uses list/cards — fallback generic parsing
    base = "https://smartcitykochi.in"
    for page in range(1, pages+1):
        url = f"{base}/careers"
        try:
            driver.get(url); time.sleep(1)
            soup = BeautifulSoup(driver.page_source, "html.parser")
            cards = soup.select(".career-listing, .job-card, .vacancy, li, .career-item")
            for c in cards:
                # find anchor with job text
                a = c.find("a", href=True)
                title = a.get_text(strip=True) if a else (c.select_one("h3,h2,.title").get_text(strip=True) if c.select_one("h3,h2,.title") else "")
                company = "SmartCity Kochi"
                link = a["href"] if a else ""
                if link and not link.startswith("http"):
                    link = urllib.parse.urljoin(base, link)
                if title and looks_relevant(title):
                    jobs.append({"title": title, "company": company, "link": link})
        except Exception as e:
            print(f"⚠️ SmartCity fetch error: {e}")
    return jobs

def fetch_tidelpark_jobs(pages=3):
    jobs = []
    # TIDEL Park (Chennai) — some parks have 'career' or 'company list' pages; fallback generic
    base = "https://www.tidelpark.com"
    try:
        url = f"{base}/careers"
        driver.get(url); time.sleep(1)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        cards = soup.select("a[href*='career'], .career-listing, .job, li")
        for c in cards:
            a = c.find("a", href=True) if hasattr(c, "find") else None
            title = a.get_text(strip=True) if a else (c.get_text(strip=True)[:120] if c else "")
            company = "TIDEL Park"
            link = a["href"] if a else ""
            if link and not link.startswith("http"):
                link = urllib.parse.urljoin(base, link)
            if title and looks_relevant(title):
                jobs.append({"title": title, "company": company, "link": link})
    except Exception as e:
        print(f"⚠️ TIDEL fetch error: {e}")
    return jobs

def fetch_stpi_jobs(pages=2):
    jobs = []
    # STPI centers are many - try generic STPI careers pages or postings hub
    base = "https://www.stpi.in"
    try:
        url = f"{base}/career"
        driver.get(url); time.sleep(1)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        cards = soup.select(".career, .job, a[href*='career'], li")
        for c in cards:
            a = c.find("a", href=True) if hasattr(c, "find") else None
            title = a.get_text(strip=True) if a else (c.get_text(strip=True)[:120] if c else "")
            company = "STPI"
            link = a["href"] if a else ""
            if link and not link.startswith("http"):
                link = urllib.parse.urljoin(base, link)
            if title and looks_relevant(title):
                jobs.append({"title": title, "company": company, "link": link})
    except Exception as e:
        print(f"⚠️ STPI fetch error: {e}")
    return jobs

# Generic "other parks" fetcher: attempts to fetch job-like links from a list of park URLs
def fetch_generic_park(url, pages=1):
    jobs = []
    try:
        driver.get(url); time.sleep(1)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        # look for links that include 'career' or 'job' in href or text
        anchors = soup.find_all("a", href=True)
        hits = []
        for a in anchors:
            href = a["href"].lower()
            text = a.get_text(" ", strip=True).lower()
            if "career" in href or "job" in href or "vacancy" in href or "careers" in href:
                hits.append((a["href"], a.get_text(strip=True)))
        # Visit discovered career pages and parse job cards or anchors
        for href, text in hits[:6]:  # limit number of discovered pages
            full = href if href.startswith("http") else urllib.parse.urljoin(url, href)
            try:
                driver.get(full); time.sleep(1)
                s2 = BeautifulSoup(driver.page_source, "html.parser")
                # find anchors that appear like job posts
                anchors2 = s2.find_all("a", href=True)
                for a2 in anchors2:
                    t = a2.get_text(strip=True)
                    if not t:
                        continue
                    if looks_relevant(t):
                        link = a2["href"]
                        if link and not link.startswith("http"):
                            link = urllib.parse.urljoin(full, link)
                        jobs.append({"title": t, "company": url.replace("https://","").split("/")[0], "link": link})
            except Exception:
                pass
    except Exception as e:
        print(f"⚠️ Generic park fetch error for {url}: {e}")
    return jobs

# -------------------------
# Combine all fetchers
# -------------------------
def fetch_all_jobs():
    jobs = []
    # Kerala parks
    jobs.extend(fetch_infopark_jobs(pages=3))
    jobs.extend(fetch_technopark_jobs(pages=3))
    jobs.extend(fetch_cyberpark_jobs(pages=3))
    jobs.extend(fetch_smartcity_jobs(pages=2))

    # Major India parks / hubs (best-effort)
    jobs.extend(fetch_tidelpark_jobs(pages=1))
    jobs.extend(fetch_stpi_jobs(pages=1))

    # Generic attempts for major IT hubs (use official park/home pages)
    GENERIC_PARK_URLS = [
        "https://www.greaternoidaauthority.in",        # example; many hubs will not host job pages
        "https://www.hitechcity.org",                  # placeholder for Hyderabad tech hub
        "https://www.bengaluruitpark.in",              # placeholder
        # NOTE: these are placeholders; replace with actual park domains you want to target
    ]
    for g in GENERIC_PARK_URLS:
        jobs.extend(fetch_generic_park(g))

    # Deduplicate and normalize
    jobs = [normalize_job(j) for j in jobs if j.get("title")]
    jobs = dedupe_jobs(jobs)
    return jobs

# -------------------------
# EMAIL - KEEP YOUR ORIGINAL PRE-SETTINGS (unchanged)
# I will reuse the exact send_email you gave earlier (preserve formatting & env usage)
# -------------------------
def send_email(jobs):
    sender = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASS")
    recipients = [x.strip() for x in os.getenv("EMAIL_TO", "").split(",") if x.strip()]

    # 🧩 Debug: Read and clean STUDENT_NAMES from GitHub
    raw_names = os.getenv("STUDENT_NAMES", "")
    print(f"🧩 Raw STUDENT_NAMES from GitHub → '{raw_names}'")

    student_names = [
        x.strip() for x in raw_names.replace("\r", "")
        .replace("\n", "")
        .replace(" ,", ",")
        .replace(", ", ",")
        .split(",") if x.strip()
    ]
    print(f"✅ Parsed student_names → {student_names}")

    tracker_url = os.getenv("TRACKER_URL")

    # ✅ Subject line
    subject = f"Acadeno Technologies | Latest Kerala IT Park Jobs – {datetime.now().strftime('%d %b %Y')}"
    logo_url = "https://drive.google.com/uc?export=view&id=1wLdjI3WqmmeZcCbsX8aADhP53mRXthtB"

    # ✅ Validate counts
    if len(student_names) != len(recipients):
        print(f"⚠️ Warning: STUDENT_NAMES count ({len(student_names)}) does not match EMAIL_TO count ({len(recipients)}).")
        print("Continuing with available names (matching by index)...\n")

    for index, student_email in enumerate(recipients):
        # ✅ Safely get student name or fallback
        student_name = student_names[index] if index < len(student_names) else "Student"

        # ---- EMAIL BODY ----
        html = f"""
        <html>
        <body style="font-family:Arial, sans-serif; background:#f4f8f5; padding:25px; line-height:1.6;">

        <!-- HEADER -->
        <div style="background:linear-gradient(90deg, #5B00C2, #FF6B00); padding:25px; border-radius:15px; color:white; text-align:center;">
            <img src="{logo_url}" alt="Acadeno Logo" style="width:120px; height:auto; margin-bottom:12px; border-radius:10px;">
            <h2 style="margin:0; font-size:22px;">Acadeno Technologies Private Limited</h2>
            <p style="margin:5px 0; font-size:14px;">
                4437, First Floor, AVS Tower, Opp. Jayalakshmi Silks, Kallai Road, Calicut, 673002, Kerala
            </p>
        </div>

        <!-- BODY -->
        <div style="background:white; padding:25px; border-radius:12px; margin-top:25px; box-shadow:0 2px 5px rgba(0,0,0,0.1);">
            <p>Dear <b style="color:#5B00C2;">{student_name}</b>,</p>

            <p>Every great career begins with a single step — a moment of courage, determination, and belief in yourself. 🌱</p>

            <p>At Acadeno Technologies, we believe that your journey matters as much as your destination. The opportunities before you are not just job openings — they are doors to your future, waiting for you to knock with confidence, curiosity, and commitment. 💡</p>

            <p><b>Remember:</b> You don’t need to be perfect to begin — you just need to begin.</p>

            <p>Every interview you attend, every resume you refine, and every challenge you face brings you one step closer to your goal. Growth happens when you step out of your comfort zone and trust your own potential.</p>

            <p>So take this chance, believe in your abilities, and give your best. The effort you put in today will become the story you’re proud to tell tomorrow. 🌟</p>

            <p>Your future is not waiting to happen — it’s waiting for you to make it happen.</p>

            <p>With best wishes,</p>
            <p><b>Team Acadeno Technologies Pvt. Ltd.</b></p>
        </div>

        <!-- JOB LISTINGS -->
        <div style="margin-top:30px;">
        """

        # ---- JOB CARDS ----
        for job in jobs:
            safe_link = urllib.parse.quote(job['link'], safe='')
            safe_title = urllib.parse.quote(job['title'], safe='')
            safe_email = urllib.parse.quote(student_email, safe='')

            tracking_link = f"{tracker_url}?email={safe_email}&job={safe_title}&link={safe_link}"

            html += f"""
            <div style="border:1px solid #ddd; border-radius:10px; padding:15px; background:#ffffff; margin-bottom:15px; box-shadow:0 1px 3px rgba(0,0,0,0.1);">
                <h3 style="color:#5B00C2; margin:0;">{job['title']}</h3>
                <p style="margin:6px 0;">🏢 {job['company']}</p>
                <a href="{tracking_link}" style="display:inline-block; background:linear-gradient(90deg, #FF6B00, #5B00C2); color:white; padding:10px 18px; text-decoration:none; border-radius:6px; font-weight:bold;">🔗 View & Apply</a>
            </div>
            """

        html += """
        </div>
        <p style="font-size:12px; color:#777; margin-top:35px; text-align:center;">
            Generated by Maitexa Job Tracker © 2025
        </p>
        </body>
        </html>
        """

        # ---- SEND EMAIL ----
        msg = MIMEMultipart("alternative")
        msg["From"] = sender
        msg["To"] = student_email
        msg["Subject"] = subject
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender, password)
            server.send_message(msg)

        print(f"✅ Email sent to {student_name} ({student_email})")

# -------------------------
# MAIN
# -------------------------
if __name__ == "__main__":
    try:
        jobs = fetch_all_jobs()
    except Exception as e:
        print("Fatal scraping error:", e)
        jobs = []
    finally:
        try:
            driver.quit()
        except Exception:
            pass

    if jobs:
        print(f"✅ Found {len(jobs)} matching jobs (deduped). Sample:")
        for j in jobs[:10]:
            print(f" - {j['title']} @ {j['company']} -> {j['link']}")
        # send email using your original function
        send_email(jobs)
    else:
        print("⚠️ No matching jobs found.")
