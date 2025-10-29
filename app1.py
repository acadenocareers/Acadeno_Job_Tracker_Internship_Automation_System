import time
import requests
from bs4 import BeautifulSoup
from fpdf import FPDF
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================================
# ✅ Selenium Setup
# ==========================================================
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

# ==========================================================
# 🔹 Fetch Infopark Jobs (Live AJAX)
# ==========================================================
def fetch_infopark_jobs():
    print("Fetching jobs from Infopark...")
    jobs = []
    page = 1
    while True:
        url = f"https://infopark.in/companies/job-search?ajax=true&page={page}"
        resp = requests.get(url, verify=False, timeout=10)
        html = resp.text.strip()
        if not html or "No jobs found" in html:
            break
        soup = BeautifulSoup(html, "html.parser")
        rows = soup.find_all("tr")

        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 3:
                date = cols[0].get_text(strip=True)
                title = cols[1].get_text(strip=True)
                company = cols[2].get_text(strip=True)
                link_tag = cols[1].find("a")
                link = "https://infopark.in" + link_tag["href"] if link_tag and link_tag.get("href") else ""
                jobs.append({
                    "park": "Infopark",
                    "title": title,
                    "company": company,
                    "experience": "Not specified",
                    "date": date,
                    "link": link,
                    "location": "Infopark, Kochi"
                })
        page += 1
    print(f"✅ Found {len(jobs)} jobs from Infopark.")
    return jobs

# ==========================================================
# 🔹 Fetch Technopark Jobs
# ==========================================================
def fetch_technopark_jobs():
    print("Fetching jobs from Technopark...")
    jobs = []
    try:
        driver.get("https://technopark.org/careers")
        WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.job_box"))
        )
        job_cards = driver.find_elements(By.CSS_SELECTOR, "div.job_box")
        for jc in job_cards:
            title = jc.find_element(By.TAG_NAME, "h4").text.strip()
            company = jc.find_element(By.TAG_NAME, "h5").text.strip()
            link = jc.find_element(By.TAG_NAME, "a").get_attribute("href")
            jobs.append({
                "park": "Technopark",
                "title": title,
                "company": company,
                "experience": "Not specified",
                "date": "N/A",
                "link": link,
                "location": "Technopark, Trivandrum"
            })
    except Exception as e:
        print("⚠️ Technopark load error:", e)
    print(f"✅ Found {len(jobs)} jobs from Technopark.")
    return jobs

# ==========================================================
# 🔹 Fetch Cyberpark Jobs
# ==========================================================
def fetch_cyberpark_jobs():
    print("Fetching jobs from Cyberpark...")
    jobs = []
    try:
        driver.get("https://cyberparkkerala.org/careers")
        WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.job-item"))
        )
        job_cards = driver.find_elements(By.CSS_SELECTOR, "div.job-item")
        for jc in job_cards:
            title = jc.find_element(By.TAG_NAME, "h3").text.strip()
            company = jc.find_element(By.TAG_NAME, "p").text.strip()
            link_tag = jc.find_element(By.TAG_NAME, "a").get_attribute("href")
            jobs.append({
                "park": "Cyberpark",
                "title": title,
                "company": company,
                "experience": "Not specified",
                "date": "N/A",
                "link": link_tag,
                "location": "Cyberpark, Kozhikode"
            })
    except Exception as e:
        print("⚠️ Cyberpark load error:", e)
    print(f"✅ Found {len(jobs)} jobs from Cyberpark.")
    return jobs

# ==========================================================
# 🔹 Filter Jobs by Keyword
# ==========================================================
def filter_relevant_jobs(jobs):
    keywords = ["python", "data", "ai", "machine", "power bi", "analytics"]
    return [job for job in jobs if any(k in job["title"].lower() for k in keywords)]

# ==========================================================
# 🎨 Create Professional PDF with Branding
# ==========================================================
class PDFReport(FPDF):
    def header(self):
        # Company logo
        self.image("logo.png", 10, 8, 30)
        # Company name
        self.set_xy(45, 10)
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(0, 51, 102)
        self.cell(0, 10, "MAITEXA TECHNOLOGIES PVT LTD", ln=True)
        # Address & Contact
        self.set_font("Helvetica", "", 11)
        self.set_text_color(80, 80, 80)
        self.cell(0, 8, "Kadannamanna, Malappuram, Kerala – 679324", ln=True)
        self.cell(0, 8, "✉ contact@maitexa.com | 🌐 www.maitexa.com", ln=True)
        self.ln(5)
        # Title bar
        self.set_fill_color(0, 51, 102)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 10, "Kerala IT Park Job Report – October 2025", ln=True, align="C", fill=True)
        self.ln(8)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 9)
        self.set_text_color(128)
        self.cell(0, 10, "Generated by MAITEXA Job Tracker System", align="C")

    def add_job(self, job, idx):
        self.set_text_color(0, 0, 0)
        self.set_font("Helvetica", "B", 12)
        self.multi_cell(0, 8, f"{idx}. {job['title']}", align="L")

        self.set_font("Helvetica", "", 11)
        self.cell(0, 7, f"🏢 {job['company']}", ln=True)
        self.cell(0, 7, f"📍 {job['location']} | 📅 {job['date']}", ln=True)

        if job["link"]:
            self.set_text_color(0, 0, 180)
            self.cell(0, 7, "🔗 Click here to view job", ln=True, link=job["link"])

        self.ln(5)
        self.set_draw_color(220, 220, 220)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

def generate_pdf(jobs, filename="Maitexa_Job_Report.pdf"):
    pdf = PDFReport()
    pdf.add_page()
    for i, job in enumerate(jobs, 1):
        pdf.add_job(job, i)
    pdf.output(filename)
    print(f"✅ Professional PDF saved as {filename}")

# ==========================================================
# MAIN FUNCTION
# ==========================================================
def main():
    all_jobs = []
    all_jobs += fetch_infopark_jobs()
    all_jobs += fetch_technopark_jobs()
    all_jobs += fetch_cyberpark_jobs()
    driver.quit()

    filtered = filter_relevant_jobs(all_jobs)
    if filtered:
        generate_pdf(filtered)
    else:
        print("⚠️ No relevant jobs found.")

if __name__ == "__main__":
    main()
