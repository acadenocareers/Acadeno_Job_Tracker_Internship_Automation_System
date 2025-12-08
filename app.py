# app.py
import os
import smtplib
import time
import re
import urllib.parse
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException, NoSuchElementException, TimeoutException
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# -------------------------
# CONFIG / SETUP
# -------------------------
# Selenium/Chrome options suitable for GitHub Actions
chrome_options = Options()
chrome_options.add_argument("headless")
chrome_options.add_argument("no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920,1080")
# optional: avoid images to speed up
chrome_prefs = {"profile.managed_default_content_settings.images": 2}
chrome_options.add_experimental_option("prefs", chrome_prefs)

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
time.sleep(1)

# -------------------------
# FILTERS
# -------------------------
EXCLUDE_KEYWORDS = [
    "php","laravel","wordpress","drupal",".net","c#","java","spring","hibernate",
    "senior","lead","manager","architect","director","principal","vp","head",
    "3 year","3 years","4 year","4 years","5 year","5 years","5+","6 year","6 years"
]
EXCLUDE_LOWER = [e.lower() for e in EXCLUDE_KEYWORDS]

PREFER_TERMS = [
    "fresher","freshers","intern","internship","trainee","entry level",
    "0-1","0 - 1","0-2","0 - 2","0 to 2","1 year","below 2","junior"
]
PREFER_LOWER = [p.lower() for p in PREFER_TERMS]

INCLUDE_TERMS = [
    "python","django","flask","fastapi","react","angular","vue","javascript","typescript",
    "full stack","backend","frontend","web developer","backend developer",
    "machine learning","ml","ai","artificial intelligence","deep learning",
    "data science","data scientist","data analyst","analytics","business intelligence",
    "power bi","tableau","excel","sql","dashboard","bi developer","data engineer",
    "nlp","llm","pandas","numpy","scikit-learn","tensorflow","pytorch","rest api","Data Analyst","Junior Data Analyst","Senior Data Analyst","Business Data Analyst",
"Business Analyst","Reporting Analyst","Data Reporting Analyst","Operations Analyst","Product Analyst","Marketing Analyst","Financial Analyst","BI Analyst / Business Intelligence Analyst","Data Quality Analyst","Data Visualization Analyst",
"Quantitative Analyst / Quant Analyst","Statistical Analyst","Data Science Analyst","Insights Analyst","Data Operations Analyst","Risk Analyst","Fraud Analyst","Workforce Analyst"
"Revenue Analyst","Research Analyst","Analytics Specialist","Decision Support Analyst","flutter",
    "dart",
    "flutter developer",
    "mobile developer",
    "android developer",
    "ios developer",
    "cross platform developer",
    "mobile app developer",

    # Flutter frameworks / tools
    "flutter bloc",
    "bloc pattern",
    "provider",
    "riverpod",
    "getx",
    "flutter mobx",
    "flutter cubit",
    "flutter hooks",
    "clean architecture flutter",

    # Backend API integration (common in Flutter roles)
    "rest api",
    "graphql",
    "firebase",
    "supabase",
    "appwrite",
    "backend integration",

    # Database keywords
    "sqlite",
    "hive",
    "moor",
    "isar",
    "shared preferences",

    # UI / UX keywords used in job posts
    "ui design",
    "ux",
    "material design",
    "responsive ui",
    "widget development",
    "state management",

    # Extra skills often expected
    "git",
    "github",
    "devops",
    "ci cd",
    "play store",
    "app store",
    "deployment",
    "version control",

    # Cloud integrations common in Flutter jobs
    "aws",
    "gcp",
    "google cloud",
    "azure",
    "cloud functions",

    # Testing
    "unit testing",
    "integration testing",
    "flutter test",
    "widget testing",

    # Other frontend/mobile tech often listed in job descriptions
    "react native",
    "kotlin",
    "swift",
    "java android",
    "objective c",

]

# Regex to detect high experience mentions (to be excluded)
HIGH_EXPERIENCE_RE = re.compile(r"\b([3-9]|[1-9]\d)\+?\s*(year|years|yrs|yr)\b", flags=re.IGNORECASE)

# -------------------------
# HELPERS: safety + scrolling + parsing
# -------------------------
def safe_get(url, wait_after=1.0):
    """Open URL with driver.get — return BeautifulSoup or None on failure."""
    try:
        driver.get(url)
        time.sleep(wait_after)
        return BeautifulSoup(driver.page_source, "html.parser")
    except WebDriverException as e:
        print(f"⚠️ Could not load {url}: {e}")
        return None

