import os
import sys
import subprocess
import shutil


def main():
    print("==================================================")
    # 1. Ensure PyInstaller is installed in the active venv
    try:
        print("[Build] PyInstaller is already installed.")
    except ImportError:
        print("[Build] PyInstaller not found. Installing in active environment...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "pyinstaller"], check=True
        )

    backend_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(backend_dir)

    # Clean previous builds
    print("[Build] Cleaning old build/dist directories...")
    if os.path.exists("build"):
        shutil.rmtree("build", ignore_errors=True)
    for f in [
        os.path.join("dist", "AI-BS.exe"),
        os.path.join("dist", "AI-BS_Setup.exe"),
    ]:
        if os.path.exists(f):
            try:
                os.remove(f)
            except Exception as e:
                print(f"[Warning] Could not remove {f}: {e}")

    # 2. Build the main production launcher
    print("[Build] Compiling AI-BS Production Launcher...")
    subprocess.run([sys.executable, "-m", "PyInstaller", "AI-BS.spec"], check=True)

    launcher_exe = os.path.join(backend_dir, "dist", "AI-BS.exe")
    if not os.path.exists(launcher_exe):
        print("[Error] Failed to compile AI-BS.exe")
        sys.exit(1)
    print(f"[Build] AI-BS.exe compiled successfully: {launcher_exe}")

    # 3. Generate Code Signing Certificate (if missing)
    pfx_path = os.path.join(backend_dir, "stehouwer_code_signing.pfx")
    pfx_password = "Stehouwer2026!"

    if not os.path.exists(pfx_path):
        print("[Signing] Generating self-signed code signing certificate...")
        ps_gen_cert = f"""
        $cert = New-SelfSignedCertificate -Type CodeSigningCert -Subject "CN=Stehouwer Advertising, O=Stehouwer Advertising, C=US" -KeyUsage DigitalSignature -FriendlyName "Stehouwer Advertising Code Signing" -CertStoreLocation Cert:\\CurrentUser\\My
        $password = ConvertTo-SecureString "{pfx_password}" -AsPlainText -Force
        Export-PfxCertificate -Cert $cert -FilePath "{pfx_path}" -Password $password
        """
        subprocess.run(["powershell", "-Command", ps_gen_cert], check=True)
        print(f"[Signing] Certificate generated and saved to: {pfx_path}")
    else:
        print(f"[Signing] Using existing certificate: {pfx_path}")

    # 4. Sign the main launcher
    print("[Signing] Cryptographically signing AI-BS.exe...")
    ps_sign_launcher = f"""
    $cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2("{pfx_path}", "{pfx_password}")
    Set-AuthenticodeSignature -FilePath "{launcher_exe}" -Certificate $cert -HashAlgorithm SHA256
    """
    subprocess.run(["powershell", "-Command", ps_sign_launcher], check=True)

    # 5. Build the setup wizard (bundling the signed launcher)
    print("[Build] Compiling AI-BS Setup Wizard (bundling signed launcher)...")
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", "AI-BS_Setup.spec"], check=True
    )

    setup_exe = os.path.join(backend_dir, "dist", "AI-BS_Setup.exe")
    if not os.path.exists(setup_exe):
        print("[Error] Failed to compile AI-BS_Setup.exe")
        sys.exit(1)
    print(f"[Build] AI-BS_Setup.exe compiled successfully: {setup_exe}")

    # 6. Sign the setup wizard
    print("[Signing] Cryptographically signing AI-BS_Setup.exe...")
    ps_sign_setup = f"""
    $cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2("{pfx_path}", "{pfx_password}")
    Set-AuthenticodeSignature -FilePath "{setup_exe}" -Certificate $cert -HashAlgorithm SHA256
    """
    subprocess.run(["powershell", "-Command", ps_sign_setup], check=True)

    # 7. Verify signatures
    print("\n==================================================")
    print("[Verification] Verifying Authenticode Signatures...")
    print("==================================================")

    ps_verify = f"""
    Get-AuthenticodeSignature -FilePath "{launcher_exe}", "{setup_exe}" | Format-Table -Property Path, Status, StatusMessage
    """
    subprocess.run(["powershell", "-Command", ps_verify])


if __name__ == "__main__":
    main()
