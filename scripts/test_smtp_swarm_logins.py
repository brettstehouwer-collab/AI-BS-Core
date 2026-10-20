import smtplib
import ssl

accounts = [
    {
        "id": "acct_adam",
        "email": "adamstehouwer24@gmail.com",
        "app_password": "tghxprhndaddvobb"
    },
    {
        "id": "acct_brett",
        "email": "brettstehouwer@gmail.com",
        "app_password": "tngtxhpdgunzjiva"
    },
    {
        "id": "acct_football",
        "email": "footballstar0325@gmail.com",
        "app_password": "xpmeqidiezqqvfku"
    },
    {
        "id": "acct_noco",
        "email": "brett.noco.letsgo.stehouwer@gmail.com",
        "app_password": "aheuozzanotbdttd"
    }
]

print("=== Testing SMTP Login for All Swarm Accounts ===")
for acct in accounts:
    email_addr = acct["email"]
    pwd = acct["app_password"]
    try:
        context = ssl.create_default_context()
        server = smtplib.SMTP("smtp.gmail.com", 587, timeout=10)
        server.ehlo()
        server.starttls(context=context)
        server.ehlo()
        server.login(email_addr, pwd)
        server.quit()
        print(f"[SUCCESS] {email_addr} authenticated successfully!")
    except Exception as e:
        print(f"[FAILED]  {email_addr}: {e}")