def scroll_page(pause=0.5, scrolls=6):
    """Scroll the page to trigger lazy loading (Selenium context)."""
    try:
        for _ in range(scrolls):
            driver.execute_script("window.scrollBy(0, document.body.scrollHeight);")
            time.sleep(pause)
    except Exception:
        pass

def text_clean(s):
    return (s or "").strip()

def looks_relevant(title, snippet=""):
    text = f"{title} {snippet}".lower()

    # exclude if explicit exclude tokens present
    if any(ex in text for ex in EXCLUDE_LOWER):
        return False

    # must contain at least one include term
    if not any(term in text for term in INCLUDE_TERMS):
        return False

    # explicit high experience -> exclude
    if re.search(HIGH_EXPERIENCE_RE, text):
        return False

    # exclude managerial words
    if re.search(r"\b(senior|lead|manager|director|principal|head|vp)\b", text):
        return False

    # prefer fresher/trainee terms but not mandatory
    if any(p in text for p in PREFER_LOWER):
        return True

    # otherwise accept general relevant roles (non-senior)
    return True

def normalize_job(job):
    return {
        "title": text_clean(job.get("title","")),
        "company": text_clean(job.get("company","")),
        "link": text_clean(job.get("link",""))
    }

def dedupe_jobs(jobs):
    seen = set()
    unique = []
    for j in jobs:
        key = (j.get("title","").lower(), j.get("company","").lower())
        if key not in seen:
            seen.add(key)
            unique.append(j)
    return unique

# -------------------------
# SITE-SPECIFIC SCRAPERS
# Note: Many sites change UI frequently. These are robust, best-effort scrapers.
# -------------------------

# 1) Infopark (Kerala)
def fetch_infopark_jobs(pages=5):
    jobs = []
    for page in range(1, pages+1):
        url = f"https://infopark.in/companies/job-search?page={page}"
        soup = safe_get(url, wait_after=1.2)
        if not soup:
            continue
        rows = soup.select("table tr")
        if not rows:
            # fallback: anchors
            anchors = soup.find_all("a", href=True)
            for a in anchors:
                t = a.get_text(strip=True)
                if looks_relevant(t):
                    link = a['href']
                    if not link.startswith("http"):
                        link = urllib.parse.urljoin(url, link)
                    jobs.append({"title": t, "company": "Infopark", "link": link})
            continue
        for row in rows[1:]:
            cols = row.find_all("td")
            if len(cols) < 3:
                continue
            title = cols[1].get_text(strip=True)
            company = cols[2].get_text(strip=True)
            a = row.find("a", href=True)
            link = a["href"] if a else ""
            if link and not link.startswith("http"):
                link = urllib.parse.urljoin(url, link)
            if looks_relevant(title):
                jobs.append({"title": title, "company": company or "Infopark", "link": link})
    return jobs

# 2) Technopark (Kerala)
def fetch_technopark_jobs(pages=5):
    jobs = []
    for page in range(1, pages+1):
        url = f"https://technopark.in/job-search?page={page}"
        soup = safe_get(url, wait_after=1.2)
        if not soup:
            continue
        rows = soup.select("table tr")
        if rows and len(rows) > 1:
            for row in rows[1:]:
                cols = row.find_all("td")
                if len(cols) < 3:
                    continue
                title = cols[1].get_text(strip=True)
                company = cols[2].get_text(strip=True)
                a = row.find("a", href=True)
                link = a["href"] if a else ""
                if link and not link.startswith("http"):
                    link = urllib.parse.urljoin(url, link)
                if looks_relevant(title):
                    jobs.append({"title": title, "company": company or "Technopark", "link": link})
        else:
            # fallback: find possible job tiles
            anchors = soup.find_all("a", href=True)
            for a in anchors:
                t = a.get_text(strip=True)
                if looks_relevant(t):
                    link = a['href']
                    if link and not link.startswith("http"):
                        link = urllib.parse.urljoin(url, link)
                    jobs.append({"title": t, "company": "Technopark", "link": link})
    return jobs

# 3) Cyberpark (Kozhikode)
def fetch_cyberpark_jobs():
    jobs = []
    url = "https://cyberparks.in/careers"
    soup = safe_get(url, wait_after=1.2)
    if not soup:
        return jobs
    # find likely anchors/cards
    anchors = soup.select("a[href*='job'], a[href*='career'], .job, .career, .vacancy, .job-card")
    if not anchors:
        anchors = soup.find_all("a", href=True)
    for a in anchors:
        t = a.get_text(strip=True)
        if not t:
            continue
        link = a['href']
        if link and not link.startswith("http"):
            link = urllib.parse.urljoin(url, link)
        if looks_relevant(t):
            jobs.append({"title": t, "company": "Cyberpark", "link": link})
    return jobs

