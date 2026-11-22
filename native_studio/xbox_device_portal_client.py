import requests
import json
import urllib3
import sys
import os

# Suppress self-signed certificate warnings for Xbox Device Portal
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class XboxDevicePortalClient:
    def __init__(self, host="192.168.10.2", port=11443, username="", password=""):
        self.base_url = f"https://{host}:{port}"
        self.session = requests.Session()
        self.session.verify = False
        if username and password:
            self.session.auth = (username, password)

    def test_connection(self):
        """Test if the Xbox Device Portal is reachable and responding."""
        try:
            r = self.session.get(f"{self.base_url}/api/os/info", timeout=3)
            return r.status_code == 200, r.json() if r.status_code == 200 else r.status_code
        except requests.exceptions.ConnectTimeout:
            return False, "Connection Timed Out (Ensure Xbox is in Developer Mode with Portal enabled)"
        except requests.exceptions.ConnectionError as e:
            return False, f"Connection Refused: {e}"

    def get_system_perf(self):
        """Get live CPU, GPU, memory, and thermal performance telemetry."""
        url = f"{self.base_url}/api/resourcemanager/systemperf"
        r = self.session.get(url, timeout=5)
        return r.json() if r.status_code == 200 else None

    def get_running_processes(self):
        """List active processes running on the console."""
        url = f"{self.base_url}/api/resourcemanager/processes"
        r = self.session.get(url, timeout=5)
        return r.json() if r.status_code == 200 else None

    def install_app_package(self, package_path):
        """Install an .appx or .msix package over Ethernet."""
        if not os.path.exists(package_path):
            raise FileNotFoundError(f"Package not found: {package_path}")

        filename = os.path.basename(package_path)
        url = f"{self.base_url}/api/app/packagemanager/package?package={filename}"
        with open(package_path, "rb") as f:
            headers = {"Content-Type": "application/octet-stream"}
            r = self.session.post(url, data=f, headers=headers, timeout=60)
            return r.status_code, r.text

    def reboot(self):
        """Reboot the Xbox console remotely."""
        url = f"{self.base_url}/api/control/restart"
        r = self.session.post(url, timeout=5)
        return r.status_code == 200

if __name__ == "__main__":
    client = XboxDevicePortalClient()
    print("Testing connection to Xbox Device Portal (192.168.10.2:11443)...")
    ok, res = client.test_connection()
    if ok:
        print(f"[+] Device Portal Connected! Info: {json.dumps(res, indent=2)}")
    else:
        print(f"[-] Status: {res}")
