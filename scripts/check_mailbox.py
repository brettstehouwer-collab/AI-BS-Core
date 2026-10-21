import sys
import imaplib
import email
from email.header import decode_header
from pathlib import Path
sys.path.insert(0, str(Path("backend").resolve()))
from routers.rec_debut_router import load_credentials, decode_mime_words, extract_email_body

creds = load_credentials()
imap_user = creds.get("IMAP_USER", "footballstar0325@gmail.com")
imap_pwd = creds.get("IMAP_APP_PASSWORD", "dnbmziwbtrfgfeht")

mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
mail.login(imap_user, imap_pwd)
mail.select("INBOX", readonly=True)

# Search last 30 messages
status, res = mail.search(None, 'ALL')
if status == "OK" and res[0]:
    all_ids = res[0].split()
    print(f"Total messages in INBOX: {len(all_ids)}")
    recent_ids = all_ids[-30:]
    for mid in reversed(recent_ids):
        s, data = mail.fetch(mid, "(RFC822)")
        if s != "OK" or not data or not data[0]:
            continue
        msg = email.message_from_bytes(data[0][1])
        from_hdr = decode_mime_words(msg.get("From", ""))
        to_hdr = decode_mime_words(msg.get("To", ""))
        subject_hdr = decode_mime_words(msg.get("Subject", ""))
        date_hdr = msg.get("Date", "")
        # print first 100 chars of body
        body = extract_email_body(msg)[:100].replace('\n', ' ')
        print(f"ID: {mid.decode()} | From: {from_hdr} | To: {to_hdr} | Subj: {subject_hdr} | Date: {date_hdr}")
        print(f"   Body preview: {body}\n")
mail.logout()
