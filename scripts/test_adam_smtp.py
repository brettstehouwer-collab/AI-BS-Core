import smtplib

def test_login():
    email = "adamstehouwer24@gmail.com"
    app_pwd = "tghxprhndaddvobb"
    print(f"Testing SMTP login for: {email}...")
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587, timeout=10)
        server.starttls()
        server.login(email, app_pwd)
        print("SUCCESS! Credentials authenticated with Google SMTP 100%!")
        server.quit()
        return True
    except Exception as e:
        print(f"FAILED to authenticate: {e}")
        return False

if __name__ == '__main__':
    test_login()
