import smtplib
import email.utils
from email.mime.text import MIMEText

sender_email = 'brettstehouwer@gmail.com'
app_password = 'tngtxhpdgunzjiva'
recipient = 'brettstehouwer@gmail.com'

msg = MIMEText("Hey Brett,\n\nYour account brettstehouwer@gmail.com is now officially verified and connected to AI-BS as an active SMTP Swarm gateway!\n\nAll systems operational.\n\n- AI-BS Ecosystem", "plain", "utf-8")
msg["Subject"] = "AI-BS Gateway Connected: brettstehouwer@gmail.com"
msg["From"] = f"AI-BS Sovereign Node <{sender_email}>"
msg["To"] = recipient
msg["Reply-To"] = "dbell002@sbcglobal.net"
msg["Date"] = email.utils.formatdate(localtime=True)

try:
    server = smtplib.SMTP('smtp.gmail.com', 587, timeout=10.0)
    server.ehlo()
    server.starttls()
    server.ehlo()
    server.login(sender_email, app_password)
    server.sendmail(sender_email, [recipient], msg.as_string())
    server.quit()
    print("SUCCESS: Live test email delivered from brettstehouwer@gmail.com!")
except Exception as e:
    print(f"FAILED: {e}")
