import sqlite3

conn = sqlite3.connect("users.db")
cur = conn.cursor()

cur.execute("PRAGMA table_info(users)")
columns = cur.fetchall()

print("\nCOLUMNS IN USERS TABLE:\n------------------------")
for col in columns:
    print(col)

conn.close()
