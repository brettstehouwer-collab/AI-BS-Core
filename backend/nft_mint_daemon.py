import os
import json
import hashlib
import logging
from pathlib import Path
from dotenv import load_dotenv

# Optional: Using httpx for RPC calls if needed, otherwise subprocess wrapper
import subprocess

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("NFTMinter")

# Load configuration
ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(ENV_PATH)

CHIA_NFT_FINGERPRINT = os.getenv("CHIA_NFT_FINGERPRINT", "")
ROYALTY_PCT = int(os.getenv("NFT_ROYALTY_PERCENTAGE", "500"))  # 500 = 5%
ROYALTY_ADDR = os.getenv("NFT_ROYALTY_ADDRESS", "")


def sha256_file(filepath: str) -> str:
    """Calculate SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def generate_chip0007_metadata(
    name: str,
    description: str,
    collection_name: str,
    collection_id: str,
    attributes: list,
    output_path: str,
) -> str:
    """
    Generate CHIP-0007 compliant JSON metadata for the NFT.
    """
    metadata = {
        "format": "CHIP-0007",
        "name": name,
        "description": description,
        "minting_tool": "AI-BS Matrix NFT Minter",
        "sensitive_content": False,
        "series_number": 1,
        "series_total": 1,
        "attributes": attributes,
        "collection": {"name": collection_name, "id": collection_id, "attributes": []},
    }

    with open(output_path, "w") as f:
        json.dump(metadata, f, indent=4)

    logger.info(f"Generated CHIP-0007 metadata at {output_path}")
    return sha256_file(output_path)


async def check_or_create_did() -> str:
    """
    Check if a DID wallet exists. If not, create one.
    Requires the wallet to be fully synced and have a balance (dust).
    Returns the DID ID.
    """
    logger.info("Checking for existing DID wallets...")

    # Using chia rpc or CLI wrapper
    # chia wallet get_wallets
    try:
        result = subprocess.run(
            ["chia", "wallet", "get_wallets", "-f", CHIA_NFT_FINGERPRINT],
            capture_output=True,
            text=True,
            check=True,
        )
        output = result.stdout

        # Simple parse for Decentralized ID Wallet
        if "DID Wallet" in output:
            logger.info("DID Wallet already exists.")
            # We would extract the DID ID here in a full RPC implementation
            return "did:chia:existing_did_here"
        else:
            logger.info("No DID found. Attempting to create one (requires 1 mojo)...")
            # chia wallet did create -n "AI-BS DID"
            create_res = subprocess.run(
                [
                    "chia",
                    "wallet",
                    "did",
                    "create",
                    "-n",
                    "AI-BS_DID",
                    "-f",
                    CHIA_NFT_FINGERPRINT,
                ],
                capture_output=True,
                text=True,
            )
            if create_res.returncode == 0:
                logger.info(
                    "Successfully requested DID creation. Waiting for blockchain confirmation."
                )
                return "did:chia:pending"
            else:
                logger.error(f"Failed to create DID: {create_res.stderr}")
                return ""
    except Exception as e:
        logger.error(f"Error communicating with chia daemon: {e}")
        return ""


async def mint_nft(
    wallet_id: int,
    royalty_address: str,
    royalty_pct: int,
    data_uris: list,
    data_hash: str,
    meta_uris: list,
    meta_hash: str,
    license_uris: list,
    license_hash: str,
    did_id: str = "",
):
    """
    Mint the actual NFT using the chia wallet command.
    """
    cmd = [
        "chia",
        "wallet",
        "nft",
        "mint",
        "-f",
        CHIA_NFT_FINGERPRINT,
        "-i",
        str(wallet_id),
        "-ra",
        royalty_address,
        "-rp",
        str(royalty_pct),
        "-nh",
        data_hash,
        "-mh",
        meta_hash,
        "-lh",
        license_hash,
    ]

    for uri in data_uris:
        cmd.extend(["-u", uri])
    for uri in meta_uris:
        cmd.extend(["-mu", uri])
    for uri in license_uris:
        cmd.extend(["-lu", uri])

    if did_id and not did_id.endswith("pending"):
        cmd.extend(["-di", did_id])

    logger.info(f"Minting NFT with command: {' '.join(cmd)}")

    try:
        # In a real environment, wait for transaction confirmation
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            logger.info("NFT Mint transaction submitted successfully!")
            logger.info(result.stdout)
        else:
            logger.error(f"NFT Mint failed: {result.stderr}")
    except Exception as e:
        logger.error(f"Exception during minting: {e}")


if __name__ == "__main__":
    logger.info("AI-BS Matrix: NFT Minting Daemon Initialized.")
    # This daemon is meant to be invoked externally via the AI-BS Backend API
    # or scripts.