# 4) SmartCity Kochi
def fetch_smartcity_jobs():
    jobs = []
    url = "https://smartcitykochi.in/careers"
    soup = safe_get(url, wait_after=1.2)
    if not soup:
        return jobs
    anchors = soup.select("a[href*='job'], a[href*='career'], .vacancy, .career-item, .job-card")
    if not anchors:
        anchors = soup.find_all("a", href=True)
    for a in anchors:
        t = a.get_text(strip=True)
        if not t: continue
        link = a['href']
        if link and not link.startswith("http"):
            link = urllib.parse.urljoin(url, link)
        if looks_relevant(t):
            jobs.append({"title": t, "company": "SmartCity Kochi", "link": link})
    return jobs

# 5) TIDEL Park (Chennai)
def fetch_tidelpark_jobs():
    jobs = []
    url = "https://www.tidelpark.com/careers"
    soup = safe_get(url, wait_after=1.2)
    if not soup:
        return jobs
    anchors = soup.select("a[href*='career'], a[href*='job'], .career, .vacancy")
    for a in anchors:
        t = a.get_text(strip=True)
        if not t: continue
        link = a['href']
        if link and not link.startswith("http"):
            link = urllib.parse.urljoin(url, link)
        if looks_relevant(t):
            jobs.append({"title": t, "company": "TIDEL Park Chennai", "link": link})
    return jobs

# 6) STPI (India)
def fetch_stpi_jobs():
    jobs = []
    url = "https://www.stpi.in/career"
    soup = safe_get(url, wait_after=1.2)
    if not soup:
        return jobs
    anchors = soup.select("a[href*='career'], a[href*='job'], .vacancy, .career")
    for a in anchors:
        t = a.get_text(strip=True)
        if not t: continue
        link = a['href']
        if link and not link.startswith("http"):
            link = urllib.parse.urljoin(url, link)
        if looks_relevant(t):
            jobs.append({"title": t, "company": "STPI India", "link": link})
    return jobs

# 7) Bengaluru parks — generic approach: Manyata / ITPB / Embassy / Ecospace (public pages vary)
def fetch_bengaluru_generic(url):
    jobs = []
    soup = safe_get(url, wait_after=1.2)
    if not soup:
        return jobs
    # find career/job links
    anchors = soup.find_all("a", href=True)
    for a in anchors:
        href = a['href']
        text = a.get_text(strip=True)
        if not text: continue
        if "career" in href.lower() or "job" in href.lower() or "career" in text.lower() or "vacancy" in text.lower():
            link = href if href.startswith("http") else urllib.parse.urljoin(url, href)
            # fetch that page and extract job anchors
            s2 = safe_get(link, wait_after=1.0)
            if not s2: continue
            for a2 in s2.find_all("a", href=True):
                t2 = a2.get_text(strip=True)
                if not t2: continue
                if looks_relevant(t2):
                    link2 = a2['href']
                    if not link2.startswith("http"):
                        link2 = urllib.parse.urljoin(link, link2)
                    jobs.append({"title": t2, "company": url.split("//")[-1].split("/")[0], "link": link2})
    return jobs

# 8) Indeed (India) — search-based
def fetch_indeed_jobs(query_terms=None, pages=3):
    jobs = []
    if query_terms is None:
        query_terms = ["python", "data analyst", "data scientist", "machine learning", "react", "full stack"]
    base_query = "+".join([urllib.parse.quote_plus(q) for q in query_terms])
    for page in range(0, pages):
        start = page * 10
        url = f"https://www.indeed.co.in/jobs?q={base_query}&l=India&start={start}"
        try:
            driver.get(url)
            time.sleep(2)
            scroll_page(pause=0.7, scrolls=5)
            soup = BeautifulSoup(driver.page_source, "html.parser")
            cards = soup.select("a[data-jk], .job_seen_beacon, .result")
            if not cards:
                cards = soup.select("a[href*='/rc/clk']")
            for c in cards:
                # try multiple ways to obtain title/company/link
                title = ""
                company = ""
                link = ""
                try:
                    title_el = c.select_one("h2.jobTitle, .jobTitle, .title")
                    if title_el:
                        title = title_el.get_text(strip=True)
                except Exception:
                    title = c.get_text(strip=True)[:120]
                # company
                comp_el = c.select_one(".companyName, .company")
                if comp_el:
                    company = comp_el.get_text(strip=True)
                # link
                if c.has_attr("data-jk"):
                    link = f"https://www.indeed.co.in/viewjob?jk={c['data-jk']}"
                elif c.has_attr("href"):
                    link = c["href"]
                    if not link.startswith("http"):
                        link = urllib.parse.urljoin(url, link)
                if not title:
                    title = c.get_text(strip=True)[:120]
                if looks_relevant(title, company):
                    jobs.append({"title": title, "company": company or "Indeed", "link": link})
        except Exception as e:
            print(f"⚠️ Indeed fetch error page {page}: {e}")
            continue
    return jobs

