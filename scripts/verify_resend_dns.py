import subprocess
import sys
import time

def check_dns():
    print("=== Checking DNS Propagation for recdebut.com ===")
    records = [
        ("resend._domainkey.recdebut.com", "TXT"),
        ("rsend.recdebut.com", "CNAME"),
        ("send.recdebut.com", "CNAME")
    ]
    
    all_ready = True
    for name, rtype in records:
        cmd = ["powershell", "-Command", f"Resolve-DnsName -Name {name} -Type {rtype} -Server 8.8.8.8 -ErrorAction SilentlyContinue"]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
            out = res.stdout.strip()
            if out and ("Strings" in out or "NameHost" in out or name in out):
                print(f"[FOUND] {rtype} {name}")
                for line in out.splitlines():
                    if any(k in line for k in ["Strings", "NameHost", "resend", "rmta.net"]):
                        print(f"        -> {line.strip()}")
            else:
                print(f"[PENDING] {rtype} {name} (Not detected yet)")
                all_ready = False
        except Exception as e:
            print(f"[ERROR] Checking {name}: {e}")
            all_ready = False

    return all_ready

if __name__ == "__main__":
    ready = check_dns()
    if ready:
        print("\nAll DNS records are live and propagated! You can now click 'Verify Records' in Resend.")
    else:
        print("\nRecords are still pending propagation. Add them in Hostinger and re-run this check.")
