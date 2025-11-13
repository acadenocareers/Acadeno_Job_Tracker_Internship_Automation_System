# app.py
import os
import smtplib
import time
import re
import urllib.parse
import pandas as pd
import random
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
import google.generativeai as genai  # ✅ Added for Gemini API

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
# AI MOTIVATIONAL QUOTE
# -------------------------

def get_ai_quote():
    """
    Generate motivational quote using Gemini AI.
    Falls back to a static quote if API fails.
    """
    api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        print("⚠️ GOOGLE_API_KEY missing — using fallback quote.")
        return random.choice([
            "Believe in yourself — your hard work will shape your future. 🌟",
            "Success grows from the small steps you take every day. 🌱"
        ])

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")

        prompt = (
            "Generate one short motivational quote (1–2 sentences) related to career, confidence, growth, learning, "
            "and job seeking. Keep it friendly, simple, positive, no quotes around it, and add one emoji at the end."
        )

        response = model.generate_content(prompt)
        ai_text = response.text.strip()

        if not ai_text:
            raise Exception("Empty response from Gemini")

        return ai_text

    except Exception as e:
        print(f"⚠️ Gemini generation error: {e}")
        return "Your future is built by what you do today — keep moving forward. 🌿"

# -------------------------
# THE REST OF YOUR CODE (SCRAPERS + FILTERS)
# -------------------------
# I keep everything SAME — unchanged
# (your long scraper logic stays here EXACTLY as before)
# -------------------------

# ⚠️ I will not reprint the full scraper code here because you already pasted it above.
# Just keep it exactly as-is.
# The only modification needed was adding Gemini + calling get_ai_quote() in send_email()

# -------------------------
# EMAIL FUNCTION — UPDATED
# -------------------------
def send_email(jobs):
    sender = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASS")
    recipients = [x.strip() for x in os.getenv("EMAIL_TO", "").split(",") if x.strip()]

    raw_names = os.getenv("STUDENT_NAMES", "")
    student_names = [
        x.strip() for x in raw_names.replace("\r", "").replace("\n", "")
        .replace(" ,", ",").replace(", ", ",").split(",") if x.strip()
    ]

    tracker_url = os.getenv("TRACKER_URL")

    subject = f"Acadeno Technologies | Latest Jobs Updates – {datetime.now().strftime('%d %b %Y')}"
    logo_url = "https://drive.google.com/uc?export=view&id=1wLdjI3WqmmeZcCbsX8aADhP53mRXthtB"

    # ✅ Generate the AI motivational quote here
    quote = get_ai_quote()

    for index, student_email in enumerate(recipients):
        student_name = student_names[index] if index < len(student_names) else "Student"

        html = f"""
        <html>
        <body style="font-family:Arial, sans-serif; background:#f4f8f5; padding:25px; line-height:1.6;">

        <!-- HEADER -->
        <div style="background:linear-gradient(90deg, #5B00C2, #FF6B00); padding:25px; border-radius:15px; color:white; text-align:center;">
            <img src="{logo_url}" alt="Acadeno Logo" style="width:120px; margin-bottom:12px; border-radius:10px;">
            <h2 style="margin:0; font-size:22px;">Acadeno Technologies Private Limited</h2>
        </div>

        <!-- BODY -->
        <div style="background:white; padding:25px; border-radius:12px; margin-top:25px; box-shadow:0 2px 5px rgba(0,0,0,0.1);">
            <p>Dear <b style="color:#5B00C2;">{student_name}</b>,</p>

            <p style="font-size:16px; color:#333; margin-bottom:20px;">
                {quote}
            </p>

            <p>At Acadeno Technologies, we believe that every opportunity is a chance to grow — 
            to learn, adapt, and move closer to your dream career. 🌱</p>

            <p>Your journey might feel challenging at times, but remember: consistency, curiosity, 
            and confidence will always lead you forward. 💡</p>

            <p>Wishing you success in every application and every step you take.</p>

            <p><b>With best wishes,<br>Team Acadeno Technologies Pvt. Ltd.</b></p>
        </div>

        <div style="margin-top:20px;">
        """

        # JOB CARDS (unchanged)
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
        print(f"✅ Found {len(df)} matching jobs.")
        send_email(jobs)
    else:
        print("⚠️ No matching jobs found.")
