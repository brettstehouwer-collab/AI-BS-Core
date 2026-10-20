import imaplib
import email

IMAP_SERVER = "imap.gmail.com"
IMAP_PORT = 993
IMAP_USER = "footballstar0325@gmail.com"
IMAP_PASSWORD = "dnbmziwbtrfgfeht"

def check_carrier_gateways():
    mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
    mail.login(IMAP_USER, IMAP_PASSWORD)
    mail.select("INBOX", readonly=True)
    
    gateways = [
        "vzwpix.com", "vtext.com", "mms.att.net", "txt.att.net", 
        "tmomail.net", "mms.cricketwireless.net", "myboostmobile.com",
        "mms.uscc.net", "msg.fi.google.com"
    ]
    
    found_any = False
    for gw in gateways:
        status, res = mail.search(None, f'(FROM "{gw}")')
        ids = res[0].split()
        if ids:
            found_any = True
            print(f"Gateway {gw}: {len(ids)} messages found!")
            for mid in ids[-2:]:
                _, data = mail.fetch(mid, "(RFC822)")
                msg = email.message_from_bytes(data[0][1])
                print(f"  From: {msg.get('From')}")
                print(f"  To: {msg.get('To')}")
                print(f"  Subject: {msg.get('Subject')}")
                print(f"  Date: {msg.get('Date')}")
    if not found_any:
        print("No carrier gateway emails found yet in INBOX.")
    mail.logout()

if __name__ == "__main__":
    check_carrier_gateways()