# 9) Naukri (India) — search-based
def fetch_naukri_jobs(query_terms=None, pages=3):
    jobs = []
    if query_terms is None:
        query_terms = ["python", "data analyst", "data scientist", "machine learning", "react", "full stack"]
    base_query = "%20".join([urllib.parse.quote_plus(q) for q in query_terms])
    for page in range(1, pages+1):
        url = f"https://www.naukri.com/{base_query}-jobs-{page}"
        try:
            driver.get(url)
            time.sleep(2)
            scroll_page(pause=0.7, scrolls=4)
            soup = BeautifulSoup(driver.page_source, "html.parser")
            cards = soup.select(".jobTuple, .jobTuple .title, .jobCard, .list")
            if not cards:
                cards = soup.find_all("a", href=True)
            for c in cards:
                title = c.get_text(strip=True)[:140]
                # try to find company nearby
                # often company is in .company or .orgName
                company = ""
                comp_el = c.select_one(".company, .orgName, .companyName")
                if comp_el:
                    company = comp_el.get_text(strip=True)
                link = ""
                if c.name == "a" and c.has_attr("href"):
                    link = c["href"]
                if link and not link.startswith("http"):
                    link = urllib.parse.urljoin(url, link)
                if looks_relevant(title, company):
                    jobs.append({"title": title, "company": company or "Naukri", "link": link})
        except Exception as e:
            print(f"⚠️ Naukri fetch error page {page}: {e}")
            continue
    return jobs

# 10) LinkedIn (best-effort — may be blocked)
def fetch_linkedin_jobs(query_terms=None, pages=2):
    """
    Best-effort. LinkedIn blocks scraping aggressively.
    This function searches LinkedIn jobs page for the query — it may return empty or require login.
    Use responsibly; consider LinkedIn API instead if you need reliable results.
    """
    jobs = []
    if query_terms is None:
        query_terms = ["python", "data analyst", "data scientist", "machine learning", "react", "full stack"]
    q = "%20".join([urllib.parse.quote_plus(q) for q in query_terms])
    for page in range(0, pages):
        start = page * 25
        url = f"https://www.linkedin.com/jobs/search?keywords={q}&location=India&start={start}"
        try:
            driver.get(url)
            time.sleep(2.0)
            scroll_page(pause=0.7, scrolls=6)
            soup = BeautifulSoup(driver.page_source, "html.parser")
            cards = soup.select(".result-card__contents, .jobs-search-results__list-item, .base-search-card__info")
            for c in cards:
                title_el = c.select_one("h3, .base-search-card__title")
                comp_el = c.select_one("h4, .base-search-card__subtitle")
                link_el = c.find("a", href=True)
                title = title_el.get_text(strip=True) if title_el else c.get_text(strip=True)[:120]
                company = comp_el.get_text(strip=True) if comp_el else ""
                link = link_el["href"] if link_el and link_el.has_attr("href") else ""
                if link and not link.startswith("http"):
                    link = urllib.parse.urljoin(url, link)
                if looks_relevant(title, company):
                    jobs.append({"title": title, "company": company or "LinkedIn", "link": link})
        except Exception as e:
            print(f"⚠️ LinkedIn fetch error (may be blocked): {e}")
            break
    return jobs

