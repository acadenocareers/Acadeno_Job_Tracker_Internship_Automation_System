<div align="center">

<img src="https://drive.google.com/uc?export=view&id=1wLdjI3WqmmeZcCbsX8aADhP53mRXthtB" alt="Acadeno Logo" width="120" style="border-radius:10px;"/>

<h1> Acadeno Job Tracker & Internship Automation System</h1>
<h3>Developed by <a href="https://acadeno.com" target="_blank">Acadeno Technologies Pvt. Ltd.</a></h3>

<p> Automated system that scrapes job openings from Indian IT Parks & Job Portals, filters fresher-level roles, emails them to students daily, and tracks engagement in real-time using Google Sheets.</p>

</div>

---

##  Overview

The **Acadeno Job Tracker** is a fully automated internship/job support system designed for educational institutes offering placement assistance.  
It intelligently collects, filters, and emails live job listings to 100+ students daily — while tracking every job application click in Google Sheets.

This project was developed to **simplify internship support**, **reduce manual coordination**, and **improve placement visibility** for institutes.

---

##  Objectives

-  Deliver **daily job notifications** directly to students’ inboxes.
-  Filter **only relevant and fresher-friendly** openings.
-  Enable institutes to **monitor student engagement** via Google Sheets.
-  Automate the entire process using **GitHub Actions**, **Python**, and **Google Apps Script**.

---

##  Key Features

###  Smart Job Scraper
Scrapes verified IT park and portal websites:
- Infopark, Technopark, Cyberpark, SmartCity Kochi  
- TIDEL Park Chennai, STPI India  
- Indeed, Naukri (Nationwide)  
- LinkedIn (best-effort fetch)  

###  Intelligent Filters
Includes roles like:
> *Full Stack Developer (Python + React)*  
> *Data Analyst (Python + Power BI)*  
> *Machine Learning Engineer*  
> *AI Developer*  
> *Python Developer (Intern / Fresher)*  

Excludes:
> PHP, Java, .NET, Laravel, Senior, Manager, 3+ Years

###  Personalized Email Delivery
- Automatically sends beautiful HTML job alert emails.  
- Each mail includes motivational quotes and company branding.  
- Personalized with student name and tracked job links.  
- Sent securely via Gmail SMTP (using GitHub Secrets).

###  Real-Time Google Sheet Tracking
- Every student click is logged with timestamp, email, job title, and job link.  
- Each student also gets their own tab for personalized record tracking.  
- Placement coordinators can monitor daily engagement and application behavior.

Example:
| Timestamp | Student Email | Job Title | Job Link |
|------------|----------------|------------|-----------|
| 12/11/2025 15:18:46 | aswathyshibinnm@gmail.com | Python Developer GenAI | https://linkedin.com/... |

---

##  Workflow Summary

<div align="center">
<img src="https://img.icons8.com/color/48/000000/workflow.png" width="40"/>
</div>

1️⃣ **Daily Job Scraping**  
→ Python Selenium crawler runs via GitHub Actions at 10 AM IST.  
2️⃣ **Data Filtering**  
→ Filters jobs for Python, AI, Data Science, ML, Full Stack, etc.  
3️⃣ **Email Broadcast**  
→ Sends to 100+ students with personalized links.  
4️⃣ **Click Tracking**  
→ Logs data in Google Sheets instantly via Google Apps Script.  
5️⃣ **Reporting**  
→ Placement coordinators view engagement metrics in Sheets or BI tools.

---

## Tech Stack

| Layer | Technology |
|-------|-------------|
| **Automation** | Python 3.11 |
| **Web Scraping** | Selenium, BeautifulSoup4 |
| **Data Cleaning** | Pandas |
| **Scheduling** | GitHub Actions |
| **Emailing** | smtplib, MIME |
| **Tracking** | Google Apps Script + Google Sheets |
| **Data Storage** | CSV / Google Sheets |

---

## Environment Variables (GitHub Secrets)

| Secret | Description |
|---------|--------------|
| `EMAIL_USER` | Gmail ID used for sending |
| `EMAIL_PASS` | Gmail App Password |
| `EMAIL_TO` | Comma-separated student email list |
| `STUDENT_NAMES` | Comma-separated student names |
| `TRACKER_URL` | Deployed Apps Script URL for click tracking |

---

##  GitHub Actions Setup

```yaml
name: Maitexa Job Scraper Automation

on:
  schedule:
    - cron: '0 4 * * *'   # Runs every day at 10:00 AM IST
  workflow_dispatch:

jobs:
  run-script:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install pandas selenium requests beautifulsoup4 webdriver-manager

      - name: Run Maitexa job scraper and send tracked mails
        env:
          EMAIL_USER: ${{ secrets.EMAIL_USER }}
          EMAIL_PASS: ${{ secrets.EMAIL_PASS }}
          EMAIL_TO: ${{ secrets.EMAIL_TO }}
          STUDENT_NAMES: ${{ secrets.STUDENT_NAMES }}
          TRACKER_URL: ${{ secrets.TRACKER_URL }}
        run: python app.py
