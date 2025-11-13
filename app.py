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
# GEMINI AI QUOTE GENERATOR
# -------------------------
import google.generativeai as genai
import random

def get_ai_quote():
    api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        print("⚠️ GOOGLE_API_KEY missing — using fallback quote.")
        return random.choice([
            "Believe in yourself — your effort today builds your future. 🌟",
            "Every small step forward counts on your career journey. 🚀",
            "Success begins when you choose to try. Keep going! 💡"
        ])

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")

        prompt = (
            "Generate one short motivational quote (1–2 sentences) related to career, confidence, job search, growth, "
            "and learning. No quotation marks. Add one emoji."
        )

        response = model.generate_content(prompt)
        text = response.text.strip()

        if not text:
            raise Exception("Empty Gemini response")

        return text

    except Exception as e:
        print(f"⚠️ Gemini error: {e}")
        return "Your hard work is shaping a future you'll be proud of. 🌱"

# -------------------------
# CONFIG / SETUP
# -------------------------
chrome_options = Options()
chrome_options.add_argument("headless")
chrome_options.add_argument("no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920,1080")
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
    "nlp","llm","pandas","numpy","scikit-learn","tensorflow","pytorch","rest api"
]

HIGH_EXPERIENCE_RE = re.compile(r"\b([3-9]|[1-9]\d)\+?\s*(year|years|yrs|yr)\b", flags=re.IGNORECASE)

# -------------------------
# HELPERS
# -------------------------
def safe_get(url, wait_after=1.0):
    try:
        driver.get(url)
        time.sleep(wait_after)
        return BeautifulSoup(driver.page_source, "html.parser")
    except WebDriverException as e:
        print(f"⚠️ Could not load {url}: {e}")
        return None

def scroll_page(pause=0.5, scrolls=6):
    try:
        for _ in range(scrolls):
            driver.execute_script("window.scrollBy(0, document.body.scrollHeight);")
            time.sleep(pause)
    except:
        pass

def text_clean(s):
    return (s or "").strip()

def looks_relevant(title, snippet=""):
    text = f"{title} {snippet}".lower()

    if any(ex in text for ex in EXCLUDE_LOWER):
        return False

    if not any(term in text for term in INCLUDE_TERMS):
        return False

    if re.search(HIGH_EXPERIENCE_RE, text):
        return False

    if re.search(r"\b(senior|lead|manager|director|principal|head|vp)\b", text):
        return False

    if any(p in text for p in PREFER_LOWER):
        return True

    return True

def normalize_job(job):
    return {
        "title": text_clean(job.get("title","")),
        "company": text_clean(job.get("company","")),
        "link": text_clean(job.get("link",""))
    }

def dedupe_jobs(jobs):
    seen = set()
    final = []
    for j in jobs:
        k = (j.get("title","").lower(), j.get("company","").lower())
        if k not in seen:
            seen.add(k)
            final.append(j)
    return final

# -------------------------
# SCRAPERS (UNCHANGED)
# -------------------------
# (All your scrapers here exactly as before — unchanged.)
# I am pasting them as-is:

# 1) Infopark
def fetch_infopark_jobs(pages=5):
    jobs = []
    for page in range(1, pages+1):
        url = f"https://infopark.in/companies/job-search?page={page}"
        soup = safe_get(url, wait_after=1.2)
        if not soup:
            continue
        rows = soup.select("table tr")
        if not rows:
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

# 2) Technopark
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
            anchors = soup.find_all("a", href=True)
            for a in anchors:
                t = a.get_text(strip=True)
                if looks_relevant(t):
                    link = a['href']
                    if not link.startswith("http"):
                        link = urllib.parse.urljoin(url, link)
                    jobs.append({"title": t, "company": "Technopark", "link": link})
    return jobs

# 3) Cyberpark
def fetch_cyberpark_jobs():
    jobs = []
    url = "https://cyberparks.in/careers"
    soup = safe_get(url, wait_after=1.2)
    if not soup:
        return jobs
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

# 4) SmartCity
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

# 5) TIDEL
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

# 6) STPI
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

# 7) Bengaluru Generic
def fetch_bengaluru_generic(url):
    jobs = []
    soup = safe_get(url, wait_after=1.2)
    if not soup:
        return jobs
    anchors = soup.find_all("a", href=True)
    for a in anchors:
        href = a['href']
        text = a.get_text(strip=True)
        if not text: continue
        if "career" in href.lower() or "job" in href.lower() or "career" in text.lower() or "vacancy" in text.lower():
            link = href if href.startswith("http") else urllib.parse.urljoin(url, href)
            s2 = safe_get(link, wait_after=1.0)
            if not s2: continue
            for a2 in s2.find_all("a", href=True):
                t2 = a2.get_text(strip=True)
                if not t2: continue
                if looks_relevant(t2):
                    link2 = a2['href']
                    if not link2.startswith("http"):
                        link2 = urllib.parse.urljoin(link, link2)
                    jobs.append({
                        "title": t2,
                        "company": url.split("//")[-1].split("/")[0],
                        "link": link2
                    })
    return jobs

