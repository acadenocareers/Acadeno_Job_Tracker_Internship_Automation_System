import time
import re
import os
import smtplib
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

# ---- CHROME CONFIG ----
chrome_options = Options()
chrome_options.add_argument("headless")
chrome_options.add_argument("disable-gpu")
chrome_options.add_argument("no-sandbox")
chrome_options.add_argument("disable-dev-shm-usage")
chrome_options.add_argument(
    "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
)

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
time.sleep(1)

# ---- JOB FILTERS ----
TECHNICAL_ROLES = [
    "data scientist", "data science", "data analyst", "machine learning", "ml", "ai",
    "python", "django", "flask", "full stack", "react", "angular", "vue", "javascript",
    "typescript", "intern", "trainee", "developer", "engineer"
]
EXCLUDE_ROLES = ["php", "laravel", "wordpress", "drupal", ".net", "c#", "java", "spring", "hibernate"]

# ---- SCRAPE INFOPARK JOBS ----
def fetch_infopark_jobs():
    print("Fetching jobs from Infopark...")
    jobs = []
    page = 1
    while page <= 5:
        url = f"https://infopark.in/companies/job-search?page={page}"
        try:
            driver.get(url)
            time.sleep(2)
        except Exception as e:
            print(f"⚠️ Failed to load {url}: {e}")
            page += 1
            continue

        soup = BeautifulSoup(driver.page_source, "html.parser")
        table = soup.find("table")
        if not table:
            break
        rows = table.find_all("tr")[1:]
        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 3:
                continue
            date = cols[0].text.strip()
            title = cols[1].text.strip()
            company = cols[2].text.strip()
            link_element = row.find("a", href=True)
            job_link = f"https://infopark.in{link_element['href']}" if link_element else ""
            title_lower = title.lower()
            if any(ex in title_lower for ex in EXCLUDE_ROLES):
                continue
            if any(role in title_lower for role in TECHNICAL_ROLES):
                experience = "0–2 years" if "intern" not in title_lower else "Intern"
                jobs.append({
                    "title": title,
                    "company": company,
                    "experience": experience,
                    "date": date,
                    "location": "Infopark, Kochi",
                    "link": job_link
                })
        page += 1
    print(f"✅ Found {len(jobs)} technical jobs.")
    return jobs

# ---- SEND EMAIL ----
def send_email(jobs):
    sender = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASS")
    recipients = [x.strip() for x in os.getenv("EMAIL_TO", "").split(",") if x.strip()]
    tracker_url = os.getenv("TRACKER_URL")

    subject = f"🌟 Latest Kerala IT Park Jobs – {datetime.now().strftime('%d %b %Y')}"
    smtp_server = "smtp.gmail.com"
    smtp_port = 587

    for student_email in recipients:
        html_content = f"""
        <html>
        <body style="font-family: Arial; background: #f4f8f5; padding: 20px;">
            <div style="background: #007A33; padding: 15px; border-radius: 12px; color: white; text-align:center;">
                <h2>Maitexa Technologies Pvt Ltd</h2>
                <p style="margin: 0;">Integrating Minds | Kadannamanna, Kerala</p>
            </div><br>
            <p>Dear <strong>{student_email}</strong>,</p>
            <p>Here are the latest <b>Kerala IT Park job openings</b> for you:</p>
        """

        for job in jobs:
            tracking_link = f"{tracker_url}?email={student_email}&job={job['title']}&link={job['link']}"
            html_content += f"""
            <div style="border:1px solid #ccc; border-radius:10px; padding:15px; margin-bottom:15px; background:white;">
                <h3 style="color:#007A33; margin:0;">{job['title']}</h3>
                <p style="margin:5px 0;"><b>🏢 {job['company']}</b></p>
                <p style="margin:5px 0;">📍 {job['location']} | 💼 {job['experience']} | 📅 {job['date']}</p>
                <a href="{tracking_link}" style="display:inline-block; padding:8px 15px; background:#007A33; color:white; text-decoration:none; border-radius:6px;">View & Apply</a>
            </div>
            """

        html_content += """
            <p style="font-size:12px; color:#777;">Generated automatically by Maitexa Job Tracker © 2025</p>
        </body></html>
        """

        msg = MIMEMultipart("alternative")
        msg["From"] = f"Maitexa Technologies <{sender}>"
        msg["To"] = student_email
        msg["Subject"] = subject
        msg.attach(MIMEText(html_content, "html"))

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender, password)
            server.send_message(msg)

        print(f"✅ Sent job email to: {student_email}")

# ---- MAIN ----
def main():
    jobs = fetch_infopark_jobs()
    driver.quit()
    if jobs:
        send_email(jobs)
    else:
        print("⚠️ No matching jobs found.")

if __name__ == "__main__":
    main()
