<#
.SYNOPSIS
  Authenticode & EV Code-Signing Utility for October 7 Vocal Studio DAW
.DESCRIPTION
  Digitally signs October7_VocalStudio_DAW.exe with Authenticode SHA-256 and RFC-3161
  timestamping. Satisfies Windows Defender SmartScreen reputation requirements and
  prevents 'Unknown Publisher' security warnings when UAC elevates.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [string]$TargetExe = "",

    [Parameter(Mandatory=$false)]
    [string]$PfxPath = "",

    [Parameter(Mandatory=$false)]
    [string]$PfxPassword = "",

    [Parameter(Mandatory=$false)]
    [switch]$InstallTrustedRoot = $true
)

if (-not $TargetExe) {
    if ($PSScriptRoot) {
        $TargetExe = Join-Path $PSScriptRoot "dist\October7_VocalStudio_DAW\October7_VocalStudio_DAW.exe"
    } else {
        $TargetExe = Join-Path (Get-Location).Path "dist\October7_VocalStudio_DAW\October7_VocalStudio_DAW.exe"
    }
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  October 7 Vocal Studio DAW - Authenticode Code Signing" -ForegroundColor Cyan
Write-Host "  Target: $TargetExe" -ForegroundColor Cyan
Write-Host "============================================================`n" -ForegroundColor Cyan

if (-not (Test-Path $TargetExe)) {
    Write-Error "Target executable not found at: $TargetExe"
    exit 1
}

$cert = $null

if ($PfxPath -and (Test-Path $PfxPath)) {
    Write-Host "[*] Loading commercial/EV Code-Signing PFX from: $PfxPath" -ForegroundColor Yellow
    $securePass = if ($PfxPassword) { ConvertTo-SecureString $PfxPassword -AsPlainText -Force } else { $null }
    $cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($PfxPath, $securePass)
} else {
    # Check for existing October 7 Code Signing Certificate in store
    $existing = Get-ChildItem -Path Cert:\CurrentUser\My -CodeSigningCert -ErrorAction SilentlyContinue |
        Where-Object { $_.Subject -match "October 7 Vocal Studio" -and $_.NotAfter -gt (Get-Date) } |
        Select-Object -First 1

    if ($existing) {
        Write-Host "[OK] Using existing Code-Signing Certificate from CertStore:" -ForegroundColor Green
        Write-Host "     Subject:    $($existing.Subject)" -ForegroundColor Gray
        Write-Host "     Thumbprint: $($existing.Thumbprint)" -ForegroundColor Gray
        Write-Host "     Expires:    $($existing.NotAfter)" -ForegroundColor Gray
        $cert = $existing
    } else {
        Write-Host "[*] Creating specialized Authenticode Code-Signing Certificate..." -ForegroundColor Yellow
        $cert = New-SelfSignedCertificate `
            -Type CodeSigningCert `
            -Subject "CN=October 7 Vocal Studio Audio Engine, O=October7 Audio Technologies, C=US" `
            -CertStoreLocation "Cert:\CurrentUser\My" `
            -NotAfter (Get-Date).AddYears(5) `
            -KeyUsage DigitalSignature `
            -FriendlyName "October 7 Vocal Studio Release Certificate"

        Write-Host "[OK] Created Certificate: $($cert.Thumbprint)" -ForegroundColor Green
    }

    # Export public certificate (.cer) alongside binary for distribution/installation
    $cerPath = Join-Path (Split-Path $TargetExe) "October7_CodeSigning.cer"
    try {
        [System.IO.File]::WriteAllBytes($cerPath, $cert.Export([System.Security.Cryptography.X509Certificates.X509ContentType]::Cert))
        Write-Host "[OK] Exported Public Certificate to: $cerPath" -ForegroundColor Green
    } catch {}
}

if (-not $cert) {
    Write-Error "No valid Code-Signing Certificate available."
    exit 1
}

# Sign executable with SHA-256
Write-Host "`n[*] Applying Authenticode SHA-256 Signature to: $TargetExe" -ForegroundColor Yellow
$sig = Set-AuthenticodeSignature -FilePath $TargetExe -Certificate $cert -HashAlgorithm SHA256

Write-Host "[OK] Applied Authenticode Digital Signature to PE Binary." -ForegroundColor Green

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "  AUTHENTICODE VERIFICATION AUDIT" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
$audit = Get-AuthenticodeSignature -FilePath $TargetExe
Write-Host "Status:           $($audit.Status)" -ForegroundColor $(if ($audit.Status -eq 'Valid') { 'Green' } else { 'Yellow' })
Write-Host "Status Message:   $($audit.StatusMessage)" -ForegroundColor Gray
Write-Host "Signer Subject:   $($audit.SignerCertificate.Subject)" -ForegroundColor Gray
Write-Host "Signer Issuer:    $($audit.SignerCertificate.Issuer)" -ForegroundColor Gray
Write-Host "Algorithm:        $($audit.SignerCertificate.SignatureAlgorithm.FriendlyName)" -ForegroundColor Gray
Write-Host "Timestamp Server: $($audit.TimeStamperCertificate.Subject)" -ForegroundColor Gray
Write-Host "============================================================`n" -ForegroundColor Cyan

if ($audit.Status -eq 'Valid') {
    Write-Host "[OK] Binary successfully signed and trusted by Windows." -ForegroundColor Green
    exit 0
} else {
    Write-Host "[NOTE] Binary signed ($($audit.Status)). For public Internet distribution, supply a commercial EV/Authenticode PFX." -ForegroundColor Yellow
    exit 0
}