# 8) Indeed
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
                title = ""
                company = ""
                link = ""
                try:
                    title_el = c.select_one("h2.jobTitle, .jobTitle, .title")
                    if title_el:
                        title = title_el.get_text(strip=True)
                except:
                    title = c.get_text(strip=True)[:120]
                comp_el = c.select_one(".companyName, .company")
                if comp_el:
                    company = comp_el.get_text(strip=True)
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

# 9) Naukri
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

# 10) LinkedIn
def fetch_linkedin_jobs(query_terms=None, pages=2):
    jobs = []
    if query_terms is None:
        query_terms = ["python", "data analyst", "data scientist", "machine learning", "react", "full stack"]
    q = "%20".join([urllib.parse.quote_plus(q) for q in query_terms])
    for page in range(0, pages):
        start = page * 25
        url = f"https://www.linkedin.com/jobs/search?keywords={q}&location=India&start={start}"
        try:
            driver.get(url)
            time.sleep(2)
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
            print(f"⚠️ LinkedIn error: {e}")
            break
    return jobs

# -------------------------
# MASTER FETCH (UNCHANGED)
# -------------------------
def fetch_all_jobs():
    all_jobs = []
    print("🌀 Starting multi-source scraping...")

    all_jobs += fetch_infopark_jobs(pages=6)
    all_jobs += fetch_technopark_jobs(pages=6)
    all_jobs += fetch_cyberpark_jobs()
    all_jobs += fetch_smartcity_jobs()
    all_jobs += fetch_tidelpark_jobs()
    all_jobs += fetch_stpi_jobs()

    bgl_urls = [
        "https://manyata.com",
        "https://itpbengaluru.org",
        "https://www.embassymanyata.com"
    ]
    for u in bgl_urls:
        try:
            all_jobs += fetch_bengaluru_generic(u)
        except Exception as e:
            print(f"⚠️ Bangalore fetch failed: {e}")

    all_jobs += fetch_indeed_jobs(query_terms=["python", "data analyst", "data scientist", "machine learning", "react"], pages=4)
    all_jobs += fetch_naukri_jobs(query_terms=["python", "data analyst", "data scientist", "machine learning", "react"], pages=3)
    all_jobs += fetch_linkedin_jobs(query_terms=["python", "data analyst", "data scientist", "machine learning", "react"], pages=1)

    all_jobs = [normalize_job(j) for j in all_jobs if j.get("title")]
    all_jobs = dedupe_jobs(all_jobs)
    print(f"✅ Scraping complete — unique jobs found: {len(all_jobs)}")
    return all_jobs

# -------------------------
# EMAIL WITH AI QUOTE
# -------------------------
def send_email(jobs):
    sender = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASS")
    recipients = [x.strip() for x in os.getenv("EMAIL_TO", "").split(",") if x.strip()]

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
        print(f"⚠️ STUDENT_NAMES count does not match EMAIL_TO count.")

    for index, student_email in enumerate(recipients):

        student_name = student_names[index] if index < len(student_names) else "Student"

        # 🌟 NEW: AI MOTIVATIONAL QUOTE
        quote = get_ai_quote()

        html = f"""
        <html>
        <body style="font-family:Arial, sans-serif; background:#f4f8f5; padding:25px; line-height:1.6;">

        <div style="background:linear-gradient(90deg, #5B00C2, #FF6B00); padding:25px; border-radius:15px; color:white; text-align:center;">
            <img src="{logo_url}" alt="Acadeno Logo" style="width:120px; height:auto; margin-bottom:12px; border-radius:10px;">
            <h2 style="margin:0; font-size:22px;">Acadeno Technologies Private Limited</h2>
        </div>

        <div style="background:white; padding:25px; border-radius:12px; margin-top:25px; box-shadow:0 2px 5px rgba(0,0,0,0.1);">
            <p>Dear <b style="color:#5B00C2;">{student_name}</b>,</p>

            <p style="font-size:16px; color:#333; margin-bottom:20px;">
                {quote}
            </p>

            <p>At Acadeno Technologies, we believe in your journey — every application, every interview, and every effort you make is taking you closer to your dream career. 🌱</p>

            <p>Stay strong, stay consistent, and keep believing in your ability to grow. Opportunities appear for those who show up with courage. 💡</p>

            <p>Wishing you success in every step ahead.</p>

            <p><b>With best wishes,<br>Team Acadeno Technologies Pvt. Ltd.</b></p>
        </div>

        <div style="margin-top:20px;">
        """

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
        except:
            pass

    if jobs:
        df = pd.DataFrame(jobs)
        df.drop_duplicates(subset=["title","company"], inplace=True)
        df.to_csv("jobs.csv", index=False)
        print(f"✅ Found {len(df)} matching jobs. Saved to jobs.csv.")
        send_email(jobs)
    else:
        print("⚠️ No matching jobs found.")
