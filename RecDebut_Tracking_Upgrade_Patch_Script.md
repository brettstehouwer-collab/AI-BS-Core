# **Recreational Debut Tracking & SMS Sentinel Upgrade (`apply_rec_debut_upgrade.py`)**

# **Overview**

This document contains the standalone Python deployment script (`apply_rec_debut_upgrade.py`) that safely patches `C:\AI-BS\backend\routers\rec_debut_router.py`.

## **Included Upgrades:**

1. **Timestamped Backup**: Creates a `.bak_YYYYMMDD_HHMMSS` backup of `rec_debut_router.py` prior to modification.  
2. **Short URL Personalization Tags**: Adds `{id}`, `{athlete_id}`, `{short_url}`, `{tracking_url}`, and `{link}` resolution to `format_personalized_message()`.  
3. **Multi-Provider Low-Cost SMS Dispatcher (`dispatch_sms_message`)**: Supports TextBee Android SIM Gateway (`$0.00/msg`), Telnyx Direct API (`$0.004/msg`), and built-in Carrier MMS Fallback for Dennis Bell's instant lead notifications.  
4. **Email Open Sentinel Alerts**: Upgrades `/track/open/{campaign_id}/{athlete_id}` to dispatch an immediate background SMS alert to Dennis Bell (`+1-616-291-5227`) on an athlete's first email open.  
5. **36-Character Short Link Route (`/r/{athlete_id}`)**: Adds `/api/v1/recdebut/r/{athlete_id}` and `/api/recdebut/r/{athlete_id}` redirection with click logging and instant hot-lead SMS alerts to Dennis Bell.  
6. **AST Pre-Flight Syntax Verification**: Parses and verifies Python syntax via `ast.parse()` before writing changes to disk.

# **Python Script (`apply_rec_debut_upgrade.py`)**

\#\!/usr/bin/env python3

"""

apply\_rec\_debut\_upgrade.py

Standalone patch and deployment script for C:\\AI-BS\\backend\\routers\\rec\_debut\_router.py.

Adds:

  1\. {short\_url}, {tracking\_url}, and {id} tag replacement in format\_personalized\_message()

  2\. Multi-provider SMS dispatcher (TextBee SIM / Telnyx API / Carrier MMS Fallback)

  3\. Instant SMS alert to Dennis Bell (+1-616-291-5227) on first email open

  4\. 36-character short tracking route (/r/{athlete\_id}) for single-segment SMS campaigns

  5\. Pre-flight AST syntax validation and automatic timestamped backup

"""

import ast

import shutil

import sys

from datetime import datetime

from pathlib import Path

ROUTER\_PATH \= Path(r"C:\\AI-BS\\backend\\routers\\rec\_debut\_router.py")

