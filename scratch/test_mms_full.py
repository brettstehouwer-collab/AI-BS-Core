import smtplib
import email.utils
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Load credentials
smtp_user = "footballstar0325@gmail.com"
smtp_pwd = "dnbmziwbtrfgfeht"
smtp_host = "smtp.gmail.com"
smtp_port = 587

recipient_digits = "6164023628"

# MMS Gateways that support long text (1000+ chars)
MMS_GATEWAYS = [
    f"{recipient_digits}@vzwpix.com",          # Verizon MMS
    f"{recipient_digits}@mms.att.net",          # AT&T MMS
    f"{recipient_digits}@tmomail.net",          # T-Mobile
    f"{recipient_digits}@mms.cricketwireless.net", # Cricket MMS
    f"{recipient_digits}@myboostmobile.com",    # Boost MMS
    f"{recipient_digits}@mms.uscc.net",         # US Cellular MMS
    f"{recipient_digits}@msg.fi.google.com",    # Google Fi
]

message_text = """CONGRATULATIONS! YOU’VE BEEN SELECTED TO GET YOUR ATHLETIC PORTFOLIO IN FRONT OF 850 COLLEGE COACHES NATIONWIDE!

I’m Dennis Bell, former New York Knick and President of Recreational Debut. We’ve helped more than 100 student-athletes get recruited, and now we want to help you get noticed.

If you’re serious about playing college sports, don’t wait for coaches to find you.
📱 Call or text: 616-291-5227
📧 Email: dbell002@sbcglobal.net
✅ Register FREE: RecDebut.com

College programs across the country are looking for talented student-athletes. That opportunity could include YOU.

Dennis Bell
Former New York Knicks
President, Recreational Debut
616-291-5227 • RecDebut.com • dbell002@sbcglobal.net"""

# Build message without subject to avoid truncating subject prepend
msg = MIMEText(message_text, "plain", "utf-8")
msg["From"] = "Brett Stehouwer <BrettStehouwer@gmail.com>"
msg["Reply-To"] = "BrettStehouwer@gmail.com"
msg["Date"] = email.utils.formatdate(localtime=True)

server = smtplib.SMTP(smtp_host, smtp_port, timeout=15.0)
server.ehlo()
server.starttls()
server.ehlo()
server.login(smtp_user, smtp_pwd)

print(f"Sending full MMS text to: {MMS_GATEWAYS}")
server.sendmail(smtp_user, MMS_GATEWAYS, msg.as_string())
server.quit()
print("Sent successfully via MMS gateways!")
