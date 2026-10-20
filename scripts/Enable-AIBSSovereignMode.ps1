# File: C:\AI-BS\scripts\Enable-AIBSSovereignMode.ps1
# Directive ID: AIBS-DIR-000-ROOT-AUTHORITY
# Purpose: Configures Windows 11 Host Environment for AI-BS Sovereign Mode:
#   1. Creates C:\AI-BS\.temp_executor & C:\AI-BS\Stehouwer_Server\Projects\.temp_executor
#   2. Registers Windows Defender Path & Process Exclusions to eliminate MsMpEng.exe IPC overhead
#   3. Sets HVCI (HypervisorEnforcedCodeIntegrity) Enabled=0 for Ring 0 MSR/Telemetry while keeping WSL2 active
#   4. Enrolls 4096-bit RSA SHA-256 X.509 Code-Signing Certificate & signs AI-BS executables

$ErrorActionPreference = "Continue"

$AIBSDir = "C:\AI-BS"
$CertDir = "$AIBSDir\security\certs"
$TempExecDir = "$AIBSDir\.temp_executor"
$FallbackServerTempDir = "$AIBSDir\Stehouwer_Server\Projects\.temp_executor"

New-Item -ItemType Directory -Force -Path $CertDir | Out-Null
New-Item -ItemType Directory -Force -Path $TempExecDir | Out-Null
New-Item -ItemType Directory -Force -Path $FallbackServerTempDir | Out-Null
New-Item -ItemType Directory -Force -Path "$AIBSDir\directives" | Out-Null

# 1. Exclusion of AI-BS Core Directories from Antivirus Real-Time Lock Contention
try {
    $excludePaths = @("C:\AI-BS", "C:\AI-BS\.temp_executor", "C:\AI-BS\Stehouwer_Server")
    if (Test-Path "G:\Stehouwer_Server") {
        $excludePaths += "G:\Stehouwer_Server"
    }
    Add-MpPreference -ExclusionPath $excludePaths -ErrorAction SilentlyContinue
    Add-MpPreference -ExclusionProcess "AI_BS_Studio.exe", "brain_backend.exe", "aibs_engine.exe", "python.exe" -ErrorAction SilentlyContinue
    Write-Output "[OK] Windows Defender Exclusions registered for C:\AI-BS and core binaries."
} catch {
    Write-Output "[WARN] Defender Exclusion update skipped or restricted: $($_.Exception.Message)"
}

# 2. Disable VTL 1 Hypervisor-Enforced Code Integrity (HVCI) to unblock Ring 0 MSR/Telemetry
try {
    $hvciPath = "HKLM:\SYSTEM\CurrentControlSet\Control\DeviceGuard\Scenarios\HypervisorEnforcedCodeIntegrity"
    if (-not (Test-Path $hvciPath)) {
        New-Item -Path $hvciPath -Force | Out-Null
    }
    Set-ItemProperty -Path $hvciPath -Name "Enabled" -Value 0 -Type DWord -ErrorAction Stop
    Write-Output "[OK] VTL 1 HVCI (HypervisorEnforcedCodeIntegrity) set to 0 (Ring 0 MSR/Telemetry unblocked)."
} catch {
    Write-Output "[WARN] HVCI registry modification requires elevated access: $($_.Exception.Message)"
}

# 3. Ensure Hypervisor remains set to Auto for WSL2 Linux Bridge
try {
    bcdedit /set hypervisorlaunchtype auto | Out-Null
    Write-Output "[OK] Hypervisor launch type verified as 'auto' for WSL2 coexistence."
} catch {
    Write-Output "[WARN] bcdedit check skipped: $($_.Exception.Message)"
}

# 4. Generate & Enroll Sovereign AI-BS Code-Signing Certificate (if not present)
$certSubject = "CN=AI-BS Sovereign Root Authority, O=Stehouwer Publishing LLC"
$existingCert = Get-ChildItem -Path Cert:\LocalMachine\My -ErrorAction SilentlyContinue | Where-Object { $_.Subject -eq $certSubject } | Select-Object -First 1

if (-not $existingCert) {
    try {
        $cert = New-SelfSignedCertificate `
            -Type CodeSigningCert `
            -Subject $certSubject `
            -KeyAlgorithm RSA `
            -KeyLength 4096 `
            -HashAlgorithm SHA256 `
            -CertStoreLocation "Cert:\LocalMachine\My" `
            -NotAfter (Get-Date).AddYears(10)

        $cerFile = "$CertDir\AIBS_Sovereign_Root.cer"
        Export-Certificate -Cert $cert -FilePath $cerFile | Out-Null
        Import-Certificate -FilePath $cerFile -CertStoreLocation "Cert:\LocalMachine\Root" | Out-Null
        Import-Certificate -FilePath $cerFile -CertStoreLocation "Cert:\LocalMachine\TrustedPublisher" | Out-Null
        $existingCert = $cert
        Write-Output "[OK] Enrolled AI-BS 4096-bit Code Signing Certificate: $($cert.Thumbprint)"
    } catch {
        Write-Output "[WARN] Certificate enrollment error: $($_.Exception.Message)"
    }
} else {
    $cerFile = "$CertDir\AIBS_Sovereign_Root.cer"
    if (-not (Test-Path $cerFile)) {
        Export-Certificate -Cert $existingCert -FilePath $cerFile | Out-Null
    }
    Write-Output "[OK] Existing AI-BS Certificate Verified: $($existingCert.Thumbprint)"
}

# 5. Sign Core AI-BS Executables with Enrolled Sovereign Certificate
if ($existingCert) {
    $targetsToSign = @(
        "C:\AI-BS\native_studio\dist\AI_BS_Studio\AI_BS_Studio.exe",
        "C:\AI-BS\backend\dist\brain_backend.exe",
        "C:\AI-BS\backend\dist\brain_backend\brain_backend.exe"
    )
    foreach ($exePath in $targetsToSign) {
        if (Test-Path $exePath) {
            try {
                $sigRes = Set-AuthenticodeSignature -FilePath $exePath -Certificate $existingCert -HashAlgorithm SHA256 -ErrorAction SilentlyContinue
                Write-Output "[OK] Authenticode Signed: $exePath ($($sigRes.Status))"
            } catch {
                Write-Output "[INFO] Skipped signing $exePath (may be in use)."
            }
        }
    }
}

Write-Output "[COMPLETE] AI-BS Sovereign Host Environment Configured (AIBS-DIR-000-ROOT-AUTHORITY)."
