import sqlite3
import shutil
import tempfile
import os

src_cookie = r'C:\Users\footb\AppData\Local\Google\Chrome\User Data\Default\Network\Cookies'
dev_cookie = r'C:\Users\footb\.cache\chrome-devtools-mcp\chrome-profile\Default\Network\Cookies'

for label, p in [('SOURCE', src_cookie), ('DEV', dev_cookie)]:
    if not os.path.exists(p):
        print(f"{label}: not found")
        continue
    # copy to temp to avoid locks
    with tempfile.NamedTemporaryFile(delete=False) as tf:
        tmp_name = tf.name
    try:
        try:
            shutil.copyfile(p, tmp_name)
        except Exception as e:
            print(f"{label}: Error copying file (likely locked by running Chrome): {e}")
            continue
        con = sqlite3.connect(tmp_name)
        cur = con.cursor()
        cur.execute("SELECT host_key, name FROM cookies WHERE host_key LIKE '%google%' AND name IN ('SID', 'SSID', 'SAPISID', 'HSID', '__Secure-1PSID')")
        rows = cur.fetchall()
        print(f"=== {label} GOOGLE AUTH COOKIES ===")
        print(f"Count: {len(rows)}")
        for r in rows:
            print(f"  {r[0]} -> {r[1]}")
        cur.execute("SELECT count(*) FROM cookies")
        total = cur.fetchone()[0]
        print(f"Total cookies in DB: {total}")
        con.close()
    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)
