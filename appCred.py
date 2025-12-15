from flask import Flask, request, jsonify, send_from_directory
import requests
from nacl import public
import base64
import json
import os
import sqlite3



app = Flask(__name__)


def init_students_db():
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT UNIQUE
        )
    """)
    conn.commit()
    conn.close()

init_students_db()

def save_student_to_db(name, email):
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO students (name, email) VALUES (?, ?)",
        (name, email)
    )
    conn.commit()
    conn.close()



# Load GitHub credentials
GITHUB_TOKEN = os.getenv("GITHUB_PAT")   # <-- FIXED
REPO = os.getenv("GITHUB_REPO", "acadenocareers/Joblisting") 
EMAIL_SECRET = "EMAIL_TO"
NAMES_SECRET = "STUDENT_NAMES"

def encrypt(public_key: str, secret_value: str) -> str:
    public_key_bytes = base64.b64decode(public_key)
    sealed_box = public.SealedBox(public.PublicKey(public_key_bytes))
    encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
    return base64.b64encode(encrypted).decode("utf-8")

def github_headers() -> dict:
    if not GITHUB_TOKEN:
        raise RuntimeError("GITHUB_PAT environment variable is missing.")

    return {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

def fetch_public_key():
    url = f"https://api.github.com/repos/{REPO}/actions/secrets/public-key"
    response = requests.get(url, headers=github_headers())
    response.raise_for_status()
    payload = response.json()
    return payload["key"], payload["key_id"]

def upsert_secret(secret_name: str, secret_value: str):
    public_key, key_id = fetch_public_key()
    encrypted_value = encrypt(public_key, secret_value)

    url_secret = f"https://api.github.com/repos/{REPO}/actions/secrets/{secret_name}"
    payload = {
        "encrypted_value": encrypted_value,
        "key_id": key_id
    }

    response = requests.put(url_secret, headers=github_headers(), json=payload)
    response.raise_for_status()

@app.get("/")
def serve_index():
    return send_from_directory(".", "index.html")

@app.post("/request-credentials")
def request_credentials():
    data = request.get_json(silent=True) or {}
    student_name = data.get("student_name", "").strip()
    student_mail = data.get("student_mail", "").strip().lower()
   


    if not student_name or not student_mail:
        return jsonify({"error": "student_name and student_mail are required."}), 400
    
    

    try:
        save_student_to_db(student_name, student_mail)
        upsert_secret(EMAIL_SECRET, student_mail)
        upsert_secret(NAMES_SECRET, student_name)

    except requests.HTTPError as exc:
        print("🔥 HTTP ERROR:", exc.response.text)
        return jsonify({"error": "GitHub API error", "details": exc.response.text}), 502

    except Exception as exc:
        print("🔥 ERROR:", exc)
        return jsonify({"error": str(exc)}), 500

    return jsonify({"status": "success"}), 200

if __name__ == "__main__":
    app.run(debug=True)
