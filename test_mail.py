import os
import smtplib
import ssl
from dotenv import load_dotenv

# Load variables from .env
load_dotenv()

EMAIL_ADDRESS = os.environ.get("MAIL_USER")
EMAIL_PASSWORD = os.environ.get("MAIL_PASS")

print("MAIL_USER =", EMAIL_ADDRESS)
print("MAIL_PASS set =", bool(EMAIL_PASSWORD))

to_email = EMAIL_ADDRESS  # send to yourself
subject = "Test from Python"
body = "If you see this email, your SMTP config works!"

message = f"Subject: {subject}\nFrom: {EMAIL_ADDRESS}\nTo: {to_email}\n\n{body}"

context = ssl.create_default_context()

try:
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as smtp:
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.sendmail(EMAIL_ADDRESS, to_email, message.encode("utf-8"))

    print("✅ Test mail sent successfully.")
except Exception as e:
    print("❌ SMTP error:", repr(e))
