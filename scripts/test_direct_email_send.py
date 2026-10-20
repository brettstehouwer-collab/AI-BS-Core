import smtplib
from email.mime.text import MIMEText

print("Testing direct email send ability:")
for email_addr, pwd in [
    ("adamstehouwer24@gmail.com", "tghxprhndaddvobb"),
    ("brettstehouwer@gmail.com", "tngtxhpdgunzjiva")
]:
    try:
        s = smtplib.SMTP("smtp.gmail.com", 587, timeout=10.0)
        s.ehlo()
        s.starttls()
        s.ehlo()
        s.login(email_addr, pwd)
        msg = MIMEText("Testing direct single recipient send", "plain", "utf-8")
        msg["From"] = "Dennis Bell (616-291-5227) <dbell002@sbcglobal.net>"
        msg["To"] = "BrettStehouwer@gmail.com"
        msg["Subject"] = "Direct Email Test"
        s.sendmail(email_addr, ["BrettStehouwer@gmail.com"], msg.as_string())
        s.quit()
        print(f"[OK] {email_addr}: Successfully sent single direct email!")
    except Exception as e:
        print(f"[FAIL] {email_addr}: Error: {e}")
