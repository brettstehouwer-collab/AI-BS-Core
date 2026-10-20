import smtplib
import socket

def test_smtp_rcpt(email_to_check):
    domain = email_to_check.split('@')[1]
    print(f"\n--- Testing SMTP Verification for: {email_to_check} ---")
    
    # Simple MX lookup using nslookup on Windows or socket
    import subprocess
    cmd = f"nslookup -type=mx {domain}"
    res = subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True)
    
    mx_host = None
    for line in res.stdout.splitlines():
        if "mail exchanger =" in line:
            mx_host = line.split("mail exchanger =")[1].strip().rstrip('.')
            break
            
    if not mx_host:
        print(f"Could not find MX host for {domain}, falling back to domain itself")
        mx_host = domain
    else:
        print(f"Found Primary MX: {mx_host}")
        
    try:
        server = smtplib.SMTP(timeout=10)
        server.connect(mx_host, 25)
        server.helo("brettstehouwer.live")
        server.mail("verify@brettstehouwer.live")
        code, msg = server.rcpt(email_to_check)
        server.quit()
        
        msg_str = msg.decode('utf-8', errors='ignore') if isinstance(msg, bytes) else str(msg)
        print(f"Result for {email_to_check}: Code={code}, Message={msg_str}")
        if code == 250:
            print("=> VERIFIED: Mailbox exists and accepts mail!")
        elif code >= 500:
            print(f"=> INVALID: Mailbox rejected (Code {code})")
        else:
            print(f"=> STATUS: Code {code}")
    except Exception as e:
        print(f"Error during SMTP handshake: {e}")

if __name__ == '__main__':
    # Test a known valid address
    test_smtp_rcpt("brettstehouwer@gmail.com")
    # Test a known non-existent address
    test_smtp_rcpt("thisuserdefinitelydoesnotexist9918237@gmail.com")
