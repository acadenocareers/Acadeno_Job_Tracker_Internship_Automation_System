import os
import sqlite3
import uuid
import smtplib
import ssl
from datetime import datetime, timedelta

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    send_from_directory,
)
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

# Load environment variables from .env (for local dev)
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key")


# =========================================================
#  DATABASE HELPERS
# =========================================================
def get_db():
    conn = sqlite3.connect("users.db")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            reset_token TEXT,
            reset_expires_at TEXT
        );
        """
    )

    # Create default admin for testing (only if not present)
    cur.execute("SELECT * FROM users WHERE email = ?", ("admin@example.com",))
    admin = cur.fetchone()
    if not admin:
        pw_hash = generate_password_hash("Admin@123")
        cur.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            ("Admin", "admin@example.com", pw_hash),
        )
        print("✅ Default admin: admin@example.com / Admin@123")

    conn.commit()
    conn.close()


# =========================================================
#  EMAIL / SMTP HELPERS
# =========================================================
def get_mail_credentials():
    """
    Read MAIL_USER and MAIL_PASS from environment (or .env).
    Raise a clear error if they are missing.
    """
    user = os.environ.get("MAIL_USER")
    pwd = os.environ.get("MAIL_PASS")

    # Debug print – helpful while you’re testing
    print("DEBUG MAIL_USER =", user)
    print("DEBUG MAIL_PASS set =", bool(pwd))

    if not user or not pwd:
        raise RuntimeError(
            "MAIL_USER or MAIL_PASS is not set. "
            "Set them in your .env or environment variables."
        )
    return user, pwd


def send_reset_email(to_email: str, reset_link: str):
    """
    Send a password reset email with a clickable link.
    """
    try:
        email_address, email_password = get_mail_credentials()
    except RuntimeError as e:
        # In dev, we at least print the link so you can copy–paste it
        print("⚠ Email not configured:", e)
        print("Reset link (fallback):", reset_link)
        return

    subject = "Password Reset - Acadeno"
    body = f"""Hello,

We received a request to reset your password.

Click this link to reset your password (valid for 30 minutes):

{reset_link}

If you did not request this, you can ignore this email.
"""

    message = f"Subject: {subject}\nFrom: {email_address}\nTo: {to_email}\n\n{body}"

    context = ssl.create_default_context()

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as smtp:
            smtp.login(email_address, email_password)
            smtp.sendmail(email_address, to_email, message.encode("utf-8"))

        print(f"📧 Reset email sent to {to_email}")
    except Exception as e:
        print("❌ Error sending email:", repr(e))
        print("Reset link (fallback):", reset_link)


# =========================================================
#  ROUTES
# =========================================================

# Root → always go to login first
@app.route("/")
def home():
    return redirect(url_for("login"))


# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # form field names must be: email, password
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cur.fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            flash("Login successful", "success")
            # redirect to index.html only after successful login
            return redirect(url_for("index_page"))
        else:
            flash("Invalid email or password", "danger")

    return render_template("login.html")


# ------------- INDEX (after login) -------------
@app.route("/index")
def index_page():
    if "user_id" not in session:
        flash("Please log in first", "warning")
        return redirect(url_for("login"))

    # index.html is in the PROJECT ROOT, not in /templates
    return send_from_directory(".", "index.html")


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out", "info")
    return redirect(url_for("login"))


# --------------- REGISTER ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # form fields: username, email, password, confirm_password
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if password != confirm:
            flash("Passwords do not match", "danger")
            return redirect(url_for("register"))

        conn = get_db()
        cur = conn.cursor()

        cur.execute("SELECT * FROM users WHERE email = ?", (email,))
        existing = cur.fetchone()
        if existing:
            flash("Email already registered", "danger")
            conn.close()
            return redirect(url_for("register"))

        pw_hash = generate_password_hash(password)
        cur.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            (username, email, pw_hash),
        )
        conn.commit()
        conn.close()

        flash("Registration successful. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


# ------------- FORGOT PASSWORD ----------------
@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        # form field: email
        email = request.form.get("email", "").strip().lower()

        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cur.fetchone()

        # Do not reveal whether email exists or not
        if not user:
            flash("If this email exists, a reset link has been sent.", "info")
            conn.close()
            return redirect(url_for("login"))

        token = str(uuid.uuid4())
        expires_at = (datetime.utcnow() + timedelta(minutes=30)).isoformat()

        cur.execute(
            "UPDATE users SET reset_token = ?, reset_expires_at = ? WHERE id = ?",
            (token, expires_at, user["id"]),
        )
        conn.commit()
        conn.close()

        reset_link = url_for("reset_password", token=token, _external=True)
        print("🔐 Reset link:", reset_link)  # backup in terminal

        send_reset_email(email, reset_link)

        flash("If this email exists, a reset link has been sent.", "info")
        return redirect(url_for("login"))

    return render_template("forgot_password.html")


# -------------- RESET PASSWORD ----------------
@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE reset_token = ?", (token,))
    user = cur.fetchone()

    if not user:
        conn.close()
        return "Invalid or expired token", 400

    # Check expiry
    if user["reset_expires_at"]:
        expires = datetime.fromisoformat(user["reset_expires_at"])
        if datetime.utcnow() > expires:
            conn.close()
            return "Reset link has expired", 400

    if request.method == "POST":
        # form fields: password, confirm_password
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if password != confirm:
            flash("Passwords do not match", "danger")
            return redirect(url_for("reset_password", token=token))

        new_hash = generate_password_hash(password)
        cur.execute(
            """
            UPDATE users
            SET password_hash = ?, reset_token = NULL, reset_expires_at = NULL
            WHERE id = ?
            """,
            (new_hash, user["id"]),
        )
        conn.commit()
        conn.close()

        flash("Password updated. Please log in.", "success")
        return redirect(url_for("login"))

    conn.close()
    return render_template("reset_password.html", token=token)


# =========================================================
#  MAIN
# =========================================================
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
