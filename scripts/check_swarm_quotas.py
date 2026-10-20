import smtplib
import json
from email.mime.text import MIMEText

with open("saved_data/rec_debut_smtp_swarm.json", "r") as f:
    accounts = json.load(f)

print("Checking SMTP quota status across accounts in swarm:")
for acct in accounts:
    email_addr = acct["email"]
    pwd = acct["app_password"]
    host = acct.get("smtp_host", "smtp.gmail.com")
    port = int(acct.get("smtp_port", 587))
    print(f"\nTesting {email_addr}...")
    try:
        s = smtplib.SMTP(host, port, timeout=10.0)
        s.ehlo()
        s.starttls()
        s.ehlo()
        s.login(email_addr, pwd)
        # Try a test message to Dennis or Brett to see if 550 tripped
        msg = MIMEText("Quota health check", "plain", "utf-8")
        msg["From"] = f"Health Check <{email_addr}>"
        msg["To"] = "footballstar0325@gmail.com"
        msg["Subject"] = "Quota Check"
        s.sendmail(email_addr, ["footballstar0325@gmail.com"], msg.as_string())
        s.quit()
        print(f" -> {email_addr}: HEALTHY & ACTIVE (Sent test email successfully!)")
    except Exception as e:
        print(f" -> {email_addr}: Notice: {e}")
