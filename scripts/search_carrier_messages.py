import sys
import imaplib
import email
from pathlib import Path
sys.path.insert(0, str(Path("backend").resolve()))
from routers.rec_debut_router import load_credentials, decode_mime_words, extract_email_body

creds = load_credentials()
imap_user = creds.get("IMAP_USER", "footballstar0325@gmail.com")
imap_pwd = creds.get("IMAP_APP_PASSWORD", "dnbmziwbtrfgfeht")

print("Logging in to IMAP...", flush=True)
mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
mail.login(imap_user, imap_pwd)
mail.select("INBOX", readonly=True)

# Search recent messages since 15-Oct-2026
print("Searching messages since 15-Oct-2026...", flush=True)
s, res = mail.search(None, '(SINCE "15-Oct-2026")')
if s == "OK" and res[0]:
    ids = res[0].split()
    print(f"Total messages since 15-Oct-2026: {len(ids)}", flush=True)
    
    carrier_domains = [
        "vzwpix.com", "vtext.com", "mms.att.net", "txt.att.net",
        "tmomail.net", "mms.cricketwireless.net", "myboostmobile.com",
        "mms.uscc.net", "msg.fi.google.com"
    ]
    
    # Check messages
    for mid in reversed(ids):
        s2, data = mail.fetch(mid, "(RFC822)")
        if s2 != "OK" or not data or not data[0]:
            continue
        msg = email.message_from_bytes(data[0][1])
        frm = decode_mime_words(msg.get("From", "")).lower()
        to = decode_mime_words(msg.get("To", "")).lower()
        subj = decode_mime_words(msg.get("Subject", ""))
        
        # Check if from carrier domain or not a mailer-daemon/delivery failure
        is_carrier = any(cd in frm for cd in carrier_domains)
        is_bounce = "mailer-daemon" in frm or "postmaster" in frm or "failure" in subj.lower()
        
        if is_carrier or ("recdebut" in subj.lower() or "dennis" in subj.lower() or "debut" in subj.lower()):
            dt = msg.get("Date", "")
            bdy = extract_email_body(msg)[:200].replace('\n', ' ')
            print(f"\n[MATCH {mid.decode()}] From: {frm} | To: {to} | Date: {dt}", flush=True)
            print(f"Subject: {subj}", flush=True)
            print(f"Is Carrier: {is_carrier} | Is Bounce: {is_bounce}", flush=True)
            print(f"Body: {bdy}", flush=True)

mail.logout()
print("\nDone.", flush=True)