# -------------------------
# MASTER FETCH (All sources)
# -------------------------
def fetch_all_jobs():
    all_jobs = []
    print("🌀 Starting multi-source scraping...")

    # Kerala parks
    all_jobs += fetch_infopark_jobs(pages=6)
    all_jobs += fetch_technopark_jobs(pages=6)
    all_jobs += fetch_cyberpark_jobs()
    all_jobs += fetch_smartcity_jobs()

    # Major hubs
    all_jobs += fetch_tidelpark_jobs()
    all_jobs += fetch_stpi_jobs()

    # Bangalore—attempts using known resource pages (Manyata/ITPB/Ecospace may not host centralized job lists)
    bgl_urls = [
        # Replace/extend with actual hub pages you want to target
        "https://manyata.com",      # placeholder/fallback
        "https://itpbengaluru.org", # placeholder
        "https://www.embassymanyata.com"  # placeholder
    ]
    for u in bgl_urls:
        try:
            all_jobs += fetch_bengaluru_generic(u)
        except Exception as e:
            print(f"⚠️ Bangalore generic fetch failed for {u}: {e}")

    # Big job portals (search-based)
    all_jobs += fetch_indeed_jobs(query_terms=["python", "data analyst", "data scientist", "machine learning", "react"], pages=4)
    all_jobs += fetch_naukri_jobs(query_terms=["python", "data analyst", "data scientist", "machine learning", "react"], pages=3)
    # LinkedIn best-effort
    all_jobs += fetch_linkedin_jobs(query_terms=["python", "data analyst", "data scientist", "machine learning", "react"], pages=1)

    # Normalize and dedupe
    all_jobs = [normalize_job(j) for j in all_jobs if j.get("title")]
    all_jobs = dedupe_jobs(all_jobs)
    print(f"✅ Scraping complete — unique jobs found: {len(all_jobs)}")
    return all_jobs

# -------------------------
# EMAIL (unchanged; preserve your original styling & env usage)
# -------------------------
def send_email(jobs):
    sender = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASS")
    recipients = [x.strip() for x in os.getenv("EMAIL_TO", "").split(",") if x.strip()]

    # Read STUDENT_NAMES from secrets/env
    raw_names = os.getenv("STUDENT_NAMES", "")
    student_names = [
        x.strip() for x in raw_names.replace("\r", "")
        .replace("\n", "")
        .replace(" ,", ",")
        .replace(", ", ",")
        .split(",") if x.strip()
    ]
    tracker_url = os.getenv("TRACKER_URL")

    subject = f"Acadeno Technologies | Latest Jobs Updates – {datetime.now().strftime('%d %b %Y')}"
    logo_url = "https://drive.google.com/uc?export=view&id=1wLdjI3WqmmeZcCbsX8aADhP53mRXthtB"

    if len(student_names) != len(recipients):
        print(f"⚠️ Warning: STUDENT_NAMES count ({len(student_names)}) != EMAIL_TO count ({len(recipients)}). Proceeding by index.")

    for index, student_email in enumerate(recipients):
        student_name = student_names[index] if index < len(student_names) else "Student"

        html = f"""
        <html>
        <body style="font-family:Arial, sans-serif; background:#f4f8f5; padding:25px; line-height:1.6;">

        <!-- HEADER -->
        <div style="background:linear-gradient(90deg, #5B00C2, #FF6B00); padding:25px; border-radius:15px; color:white; text-align:center;">
            <img src="{logo_url}" alt="Acadeno Logo" style="width:120px; height:auto; margin-bottom:12px; border-radius:10px;">
            <h2 style="margin:0; font-size:22px;">Acadeno Technologies Private Limited</h2>
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
        <!-- JOB LIST -->
        <div style="margin-top:20px;">
        """

        # Add job cards
        for job in jobs:
            safe_link = urllib.parse.quote(job['link'], safe='')
            safe_title = urllib.parse.quote(job['title'], safe='')
            safe_email = urllib.parse.quote(student_email, safe='')
            tracking_link = f"{tracker_url}?email={safe_email}&job={safe_title}&link={safe_link}"

            html += f"""
            <div style="border:1px solid #ddd; border-radius:10px; padding:15px; background:#ffffff; margin-bottom:12px;">
                <h3 style="color:#5B00C2; margin:0;">{job['title']}</h3>
                <p style="margin:6px 0;">🏢 {job['company']}</p>
                <a href="{tracking_link}" style="display:inline-block; background:linear-gradient(90deg,#FF6B00,#5B00C2); color:white; padding:8px 14px; text-decoration:none; border-radius:6px; font-weight:bold;">🔗 View & Apply</a>
            </div>
            """

        html += f"""
        </div>
        <p style="font-size:12px; color:#777; margin-top:25px; text-align:center;">
            Generated by Maitexa Job Tracker © {datetime.now().year}
        </p>
        </body>
        </html>
        """

        # Send mail
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
    finally:
        try:
            driver.quit()
        except Exception:
            pass

    if jobs:
        # Save CSV for record (GitHub Actions runner artifact if you upload it)
        df = pd.DataFrame(jobs)
        df.drop_duplicates(subset=["title","company"], inplace=True)
        df.to_csv("jobs.csv", index=False)
        print(f"✅ Found {len(df)} matching jobs. Saved to jobs.csv.")
        # Send email (keeps your original mail settings)
        send_email(jobs)
    else:
        print("⚠️ No matching jobs found.")