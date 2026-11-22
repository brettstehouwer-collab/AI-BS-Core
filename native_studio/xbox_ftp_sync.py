import ftplib
import os
import sys
import time

class XboxFTPSync:
    def __init__(self, host="192.168.10.2", port=21, user="anonymous", passwd=""):
        self.host = host
        self.port = port
        self.user = user
        self.passwd = passwd
        self.ftp = None

    def connect(self):
        try:
            self.ftp = ftplib.FTP()
            self.ftp.connect(self.host, self.port, timeout=5)
            self.ftp.login(self.user, self.passwd)
            print(f"[+] Connected to Xbox FTP at {self.host}:{self.port}")
            print(f"[*] Server banner: {self.ftp.getwelcome()}")
            return True
        except Exception as e:
            print(f"[-] Could not connect to FTP on Xbox: {e}")
            print("    (Ensure DurangoFTP, OpenFTP, or an FTP server app is open on the console)")
            return False

    def upload_file(self, local_path, remote_path):
        if not self.ftp:
            if not self.connect():
                return False
        
        file_size = os.path.getsize(local_path)
        start = time.time()
        print(f"[*] Uploading {os.path.basename(local_path)} ({file_size / (1024*1024):.2f} MB)...")
        with open(local_path, "rb") as f:
            self.ftp.storbinary(f"STOR {remote_path}", f, blocksize=65536)
        elapsed = time.time() - start
        speed_mb = (file_size / (1024 * 1024)) / max(elapsed, 0.001)
        print(f"[+] Upload complete in {elapsed:.2f}s (~{speed_mb:.2f} MB/s)")
        return True

    def list_dir(self, remote_dir="/"):
        if not self.ftp:
            if not self.connect():
                return []
        print(f"[*] Directory listing of {remote_dir}:")
        return self.ftp.dir(remote_dir)

if __name__ == "__main__":
    client = XboxFTPSync()
    client.connect()
