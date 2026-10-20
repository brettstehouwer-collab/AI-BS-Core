import imaplib
import email

IMAP_SERVER = "imap.gmail.com"
IMAP_PORT = 993
IMAP_USER = "footballstar0325@gmail.com"
IMAP_PASSWORD = "dnbmziwbtrfgfeht"

def inspect_msg():
    mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
    mail.login(IMAP_USER, IMAP_PASSWORD)
    mail.select("INBOX", readonly=True)
    status, res = mail.search(None, '(FROM "vtext.com")')
    ids = res[0].split()
    if ids:
        mid = ids[-1]
        _, data = mail.fetch(mid, "(RFC822)")
        msg = email.message_from_bytes(data[0][1])
        print("From:", msg.get("From"))
        print("Subject:", msg.get("Subject"))
        print("Content-Type:", msg.get_content_type())
        
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                cdispo = str(part.get("Content-Disposition"))
                if ctype == "text/plain" and "attachment" not in cdispo:
                    charset = part.get_content_charset() or "utf-8"
                    body = part.get_payload(decode=True).decode(charset, errors="ignore")
                    break
        else:
            charset = msg.get_content_charset() or "utf-8"
            body = msg.get_payload(decode=True).decode(charset, errors="ignore")
        print("Body snippet:\n", body[:300])
    mail.logout()

if __name__ == "__main__":
    inspect_msg()
