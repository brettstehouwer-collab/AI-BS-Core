# Fixed Windows backend for sign_native_candidate.py. No PFX or password handling.
param(
    [ValidateSet('inspect','sign','verify')][string]$Mode,
    [string]$TargetPath,
    [ValidatePattern('^[A-Fa-f0-9]{40}$')][string]$Thumbprint,
    [string]$TimestampUrl,
    [string]$ReceiptPath
)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$providerStage = 'ENTRY'
try {
    $providerStage = 'SECURITY_MODULE'
    # Python may inherit PowerShell 7 module paths. Load only this Windows
    # PowerShell installation's inbox module, including its Cert: provider.
    Import-Module -Name (Join-Path $PSHOME 'Modules\Microsoft.PowerShell.Security\Microsoft.PowerShell.Security.psd1') -ErrorAction Stop
    if ($Mode -eq 'verify') {
        $providerStage = 'VERIFY'
        $signature = Get-AuthenticodeSignature -LiteralPath $TargetPath
        $signer = ''
        if ($signature.SignerCertificate) { $signer = $signature.SignerCertificate.Thumbprint }
        @{status=[string]$signature.Status; signerThumbprint=$signer;
            timestampPresent=[bool]$signature.TimeStamperCertificate} | ConvertTo-Json -Compress
        exit 0
    }
    $providerStage = 'CERTIFICATE_METADATA'
    $certificate = Get-Item -LiteralPath "Cert:\CurrentUser\My\$Thumbprint"
    $now = [DateTime]::UtcNow
    # Windows PowerShell 5.1 lacks DisableCertificateDownloads. Use the documented
    # cache-only CryptoAPI flag on both runtimes; never silently permit AIA fetches.
    # https://learn.microsoft.com/windows/win32/api/wincrypt/nf-wincrypt-certgetcertificatechain
    $providerStage = 'OFFLINE_CHAIN_HELPER'
    Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class AibsOfflineSigningChain {
    [StructLayout(LayoutKind.Sequential)] struct Usage { public uint Count; public IntPtr Oids; }
    [StructLayout(LayoutKind.Sequential)] struct Match { public uint Type; public Usage Usage; }
    [StructLayout(LayoutKind.Sequential)] struct Parameters {
        public uint Size; public Match RequestedUsage; public Match RequestedIssuancePolicy;
        public uint UrlTimeout; public int CheckFreshness; public uint Freshness;
        public IntPtr CacheResync; public IntPtr StrongSign; public uint StrongFlags;
    }
    [DllImport("crypt32.dll", SetLastError=true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    static extern bool CertGetCertificateChain(IntPtr engine, IntPtr certificate,
        IntPtr time, IntPtr store, ref Parameters parameters, uint flags,
        IntPtr reserved, out IntPtr chain);
    [DllImport("crypt32.dll")] static extern void CertFreeCertificateChain(IntPtr chain);
    public static bool Build(IntPtr certificate) {
        IntPtr oid=IntPtr.Zero, list=IntPtr.Zero, chain=IntPtr.Zero;
        try {
            oid=Marshal.StringToHGlobalAnsi("1.3.6.1.5.5.7.3.3");
            list=Marshal.AllocHGlobal(IntPtr.Size); Marshal.WriteIntPtr(list,oid);
            Parameters p=new Parameters(); p.Size=(uint)Marshal.SizeOf(typeof(Parameters));
            p.RequestedUsage.Usage.Count=1; p.RequestedUsage.Usage.Oids=list;
            // CERT_CHAIN_CACHE_ONLY_URL_RETRIEVAL; revocation is not requested.
            bool ok=CertGetCertificateChain(IntPtr.Zero,certificate,IntPtr.Zero,
                IntPtr.Zero,ref p,0x00000004,IntPtr.Zero,out chain);
            // CERT_CHAIN_CONTEXT starts with DWORD cbSize, then CERT_TRUST_STATUS.
            return ok && chain!=IntPtr.Zero && Marshal.ReadInt32(chain,4)==0;
        } finally {
            if(chain!=IntPtr.Zero) CertFreeCertificateChain(chain);
            if(list!=IntPtr.Zero) Marshal.FreeHGlobal(list);
            if(oid!=IntPtr.Zero) Marshal.FreeHGlobal(oid);
        }
    }
}
'@
    $providerStage = 'OFFLINE_CHAIN_BUILD'
    $validChain = [AibsOfflineSigningChain]::Build($certificate.Handle)
    $providerStage = 'CERTIFICATE_POLICY'
    $codeSigning = $false
    foreach ($extension in $certificate.Extensions) {
        if ($extension -is [System.Security.Cryptography.X509Certificates.X509EnhancedKeyUsageExtension]) {
            foreach ($oid in $extension.EnhancedKeyUsages) {
                if ($oid.Value -eq '1.3.6.1.5.5.7.3.3') { $codeSigning = $true }
            }
        }
    }
    $metadata = @{
        thumbprint=$certificate.Thumbprint; selfIssued=($certificate.Subject -eq $certificate.Issuer);
        hasPrivateKey=$certificate.HasPrivateKey; codeSigningEku=$codeSigning;
        chainValid=[bool]$validChain; currentlyValid=($now -ge $certificate.NotBefore.ToUniversalTime() -and $now -le $certificate.NotAfter.ToUniversalTime())
    }
    if ($Mode -eq 'inspect') { $metadata | ConvertTo-Json -Compress; exit 0 }
    if ($Mode -ne 'sign' -or $metadata.selfIssued -or -not $metadata.hasPrivateKey -or
        -not $metadata.codeSigningEku -or -not $metadata.chainValid -or -not $metadata.currentlyValid) {
        throw 'CertificateNotReady'
    }
    $providerStage = 'STAGING_RECEIPT'
    $uri = [Uri]$TimestampUrl
    if ($uri.Scheme -ne 'https' -or $uri.UserInfo -or $uri.Fragment -or -not $uri.IsDefaultPort) { throw 'InvalidTimestamp' }
    # Require the orchestrator's exclusively created, still-pending staging receipt.
    # This is an accident-prevention check, not an untrusted-caller boundary.
    $receipt = Get-Content -LiteralPath $ReceiptPath -Raw | ConvertFrom-Json
    $absoluteTarget = [IO.Path]::GetFullPath($TargetPath)
    if ($ReceiptPath -ne ($absoluteTarget + '.signing.json') -or
        $receipt.status -ne 'IN_PROGRESS' -or $receipt.signatureVerified -ne $false -or
        $receipt.destination -ne $absoluteTarget -or $receipt.source -eq $absoluteTarget -or
        $receipt.certificateThumbprint -ne $Thumbprint -or $receipt.timestampUrl -ne $TimestampUrl -or
        $receipt.sourceSha256 -ne (Get-FileHash -LiteralPath $absoluteTarget -Algorithm SHA256).Hash) {
        throw 'StagingReceiptMismatch'
    }
    $providerStage = 'SIGN'
    $null = Set-AuthenticodeSignature -LiteralPath $TargetPath -Certificate $certificate -HashAlgorithm SHA256 -TimestampServer $TimestampUrl
    @{status='SIGN_ATTEMPTED'} | ConvertTo-Json -Compress
} catch {
    # Provider exceptions may include personal paths or key-provider diagnostics.
    [Console]::Error.WriteLine('AUTHENTICODE_PROVIDER_FAILED:' + $providerStage + ':' + $_.Exception.GetType().Name)
    exit 1
}
