#!/usr/bin/env python3
import time
import jwt
import os

# Your GitHub App configuration
GITHUB_CLIENT_ID = "Iv23likCtBlZIeMCxygd"
GITHUB_APP_ID = "4046662"

def generate_github_jwt(pem_file_path: str, client_id: str = GITHUB_CLIENT_ID) -> str:
    """
    Generates a JSON Web Token (JWT) to authenticate as a GitHub App.
    """
    if not os.path.exists(pem_file_path):
        raise FileNotFoundError(f"Cannot find the private key file at: {pem_file_path}")

    with open(pem_file_path, 'rb') as pem_file:
        signing_key = pem_file.read()

    # Create the payload according to GitHub's JWT specification
    payload = {
        # Issued at time (60 seconds in the past to account for clock drift)
        'iat': int(time.time()) - 60,
        # JWT expiration time (10 minutes maximum)
        'exp': int(time.time()) + 600,
        # GitHub App's client ID (iss)
        'iss': client_id
    }

    # Create and sign the JWT
    encoded_jwt = jwt.encode(payload, signing_key, algorithm='RS256')
    return encoded_jwt

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate a GitHub App JWT.")
    parser.add_argument("--pem", required=True, help="Path to the downloaded .pem private key file")
    
    args = parser.parse_args()
    
    try:
        token = generate_github_jwt(args.pem)
        print("\n=== SUCCESS ===")
        print("Your GitHub App JWT is:\n")
        print(token)
        print("\nNote: This token is valid for 10 minutes.")
    except Exception as e:
        print(f"Error: {e}")
