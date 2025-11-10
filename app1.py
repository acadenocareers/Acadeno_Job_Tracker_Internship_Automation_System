# ------------------------------------------------------------
# MAITEXA TECHNOLOGIES - PROFESSIONAL GREEN BROCHURE (FINAL)
# Author: Aswathy
# ------------------------------------------------------------

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
import os


# ------------------------------____
# CONFIGURATION
# ------------------------------
OUTPUT_FILE = "Maitexa_Final_Brochure.pdf"
LOGO_PATH = "maitexa_logo.png"  # Your logo
COMPANY_NAME = "MAITEXA TECHNOLOGIES PVT LTD"
SLOGAN = "Integrating Minds"
ADDRESS = "Kadannamanna, Malappuram, Kerala - 679324"
EMAIL = "contact@maitexa.com"
WEBSITE = "www.maitexa.com"

# Colors
LIGHT_GREEN = colors.Color(0.6, 0.8, 0.6)
DARK_GREEN = colors.Color(0.0, 0.5, 0.3)
WHITE = colors.white
TEXT_COLOR = colors.HexColor("#003300")

# Job Data (replace 'link' with real URLs from scraper)
jobs = [
    {
        "title": "Python Developer",
        "company": "Techversant Infotech Pvt Ltd",
        "location": "Infopark, Kochi",
        "experience": "0–2 years",
        "date": "22-10-2025",
        "link": "https://infopark.in/company/techversant-infotech/job/python-developer"
    },
    {
        "title": "Data Analyst Intern",
        "company": "ALTOS Technologies",
        "location": "Infopark, Kochi",
        "experience": "Intern",
        "date": "10-09-2025",
        "link": "https://infopark.in/company/altos-technologies/job/data-analyst-intern"
    },
    {
        "title": "AI/ML Engineer",
        "company": "Beinex Consulting Pvt Ltd",
        "location": "Infopark, Kochi",
        "experience": "0–2 years",
        "date": "24-10-2025",
        "link": "https://infopark.in/company/beinex/job/aiml-engineer"
    },
]


# ------------------------------
# DRAW HEADER DESIGN
# ------------------------------
def draw_header(pdf):
    width, height = A4

    # Light and dark green curved header
    pdf.setFillColor(LIGHT_GREEN)
    pdf.circle(-100, height - 50, 300, stroke=0, fill=1)
    pdf.setFillColor(DARK_GREEN)
    pdf.circle(250, height + 60, 300, stroke=0, fill=1)

    # Logo in green header
    if os.path.exists(LOGO_PATH):
        pdf.drawImage(LOGO_PATH, width / 2 - 50, height - 160, width=100, height=80, mask='auto')
    else:
        pdf.setFont("Helvetica-Bold", 14)
        pdf.setFillColor(WHITE)
        pdf.drawCentredString(width / 2, height - 120, "[LOGO MISSING]")

    # Company Name (within green)
    pdf.setFont("Helvetica-Bold", 18)
    pdf.setFillColor(WHITE)
    pdf.drawCentredString(width / 2, height - 190, COMPANY_NAME)

    # Slogan
    pdf.setFont("Helvetica-Oblique", 11)
    pdf.setFillColor(WHITE)
    pdf.drawCentredString(width / 2, height - 205, SLOGAN)

    # Contact Info
    pdf.setFont("Helvetica", 9)
    pdf.drawCentredString(width / 2, height - 220, ADDRESS)
    pdf.drawCentredString(width / 2, height - 232, f"{EMAIL} | {WEBSITE}")


# ------------------------------
# DRAW WATERMARK
# ------------------------------
def draw_watermark(pdf):
    width, height = A4
    if os.path.exists(LOGO_PATH):
        pdf.saveState()
        pdf.translate(width / 2 - 100, height / 2 - 100)
        pdf.setFillAlpha(0.07)  # Light opacity
        pdf.drawImage(LOGO_PATH, 0, 0, width=200, height=200, mask='auto')
        pdf.restoreState()


# ------------------------------
# DRAW FOOTER DESIGN
# ------------------------------
def draw_footer(pdf):
    width, height = A4
    pdf.setFillColor(LIGHT_GREEN)
    pdf.circle(width - 200, -60, 300, stroke=0, fill=1)
    pdf.setFillColor(DARK_GREEN)
    pdf.circle(width + 100, -100, 300, stroke=0, fill=1)


# ------------------------------
# DRAW JOBS
# ------------------------------
def draw_jobs(pdf):
    width, height = A4
    y = height - 280
    job_box_height = 90

    for idx, job in enumerate(jobs, 1):
        if y < 130:
            pdf.showPage()
            draw_watermark(pdf)
            draw_header(pdf)
            draw_footer(pdf)
            y = height - 130

        # Job box
        pdf.setFillColor(WHITE)
        pdf.roundRect(80, y - job_box_height, width - 160, job_box_height, 10, stroke=1, fill=1)

        # Job title
        pdf.setFont("Helvetica-Bold", 12)
        pdf.setFillColor(TEXT_COLOR)
        pdf.drawString(100, y - 25, f"{idx}. {job['title']}")

        # Job details
        pdf.setFont("Helvetica", 10)
        pdf.drawString(110, y - 40, f"🏢 {job['company']}")
        pdf.drawString(110, y - 55, f"📍 {job['location']}")
        pdf.drawString(110, y - 70, f"💼 {job['experience']}  |  📅 {job['date']}")

        # Job link (redirects to exact job)
        if job["link"]:
            pdf.setFillColor(colors.HexColor("#0033CC"))
            pdf.drawString(110, y - 85, "🔗 Apply / View Job")
            pdf.linkURL(job["link"], (110, y - 90, width - 100, y - 75))
        else:
            pdf.setFillColor(colors.gray)
            pdf.drawString(110, y - 85, "No link available")

        y -= job_box_height + 25


# ------------------------------
# FOOTER TEXT
# ------------------------------
def draw_footer_text(pdf):
    width, height = A4
    pdf.setFont("Helvetica-Oblique", 9)
    pdf.setFillColor(TEXT_COLOR)
    pdf.drawCentredString(width / 2, 40, "Generated by Maitexa Job Tracker © 2025 | Infopark • Technopark • Cyberpark")


# ------------------------------
# MAIN FUNCTION
# ------------------------------
def create_brochure():
    pdf = canvas.Canvas(OUTPUT_FILE, pagesize=A4)

    draw_watermark(pdf)
    draw_header(pdf)
    draw_footer(pdf)
    draw_jobs(pdf)
    draw_footer_text(pdf)

    pdf.save()
    print(f"✅ Maitexa Green Brochure (with watermark + fixed layout) saved as: {OUTPUT_FILE}")


# ------------------------------
# RUN
# ------------------------------
if __name__ == "__main__":
    create_brochure()
