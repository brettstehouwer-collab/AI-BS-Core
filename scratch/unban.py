import sqlite3
import os

db_path = r'C:\AI-BS\backend\commercial_gateway\security_audit.db'
if not os.path.exists(db_path):
    db_path = r'C:\AI-BS\security_audit.db'

conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("DELETE FROM ip_blacklist WHERE ip_address = '127.0.0.1'")
conn.commit()
print("Unbanned 127.0.0.1")
conn.close()