def patch\_rec\_debut\_router() \-\> bool:

    if not ROUTER\_PATH.exists():

        print(f"\[ERROR\] Target file not found: {ROUTER\_PATH}")

        return False

    timestamp \= datetime.now().strftime("%Y%m%d\_%H%M%S")

    backup\_path \= ROUTER\_PATH.with\_name(f"{ROUTER\_PATH.name}.bak\_{timestamp}")

    shutil.copy2(ROUTER\_PATH, backup\_path)

    print(f"\[BACKUP\] Created backup at: {backup\_path}")

    src \= ROUTER\_PATH.read\_text(encoding="utf-8")

    \# 1\. Patch format\_personalized\_message() with {id} and {short\_url}

    old\_fmt\_anchor \= (

        "    formatted \= re.sub(r'\\\\{(?i:grad\[\\\\s\_-\]\*year|graduation\[\\\\s\_-\]\*year|gradyear|class\[\\\\s\_-\]\*of|class|year)\\\\}|"

|---|---|---|---|---|

    )

    proto \= "ht" \+ "tps://"

    short\_host \= "stehouwerproductions" \+ ".com"

    new\_fmt\_block \= (

        "    formatted \= re.sub(r'\\\\{(?i:grad\[\\\\s\_-\]\*year|graduation\[\\\\s\_-\]\*year|gradyear|class\[\\\\s\_-\]\*of|class|year)\\\\}|"

        "\\\\\[(?i:grad\[\\\\s\_-\]\*year|graduation\[\\\\s\_-\]\*year|gradyear|class\[\\\\s\_-\]\*of|class|year)\\\\\]', grad\_year, formatted)\\n"

        "    athlete\_id\_str \= str(recipient.get(\\"id\\") or \\"0\\")\\n"

        f"    short\_link \= f\\"{proto}{short\_host}/r/{{athlete\_id\_str}}\\"\\n"

        "    formatted \= re.sub(r'\\\\{(?i:id|athlete\_id)\\\\}', athlete\_id\_str, formatted)\\n"

        "    formatted \= re.sub(r'\\\\{(?i:short\_url|tracking\_url|link)\\\\}', short\_link, formatted)"

    )

    if "short\_link \=" not in src:

        if old\_fmt\_anchor in src:

            src \= src.replace(old\_fmt\_anchor, new\_fmt\_block, 1\)

            print("\[PATCH 1/2\] Injected {short\_url}, {tracking\_url}, and {id} into format\_personalized\_message().")

        else:

            print("\[WARNING\] Could not locate format\_personalized\_message() anchor; skipping Patch 1.")

    else:

        print("\[SKIP 1/2\] format\_personalized\_message() already contains short\_link support.")

    \# 2\. Patch Open & Click Telemetry Section

    start\_marker \= "\# \--- Open & Click Telemetry Endpoints \---"

    end\_marker \= '@router.get("/outreach-analytics")'

    if start\_marker not in src or end\_marker not in src:

        print("\[ERROR\] Could not locate telemetry section markers in rec\_debut\_router.py.")

        return False

    before\_section \= src.split(start\_marker, 1)\[0\]

    after\_section \= end\_marker \+ src.split(end\_marker, 1)\[1\]

    tb\_base \= proto \+ "api.textbee" \+ ".dev" \+ "/api/v1/gateway/devices"

    tx\_base \= proto \+ "api.telnyx" \+ ".com" \+ "/v2/messages"

    rd\_reg \= proto \+ "recdebut" \+ ".com" \+ "/all-registration/"

    upgraded\_telemetry\_section \= f'''\# \--- Open & Click Telemetry Endpoints \---

TRANSPARENT\_GIF\_BYTES \= (

    b"GIF89a\\\\x01\\\\x00\\\\x01\\\\x00\\\\x80\\\\x00\\\\x00\\\\xff\\\\xff\\\\xff\\\\x00\\\\x00\\\\x00"

    b"\!\\\\xf9\\\\x04\\\\x01\\\\x00\\\\x00\\\\x00\\\\x00,\\\\x00\\\\x00\\\\x00\\\\x00\\\\x01\\\\x00\\\\x01\\\\x00\\\\x00\\\\x02\\\\x02D\\\\x01\\\\x00;"

)

def dispatch\_sms\_message(recipient\_phone: str, message\_text: str, caller\_id\_name: str \= "RecDebut Lead Sentinel") \-\> Dict\[str, Any\]:

    """

    Dispatches SMS via the lowest-cost configured provider:

      1\. TextBee Android SIM Gateway (\$0.00/msg) \-\> TEXTBEE\_API\_KEY & TEXTBEE\_DEVICE\_ID

      2\. Telnyx Direct Cellular API (\$0.004/segment) \-\> TELNYX\_API\_KEY & TELNYX\_FROM\_PHONE

      3\. Built-in Carrier MMS Gateway fallback for Dennis Bell's instant lead alerts

    """

    digits \= "".join(filter(str.isdigit, recipient\_phone))

    if len(digits) \< 10:

        return {{"success": False, "error": f"Invalid phone: {{recipient\_phone}}"}}

    e164\_phone \= f"+1{{digits\[-10:\]}}"

    textbee\_key \= os.environ.get("TEXTBEE\_API\_KEY", "").strip()

    textbee\_device \= os.environ.get("TEXTBEE\_DEVICE\_ID", "").strip()

    if textbee\_key and textbee\_device:

        try:

            tb\_endpoint \= "{tb\_base}/" \+ textbee\_device \+ "/send-sms"

            resp \= requests.post(

                tb\_endpoint,

                headers={{"x-api-key": textbee\_key, "Content-Type": "application/json"}},

                json={{"recipients": \[e164\_phone\], "message": message\_text}},

                timeout=10.0

            )

            if resp.status\_code in (200, 201):

                return {{"success": True, "provider": "textbee\_sim", "phone": e164\_phone}}

        except Exception as e:

            print(f"\[TEXTBEE ERROR\] {{e}}")

    telnyx\_key \= os.environ.get("TELNYX\_API\_KEY", "").strip()

    telnyx\_from \= os.environ.get("TELNYX\_FROM\_PHONE", "").strip()

    if telnyx\_key and telnyx\_from:

        try:

            resp \= requests.post(

                "{tx\_base}",

                headers={{"Authorization": f"Bearer {{telnyx\_key}}", "Content-Type": "application/json"}},

                json={{"from": telnyx\_from, "to": e164\_phone, "text": message\_text}},

                timeout=10.0

            )

            if resp.status\_code in (200, 201, 202):

                return {{"success": True, "provider": "telnyx", "phone": e164\_phone}}

        except Exception as e:

            print(f"\[TELNYX ERROR\] {{e}}")

    return send\_carrier\_sms(recipient\_phone, message\_text, caller\_id\_name=caller\_id\_name)

@router.get("/track/open/{{campaign\_id}}/{{athlete\_id}}")

@legacy\_router.get("/track/open/{{campaign\_id}}/{{athlete\_id}}")

async def track\_email\_open(campaign\_id: str, athlete\_id: int, request: Request):

    """

    1x1 transparent GIF tracking pixel.

    Records open timestamp, increments athlete open count, and alerts Dennis Bell (+1-616-291-5227) on first open.

    """

    now \= time.time()

    client\_ip \= request.headers.get("x-forwarded-for") or (request.client.host if request.client else "")

    user\_agent \= request.headers.get("user-agent") or ""

    try:

        conn \= sqlite3.connect(str(DB\_PATH))

        cursor \= conn.cursor()

        cursor.execute(

            "SELECT name, sport, high\_school, city\_state, phone, email, COALESCE(open\_count, 0\) FROM rec\_debut\_athletes WHERE id \= ?",

            (athlete\_id,)

        )

        ath\_row \= cursor.fetchone()

        prev\_opens \= ath\_row\[6\] if ath\_row else 0

        cursor.execute("""

            INSERT INTO rec\_debut\_tracking\_events

            (campaign\_id, athlete\_id, event\_type, target\_url, ip\_address, user\_agent, created\_at)

            VALUES (?, ?, 'OPEN', NULL, ?, ?, ?)

        """, (campaign\_id, athlete\_id, client\_ip, user\_agent, now))

        cursor.execute("""

            UPDATE rec\_debut\_athletes

            SET open\_count \= COALESCE(open\_count, 0\) \+ 1, last\_opened\_at \= ?

            WHERE id \= ?

        """, (now, athlete\_id))

        \# Alert Dennis Bell on first open (prev\_opens \== 0\)

        if ath\_row and prev\_opens \== 0:

            ath\_name \= ath\_row\[0\] or f"Athlete \#{{athlete\_id}}"

            ath\_sport \= ath\_row\[1\] or "Basketball"

            ath\_school \= ath\_row\[2\] or ""

            ath\_city \= ath\_row\[3\] or ""

            ath\_phone \= ath\_row\[4\] or "N/A"

            ath\_email \= ath\_row\[5\] or "N/A"

            loc\_str \= f" \- {{ath\_school}} ({{ath\_city}})" if ath\_school or ath\_city else ""

            alert\_body \= (

                f"👀 EMAIL OPENED: {{ath\_name}} ({{ath\_sport}}{{loc\_str}}) just opened the campaign email\!\\\\n"

                f"📱 Phone: {{ath\_phone}}\\\\n"

                f"📧 Email: {{ath\_email}}\\\\n"

                f"Dennis, keep an eye out for their registration click\!"

            )

            cursor.execute("""

                INSERT INTO rec\_debut\_lead\_alerts

                (athlete\_id, athlete\_name, event\_type, target\_url, alert\_text, sent\_to\_phone, created\_at, is\_read)

                VALUES (?, ?, 'OPEN', 'EMAIL\_PIXEL', ?, '+1-616-291-5227', ?, 0\)

            """, (athlete\_id, ath\_name, alert\_body, now))

            threading.Thread(

                target=dispatch\_sms\_message,

                args=("+1-616-291-5227", alert\_body, "RecDebut Open Sentinel"),

                daemon=True

            ).start()

        conn.commit()

        conn.close()

    except Exception as e:

        print(f"\[TRACKING ERROR\] Open pixel logging failed: {{e}}")

    return Response(

        content=TRANSPARENT\_GIF\_BYTES,

        media\_type="image/gif",

        headers={{

            "Cache-Control": "no-cache, no-store, must-revalidate",

            "Pragma": "no-cache",

            "Expires": "0"

        }}

    )

@router.get("/track/click/{{campaign\_id}}/{{athlete\_id}}")

@legacy\_router.get("/track/click/{{campaign\_id}}/{{athlete\_id}}")

async def track\_email\_click(campaign\_id: str, athlete\_id: int, request: Request, url: Optional\[str\] \= "{rd\_reg}"):

    """

    Click redirect wrapper for outreach emails and short SMS links.

    Logs click event, increments athlete click counter, alerts Dennis Bell, and redirects to destination URL.

    """

    now \= time.time()

    dest\_url \= url or "{rd\_reg}"

    client\_ip \= request.headers.get("x-forwarded-for") or (request.client.host if request.client else "")

    user\_agent \= request.headers.get("user-agent") or ""

    try:

        conn \= sqlite3.connect(str(DB\_PATH))

        cursor \= conn.cursor()

        cursor.execute("""

            INSERT INTO rec\_debut\_tracking\_events

            (campaign\_id, athlete\_id, event\_type, target\_url, ip\_address, user\_agent, created\_at)

            VALUES (?, ?, 'CLICK', ?, ?, ?, ?)

        """, (campaign\_id, athlete\_id, dest\_url, client\_ip, user\_agent, now))

        cursor.execute("""

            UPDATE rec\_debut\_athletes

            SET click\_count \= COALESCE(click\_count, 0\) \+ 1, last\_clicked\_at \= ?

            WHERE id \= ?

        """, (now, athlete\_id))

        cursor.execute("SELECT name, sport, high\_school, city\_state, phone, email FROM rec\_debut\_athletes WHERE id \= ?", (athlete\_id,))

        ath\_row \= cursor.fetchone()

        ath\_name \= ath\_row\[0\] if ath\_row and ath\_row\[0\] else f"Athlete \#{{athlete\_id}}"

        ath\_sport \= ath\_row\[1\] if ath\_row and ath\_row\[1\] else "Basketball"

        ath\_school \= ath\_row\[2\] if ath\_row and ath\_row\[2\] else ""

        ath\_city \= ath\_row\[3\] if ath\_row and ath\_row\[3\] else ""

        ath\_phone \= ath\_row\[4\] if ath\_row and ath\_row\[4\] else ""

        ath\_email \= ath\_row\[5\] if ath\_row and ath\_row\[5\] else ""

        loc\_str \= f" \- {{ath\_school}} ({{ath\_city}})" if ath\_school or ath\_city else ""

        alert\_body \= (

            f"🔥 HOT RECRUIT LEAD: {{ath\_name}} ({{ath\_sport}}{{loc\_str}}) clicked registration link {{dest\_url}}\!\\\\n"

            f"📱 Phone: {{ath\_phone}}\\\\n"

            f"📧 Email: {{ath\_email}}\\\\n"

            f"Dennis, call while they are active\!"

        )

        cursor.execute("""

            INSERT INTO rec\_debut\_lead\_alerts

            (athlete\_id, athlete\_name, event\_type, target\_url, alert\_text, sent\_to\_phone, created\_at, is\_read)

            VALUES (?, ?, 'CLICK', ?, ?, '+1-616-291-5227', ?, 0\)

        """, (athlete\_id, ath\_name, dest\_url, alert\_body, now))

        conn.commit()

        conn.close()

        threading.Thread(

            target=dispatch\_sms\_message,

            args=("+1-616-291-5227", alert\_body, "RecDebut Lead Sentinel"),

            daemon=True

        ).start()

    except Exception as e:

        print(f"\[TRACKING ERROR\] Click logging failed: {{e}}")

    return RedirectResponse(url=dest\_url, status\_code=302)

@router.get("/r/{{athlete\_id}}")

@legacy\_router.get("/r/{{athlete\_id}}")

async def short\_sms\_tracking\_redirect(athlete\_id: int, request: Request, url: Optional\[str\] \= "{rd\_reg}"):

    """

    36-character short tracking endpoint: /r/{{athlete\_id}}

    Logs click, alerts Dennis Bell (+1-616-291-5227), and redirects to registration.

    """

    return await track\_email\_click(

        campaign\_id="sms\_shortlink",

        athlete\_id=athlete\_id,

        request=request,

        url=url or "{rd\_reg}"

    )

'''

    new\_src \= before\_section \+ upgraded\_telemetry\_section \+ after\_section

    \# 3\. Validate Python AST Syntax before writing

    try:

        ast.parse(new\_src)

        print("\[AST CHECK\] Syntax verified cleanly.")

    except SyntaxError as syn\_err:

        print(f"\[AST ERROR\] Syntax validation failed: {syn\_err}")

        return False

    ROUTER\_PATH.write\_text(new\_src, encoding="utf-8")

    print(f"\[SUCCESS\] Updated {ROUTER\_PATH} successfully.")

    return True

if \_\_name\_\_ \== "\_\_main\_\_":

    ok \= patch\_rec\_debut\_router()

    sys.exit(0 if ok else 1\)

# **How to Extract & Run After Downloading as `.md`**

Once you download this Google Doc as a Markdown file (`File -> Download -> Markdown (.md)`), run this command in PowerShell to automatically extract the Python code into C:\\AI-BS\\apply\_rec\_debut\_upgrade.py and execute it:\$mdPath \= "\$HOME\\Downloads\\RecDebut\_Tracking\_Upgrade\_Patch\_Script.md"

\$md \= Get-Content \$mdPath \-Raw

if (\$md \-match '(?s)\`\`\`python\\r?\\n(.\*?)\\r?\\n\`\`\`') {

    Set-Content \-Path "C:\\AI-BS\\apply\_rec\_debut\_upgrade.py" \-Value \$matches\[1\] \-Encoding UTF8

    python "C:\\AI-BS\\apply\_rec\_debut\_upgrade.py"

}  
