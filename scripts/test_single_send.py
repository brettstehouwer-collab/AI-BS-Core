import smtplib
from email.mime.text import MIMEText

s = smtplib.SMTP("smtp.gmail.com", 587)
s.starttls()
s.login("brettstehouwer@gmail.com", "tngtxhpdgunzjiva")
msg = MIMEText("test", "plain")
msg["From"] = "brettstehouwer@gmail.com"
msg["To"] = "josh.smith01@gmail.com"
try:
    s.sendmail("brettstehouwer@gmail.com", ["josh.smith01@gmail.com"], msg.as_string())
    print("Sent OK from brettstehouwer!")
except Exception as e:
    print("Error from brettstehouwer:", e)
s.quit()
