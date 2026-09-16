import asyncio
import sys
from core.lost_property_scanner import run_web_osint_scan

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    email = "Stehouwer@gmail.com"
    print(f"Running OSINT scan for {email}...")
    result = run_web_osint_scan(email, scan_type="all")
    print(result)
