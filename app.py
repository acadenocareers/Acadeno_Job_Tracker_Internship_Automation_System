import time
import re
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
import os

# ---- CHROME CONFIG ----
chrome_options = Options()
chrome_options.add_argument("headless")
chrome_options.add_argument("disable-gpu")
chrome_options.add_argument("no-sandbox")
chrome_options.add_argument("disable-dev-shm-usage")
chrome_options.add_argument(
    "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
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

# ---- SCRAPE FROM INFOPARK ----
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
            job_link = ""
            if link_element:
                job_link = link_element["href"]
                if not job_link.startswith("http"):
                    job_link = f"https://infopark.in{job_link}"

            title_lower = title.lower()
            if any(ex in title_lower for ex in EXCLUDE_ROLES):
                continue
            if any(role in title_lower for role in TECHNICAL_ROLES):
                experience = "0–2 years" if "intern" not in title_lower else "Intern"
                jobs.append({
                    "park": "Infopark",
                    "title": title,
                    "company": company,
                    "experience": experience,
                    "date": date,
                    "location": "Infopark, Kochi",
                    "link": job_link
                })

        page += 1

    print(f"✅ Found {len(jobs)} filtered technical jobs from Infopark.")
    return jobs

# ---- GENERATE PDF BROCHURE ----
def generate_maitexa_brochure(jobs):
    if not jobs:
        print("No jobs to add to brochure.")
        return

    OUTPUT_FILE = os.path.join(os.getcwd(), "Maitexa_Green_Adjusted_Brochure.pdf")
    LOGO_PATH = "maitexa_logo.png"

    COMPANY_NAME = "MAITEXA TECHNOLOGIES PVT LTD"
    SLOGAN = "Integrating Minds"
    ADDRESS = "Kadannamanna, Malappuram, Kerala - 679324"
    EMAIL = "contact@maitexa.com"
    WEBSITE = "www.maitexa.com"

    LIGHT_GREEN = colors.Color(0.6, 0.8, 0.6)
    DARK_GREEN = colors.Color(0.0, 0.5, 0.3)
    WHITE = colors.white
    TEXT_COLOR = colors.HexColor("#003300")

    pdf = canvas.Canvas(OUTPUT_FILE, pagesize=A4)
    width, height = A4

    # ---- HEADER DESIGN ----
    def draw_header(pdf):
        pdf.setFillColor(LIGHT_GREEN)
        pdf.circle(-120, height + 50, 300, stroke=0, fill=1)
        pdf.setFillColor(DARK_GREEN)
        pdf.circle(width / 2, height + 100, 350, stroke=0, fill=1)

        def draw_text_with_shadow(text, font, size, x, y):
            pdf.setFont(font, size)
            pdf.setFillColor(colors.black)
            pdf.drawCentredString(x + 0.5, y - 0.5, text)
            pdf.setFillColor(WHITE)
            pdf.drawCentredString(x, y, text)

        draw_text_with_shadow(COMPANY_NAME, "Helvetica-Bold", 20, width / 2, height - 65)
        draw_text_with_shadow(SLOGAN, "Helvetica-Oblique", 12, width / 2, height - 82)

        pdf.setFont("Helvetica", 9)
        pdf.setFillColor(WHITE)
        pdf.drawCentredString(width / 2, height - 98, ADDRESS)
        pdf.drawCentredString(width / 2, height - 110, f"{EMAIL} | {WEBSITE}")

    # ---- WATERMARK ----
    def draw_watermark(pdf):
        if os.path.exists(LOGO_PATH):
            pdf.saveState()
            pdf.translate(width / 2 - 150, height / 2 - 150)
            pdf.setFillAlpha(0.18)
            pdf.drawImage(LOGO_PATH, 0, 0, width=300, height=300, mask='auto')
            pdf.restoreState()

    # ---- FOOTER CURVES ----
    def draw_footer(pdf):
        pdf.setFillColor(LIGHT_GREEN)
        pdf.circle(width - 200, -60, 300, stroke=0, fill=1)
        pdf.setFillColor(DARK_GREEN)
        pdf.circle(width + 100, -100, 300, stroke=0, fill=1)

    # ---- JOB BOXES ----
    def draw_jobs(pdf, jobs):
        y = height - 170
        job_box_height = 90
        for idx, job in enumerate(jobs, 1):
            if y < 130:
                pdf.showPage()
                draw_watermark(pdf)
                draw_header(pdf)
                draw_footer(pdf)
                y = height - 130

            pdf.setFillColor(WHITE)
            pdf.roundRect(80, y - job_box_height, width - 160, job_box_height, 10, stroke=1, fill=1)

            pdf.setFont("Helvetica-Bold", 12)
            pdf.setFillColor(TEXT_COLOR)
            pdf.drawString(100, y - 25, f"{idx}. {job['title']}")

            pdf.setFont("Helvetica", 10)
            pdf.drawString(110, y - 40, f"🏢 {job['company']}")
            pdf.drawString(110, y - 55, f"📍 {job['location']}")
            pdf.drawString(110, y - 70, f"💼 {job['experience']}  |  📅 {job['date']}")

            if job["link"]:
                pdf.setFillColor(colors.HexColor("#0033CC"))
                pdf.setFont("Helvetica-Bold", 10)
                pdf.drawString(110, y - 85, "🔗 Apply Job")
                pdf.linkURL(job["link"], (110, y - 90, width - 100, y - 75))
            else:
                pdf.setFillColor(colors.gray)
                pdf.drawString(110, y - 85, "No link available")

            y -= job_box_height + 25

    def draw_footer_text(pdf):
        pdf.setFont("Helvetica-Oblique", 9)
        pdf.setFillColor(TEXT_COLOR)
        pdf.drawCentredString(width / 2, 40, "Generated by Maitexa Job Tracker © 2025 | Infopark • Technopark • Cyberpark")

    draw_watermark(pdf)
    draw_header(pdf)
    draw_footer(pdf)
    draw_jobs(pdf, jobs)
    draw_footer_text(pdf)
    pdf.save()

    print(f"✅ Maitexa Brochure saved as: {OUTPUT_FILE}")

# ---- MAIN EXECUTION ----
def main():
    print("\n🚀 Scanning Kerala IT Parks for Technical Jobs (Excluding Java)...")
    infopark_jobs = fetch_infopark_jobs()
    driver.quit()

    if infopark_jobs:
        generate_maitexa_brochure(infopark_jobs)
        print("✅ PDF successfully created.")
    else:
        print("⚠️ No matching jobs found.")

if __name__ == "__main__":
    main()
