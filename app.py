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
from selenium.common.exceptions import WebDriverException
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# -------------------------
# GEMINI AI MOTIVATIONAL PARAGRAPH GENERATOR
# -------------------------
import google.generativeai as genai
import random

def get_ai_message(student_name="Student"):
    api_key = os.getenv("GOOGLE_API_KEY")

    # Fallback if no API key
    if not api_key:
        print("⚠️ GOOGLE_API_KEY missing — using fallback message.")
        return """
            <p>Every great career begins with a single decision — the decision to try. 🌱</p>
            <p>Your consistency and courage will take you far. Keep believing in your journey. 🚀</p>
        """

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")

        prompt = f"""
        Write a highly motivational, warm, inspiring message for a student named {student_name}.
        Format using clean HTML <p> tags.
        Length: 5–8 paragraphs.
        Include motivation about: job search, confidence, career building, learning, opportunities.
        Add emojis naturally.
        Do NOT add greeting and signature — ONLY the body paragraphs.
        Avoid repeating the same lines.
        """

        response = model.generate_content(prompt)
        text = response.text.strip()

        if not text:
            raise Exception("Empty Gemini response")

        return text

    except Exception as e:
        print(f"⚠️ Gemini error: {e}")
        return """
            <p>Your journey is unique, and every effort you make today builds a stronger tomorrow. 🌟</p>
            <p>Stay committed, stay curious, and trust the direction you're moving toward — success is closer than you think. 💡</p>
        """

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


# -------------------------------------------------------
# SCRAPERS — YOUR ORIGINAL SCRAPERS (UNCHANGED)
# -------------------------------------------------------
# ✨ All your scrapers below remain exactly the same
#   (Infopark, Technopark, Cyberpark, SmartCity, Tidel, STPI,
#    Bengaluru generic, Indeed, Naukri, LinkedIn)
# -------------------------------------------------------

# [SCRAPER CODE REMAINS THE SAME — NOT REPEATED HERE FOR LENGTH]
# ✨ I did NOT change your working scrapers. They are identical.


# -------------------------
# MASTER FETCH (UNCHANGED)
# -------------------------
# (kept exactly as yours — no changes)


# -------------------------
# EMAIL WITH AI MESSAGE
# -------------------------
def send_email(jobs):
    sender = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASS")
    recipients = [x.strip() for x in os.getenv("EMAIL_TO", "").split(",") if x.strip()]

    raw_names = os.getenv("STUDENT_NAMES", "")
    student_names = [
        x.strip() for x in raw_names.replace("\r","").replace("\n","").replace(" ,",",").replace(", ",",").split(",") if x.strip()
    ]

    tracker_url = os.getenv("TRACKER_URL")
    subject = f"Acadeno Technologies | Latest Jobs Updates – {datetime.now().strftime('%d %b %Y')}"
    logo_url = "https://drive.google.com/uc?export=view&id=1wLdjI3WqmmeZcCbsX8aADhP53mRXthtB"

    for index, student_email in enumerate(recipients):

        student_name = student_names[index] if index < len(student_names) else "Student"

        # 🌟 New long, unique Gemini message
        ai_message = get_ai_message(student_name)

        html = f"""
        <html>
        <body style="font-family:Arial, sans-serif; background:#f4f8f5; padding:25px; line-height:1.6;">

        <div style="background:linear-gradient(90deg, #5B00C2, #FF6B00); padding:25px; border-radius:15px; color:white; text-align:center;">
            <img src="{logo_url}" style="width:120px; margin-bottom:12px; border-radius:10px;">
            <h2 style="margin:0; font-size:22px;">Acadeno Technologies Private Limited</h2>
        </div>

        <div style="background:white; padding:25px; border-radius:12px; margin-top:25px;">
            <p>Dear <b style="color:#5B00C2;">{student_name}</b>,</p>

            {ai_message}

            <p><b>With best wishes,<br>Team Acadeno Technologies Pvt. Ltd.</b></p>
        </div>

        <div style="margin-top:20px;">
        """

        for job in jobs:
            safe_link = urllib.parse.quote(job["link"], safe='')
            safe_title = urllib.parse.quote(job["title"], safe='')
            safe_email = urllib.parse.quote(student_email, safe='')

            tracking_link = f"{tracker_url}?email={safe_email}&job={safe_title}&link={safe_link}"

            html += f"""
            <div style="border:1px solid #ddd; border-radius:10px; padding:15px; background:#ffffff; margin-bottom:12px;">
                <h3 style="color:#5B00C2; margin:0;">{job['title']}</h3>
                <p style="margin:6px 0;">🏢 {job['company']}</p>
                <a href="{tracking_link}" style="background:linear-gradient(90deg,#FF6B00,#5B00C2); color:white; padding:8px 14px; text-decoration:none; border-radius:6px;">
                    🔗 View & Apply
                </a>
            </div>
            """

        html += """
        </div>
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
