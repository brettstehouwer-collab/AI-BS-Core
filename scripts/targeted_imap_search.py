import sys
import imaplib
import email
from pathlib import Path
sys.path.insert(0, str(Path("backend").resolve()))
from routers.rec_debut_router import load_credentials, decode_mime_words, extract_email_body

creds = load_credentials()
imap_user = creds.get("IMAP_USER", "footballstar0325@gmail.com")
imap_pwd = creds.get("IMAP_APP_PASSWORD", "dnbmziwbtrfgfeht")

mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
mail.login(imap_user, imap_pwd)
mail.select("INBOX", readonly=True)

carrier_domains = [
    "vzwpix.com", "vtext.com", "mms.att.net", "txt.att.net",
    "tmomail.net", "mms.cricketwireless.net", "myboostmobile.com",
    "mms.uscc.net", "msg.fi.google.com"
]

found_msgs = []
for gw in carrier_domains:
    s, res = mail.search(None, f'(FROM "{gw}" SINCE "15-Oct-2026")')
    if s == "OK" and res[0]:
        ids = res[0].split()
        print(f"FROM {gw}: {len(ids)} messages")
        for mid in ids:
            found_msgs.append(mid)

s, res = mail.search(None, '(SUBJECT "Re:" SINCE "15-Oct-2026")')
if s == "OK" and res[0]:
    ids = res[0].split()
    print(f"SUBJECT 'Re:': {len(ids)} messages")
    for mid in ids:
        found_msgs.append(mid)

unique_ids = list(set(found_msgs))
print(f"Total candidate messages to inspect: {len(unique_ids)}")

for mid in unique_ids:
    s, data = mail.fetch(mid, "(RFC822)")
    if s != "OK" or not data or not data[0]:
        continue
    msg = email.message_from_bytes(data[0][1])
    frm = decode_mime_words(msg.get("From", ""))
    to = decode_mime_words(msg.get("To", ""))
    subj = decode_mime_words(msg.get("Subject", ""))
    dt = msg.get("Date", "")
    bdy = extract_email_body(msg)[:250].replace('\n', ' ')
    print(f"\n--- ID {mid.decode()} ---")
    print(f"From: {frm}")
    print(f"To: {to}")
    print(f"Subj: {subj}")
    print(f"Date: {dt}")
    print(f"Body: {bdy}")

mail.logout()
