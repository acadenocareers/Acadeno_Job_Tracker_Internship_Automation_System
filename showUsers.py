import sqlite3
from werkzeug.security import generate_password_hash

email = "aswathymaitexa@gmail.com"
new_password = generate_password_hash("Admin@123")

conn = sqlite3.connect("users.db")
cur = conn.cursor()
cur.execute("UPDATE users SET password=? WHERE email=?", (new_password, email))
conn.commit()
conn.close()

print("Password updated successfully!")
