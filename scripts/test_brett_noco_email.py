import smtplib

email_user = 'brett.noco.letsgo.stehouwer@gmail.com'
app_password = 'aheuozzanotbdttd'

try:
    print(f"Connecting to smtp.gmail.com:587 for {email_user}...")
    server = smtplib.SMTP('smtp.gmail.com', 587, timeout=10.0)
    server.ehlo()
    server.starttls()
    server.ehlo()
    server.login(email_user, app_password)
    print("SUCCESS: brett.noco.letsgo.stehouwer@gmail.com authenticated successfully with Google SMTP!")
    server.quit()
except Exception as e:
    print(f"FAILED: {e}")
