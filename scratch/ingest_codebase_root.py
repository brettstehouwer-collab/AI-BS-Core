import os
from pathlib import Path

DEFAULT_ROOT_DIR = r"C:\AI-BS"
DEFAULT_VECTOR_STORE = r"C:\AI-BS\stehouwer_vector_memory"

def main():
    print(f"Ingestion configured for Root Directory: {DEFAULT_ROOT_DIR}")
    print(f"Target Vector Vault: {DEFAULT_VECTOR_STORE}")
    # TODO: Implement traversal and embedding logic

if __name__ == "__main__":
    main()
