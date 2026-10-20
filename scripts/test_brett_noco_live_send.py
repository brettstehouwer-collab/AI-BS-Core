import smtplib
import email.utils
from email.mime.text import MIMEText

sender_email = 'brett.noco.letsgo.stehouwer@gmail.com'
app_password = 'aheuozzanotbdttd'
recipient = 'brett.noco.letsgo.stehouwer@gmail.com'

msg = MIMEText("Hey Brett,\n\nYour account brett.noco.letsgo.stehouwer@gmail.com is now officially verified and connected to AI-BS as Swarm Gateway #3!\n\nAll systems operational.\n\n- AI-BS Ecosystem", "plain", "utf-8")
msg["Subject"] = "AI-BS Gateway #3 Connected: brett.noco.letsgo.stehouwer@gmail.com"
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
    print("SUCCESS: Live test email delivered from brett.noco.letsgo.stehouwer@gmail.com!")
except Exception as e:
    print(f"FAILED: {e}")
