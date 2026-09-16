import getpass
from argon2 import PasswordHasher
import os


def setup_master_login():
    print("=== Stehouwer Publishing AI : Master Login Setup ===")
    print("This will establish the Argon2id hash for your master UI access.")

    username = input("Enter Master Username (e.g., admin): ").strip()
    if not username:
        username = "admin"

    password = getpass.getpass(prompt="Enter Master Password: ")
    confirm = getpass.getpass(prompt="Confirm Master Password: ")

    if password != confirm:
        print("[ERROR] Passwords do not match. Aborting.")
        return

    print("\nGenerating Argon2id Hash (m=65536, t=3, p=4)... This may take a moment.")
    ph = PasswordHasher()
    secure_hash = ph.hash(password)

    key_path = os.path.join(os.path.dirname(__file__), "master_key.hash")

    with open(key_path, "w") as f:
        f.write(f"{username}\n{secure_hash}")

    print(f"\n[SUCCESS] Master identity established. Key locked in: {key_path}")
    print("Restart your backend to apply security protocols.")


if __name__ == "__main__":
    setup_master_login()
