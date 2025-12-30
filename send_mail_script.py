import os
import ssl
import smtplib
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

MAIL_USER = os.getenv("MAIL_USER")
MAIL_PASS = os.getenv("MAIL_PASS")

# ---------------------------------------------------
# READ STUDENTS FROM names.txt & emails.txt
# ---------------------------------------------------
def read_students():
    students = []

    if not os.path.exists("names.txt") or not os.path.exists("emails.txt"):
        return students

    with open("names.txt", "r") as f_names, open("emails.txt", "r") as f_emails:
        names = f_names.read().strip().split(",")
        emails = f_emails.read().strip().split(",")

    for name, email in zip(names, emails):
        students.append((name.strip(), email.strip()))

    return students

# ---------------------------------------------------
# AI MOTIVATION GENERATOR (HuggingFace)
# ---------------------------------------------------
def get_ai_motivation():
    try:
        API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2"
        headers = {"Authorization": f"Bearer {os.getenv('HF_API_KEY')}"}

        prompt = """
Write a short powerful motivational message for a student applying for IT jobs.
Tone: supportive, inspiring, professional.
1–2 sentences only.
"""

        payload = {"inputs": f"<s>[INST] {prompt} [/INST]"}

        response = requests.post(API_URL, headers=headers, json=payload, timeout=60)
        result = response.json()

        text = result[0]["generated_text"]
        return text.split("[/INST]")[-1].strip()
    except:
        return "Believe in yourself — every step you take today builds the future you deserve 🌱"

# ---------------------------------------------------
# MAIN MAIL FUNCTION
# ---------------------------------------------------
def send_job_poster(file_path):
    students = read_students()

    if not students:
        print("❌ No students found. Check names.txt & emails.txt")
        return

    # Generate AI quote once per run
    quote = get_ai_motivation()

    LOGO_URL = "https://raw.githubusercontent.com/acadenocareers/Joblisting/main/maitexa_logo.png"
    context = ssl.create_default_context()

    for name, email in students:
        print(f"📩 Sending to {name} ({email})")

        msg = MIMEMultipart()
        msg["From"] = MAIL_USER
        msg["To"] = email
        msg["Subject"] = "Here is Your New Job Opportunity – Acadeno Technologies"

        html_body = f"""
        <html>
        <body style="font-family: 'Segoe UI', sans-serif; background:#f7f7f7; padding:20px;">

        <div style="max-width:700px; margin:auto; background:#ffffff; border-radius:12px; overflow:hidden;
             box-shadow:0 6px 20px rgba(0,0,0,0.15);">

            <div style="background: linear-gradient(90deg, #6e3bea, #ff7a00); 
                        padding:25px 0; text-align:center; color:#ffffff;">
                <img src="{LOGO_URL}" style="width:140px; margin-bottom:10px;">
                <h2 style="margin:0;">Acadeno Technologies Private Limited</h2>
            </div>

            <div style="padding:30px; font-size:16px; color:#333;">
                <p>Dear <strong style="color:#6e3bea;">{name}</strong>,</p>

                <p style="font-weight:600; color:#333;">
                   🌟 {quote}
                </p>

                <p>
                    At <strong>Acadeno Technologies</strong>, your journey matters. 
                    Each job opportunity we share is a door to new possibilities — 
                    waiting for you to step through with confidence and determination. 💡
                </p>

                <p>
                    <strong>Remember:</strong> You don’t need to be perfect to begin — 
                    you only need to start.
                </p>

                <p>
                    Attached is your latest <strong>Job Poster</strong>.  
                    Explore it and take one more step towards your bright future! 🚀
                </p>

                <p style="margin-top:30px;">
                With warm regards,<br>
                <strong>Team Acadeno Technologies Pvt. Ltd.</strong>
                </p>
            </div>

            <div style="background:#f0f0f0; padding:15px; text-align:center; font-size:14px; color:#777;">
                © 2025 Acadeno Technologies Pvt. Ltd. All Rights Reserved.
            </div>

        </div>

        </body>
        </html>
        """

        msg.attach(MIMEText(html_body, "html"))

        # ---------------- Attach Poster ----------------
        try:
            with open(file_path, "rb") as f:
                attachment = MIMEBase("application", "octet-stream")
                attachment.set_payload(f.read())

            encoders.encode_base64(attachment)
            attachment.add_header(
                "Content-Disposition",
                f"attachment; filename={os.path.basename(file_path)}"
            )
            msg.attach(attachment)
        except Exception as e:
            print(f"❌ Error attaching file: {e}")

        # ---------------- Send Mail ----------------
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as smtp:
                smtp.login(MAIL_USER, MAIL_PASS)
                smtp.sendmail(MAIL_USER, email, msg.as_string())

            print(f"✔ Successfully sent to {email}")
        except Exception as e:
            print(f"❌ Error sending to {email}: {e}")
