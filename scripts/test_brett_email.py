import smtplib

try:
    server = smtplib.SMTP('smtp.gmail.com', 587, timeout=10.0)
    server.ehlo()
    server.starttls()
    server.ehlo()
    server.login('brettstehouwer@gmail.com', 'dnbmziwbtrfgfeht')
    print("SUCCESS: brettstehouwer@gmail.com authenticated with dnbmziwbtrfgfeht")
    server.quit()
except Exception as e:
    print(f"FAILED: {e}")
