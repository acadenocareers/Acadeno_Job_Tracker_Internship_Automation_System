import os
import smtplib
import time
import urllib.parse
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# ---- CHROME SETUP ----
chrome_options = Options()
chrome_options.add_argument("headless")
chrome_options.add_argument("no-sandbox")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
time.sleep(1)

# ---- FILTERS ----
TECHNICAL_ROLES = [
    "data scientist", "data science", "data analyst", "machine learning", "ml", "ai",
    "python", "django", "flask", "full stack", "react", "angular", "vue", "javascript",
    "typescript", "intern", "trainee", "developer", "engineer"
]
EXCLUDE_ROLES = ["php", "laravel", "wordpress", "drupal", ".net", "c#", "java", "spring", "hibernate"]

# ---- SCRAPE INFOPARK ----
def fetch_infopark_jobs():
    jobs = []
    for page in range(1, 3):
        url = f"https://infopark.in/companies/job-search?page={page}"
        driver.get(url)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        rows = soup.select("table tr")[1:]
        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 3:
                continue
            title = cols[1].text.strip()
            company = cols[2].text.strip()
            link_el = row.find("a", href=True)
            job_link = link_el["href"] if link_el else ""
            if not job_link.startswith("http"):
                job_link = "https://infopark.in" + job_link
            if any(ex in title.lower() for ex in EXCLUDE_ROLES):
                continue
            if any(role in title.lower() for role in TECHNICAL_ROLES):
                jobs.append({"title": title, "company": company, "link": job_link})
    return jobs

# ---- EMAIL ----
def send_email(jobs):
    sender = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASS")
    recipients = [x.strip() for x in os.getenv("EMAIL_TO", "").split(",") if x.strip()]
    tracker_url = os.getenv("TRACKER_URL")

    # ✅ Update your subject here
    subject = f"🌟 Latest Kerala IT Park Jobs – {datetime.now().strftime('%d %b %Y')}"

    # ✅ Public logo URL (replace this with your hosted link)
    logo_url = "https://drive.google.com/uc?export=view&id=1wLdjI3WqmmeZcCbsX8aADhP53mRXthtB"  # Replace with your real uploaded logo URL

    for student_email in recipients:
        html = f"""
        <html>
        <body style="font-family:Arial, sans-serif; background:#f4f8f5; padding:25px; line-height:1.6;">

        <!-- HEADER SECTION -->
        <div style="background:linear-gradient(90deg, #5B00C2, #FF6B00); padding:25px; border-radius:15px; color:white; text-align:center;">
            <img src="{logo_url}" alt="Acadeno Logo" style="width:120px; height:auto; margin-bottom:12px; border-radius:10px;">
            <h2 style="margin:0; font-size:22px;">Acadeno Technologies Private Limited</h2>
            <p style="margin:5px 0; font-size:14px;">
                4437, First Floor, AVS Tower, Opp. Jayalakshmi Silks, Kallai Road, Calicut, 673002, Kerala
            </p>
        </div>

        <!-- BODY -->
        <div style="background:white; padding:25px; border-radius:12px; margin-top:25px; box-shadow:0 2px 5px rgba(0,0,0,0.1);">
            <p>Dear <b>{student_email}</b>,</p>

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

        # ---- Job Cards ----
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

        msg = MIMEMultipart("alternative")
        msg["From"] = sender
        msg["To"] = student_email
        msg["Subject"] = subject
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender, password)
            server.send_message(msg)

        print(f"✅ Email sent to: {student_email}")

# ---- MAIN ----
if __name__ == "__main__":
    jobs = fetch_infopark_jobs()
    driver.quit()
    if jobs:
        send_email(jobs)
    else:
        print("⚠️ No matching jobs found.")
