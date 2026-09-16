import re

with open("C:/AI-BS/backend/AI_BS_Backend.py", "r", encoding="utf-8") as f:
    c = f.read()
c = c.replace(
    "from typing import Optional, Header, Depends", "from typing import Optional"
)
with open("C:/AI-BS/backend/AI_BS_Backend.py", "w", encoding="utf-8") as f:
    f.write(c)

with open("C:/AI-BS/backend/calendar_integration.py", "r", encoding="utf-8") as f:
    c = f.read()

bad_snippet = """        try:
            cursor.execute("ALTER TABLE appointments ADD COLUMN client_id TEXT DEFAULT 'stehouwer_publishing'")
        except:
            pass

        conn.commit()"""

c = c.replace(bad_snippet, "        conn.commit()")

init_db_replacement = """            CREATE TABLE IF NOT EXISTS appointments (
                client_id TEXT DEFAULT 'stehouwer_publishing',
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                date TEXT,
                time TEXT,
                start_datetime TEXT,
                end_datetime TEXT,
                notes TEXT,
                category TEXT
            )
        ''')
        try:
            cursor.execute("ALTER TABLE appointments ADD COLUMN client_id TEXT DEFAULT 'stehouwer_publishing'")
        except:
            pass
        conn.commit()"""

# We'll just replace the entire init_db block safely
init_block_old = """            CREATE TABLE IF NOT EXISTS appointments (
                client_id TEXT DEFAULT 'stehouwer_publishing',
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                date TEXT,
                time TEXT,
                start_datetime TEXT,
                end_datetime TEXT,
                notes TEXT,
                category TEXT
            )
        ''')
        conn.commit()"""

c = c.replace(init_block_old, init_db_replacement)

with open("C:/AI-BS/backend/calendar_integration.py", "w", encoding="utf-8") as f:
    f.write(c)

print("Repair completed!")
