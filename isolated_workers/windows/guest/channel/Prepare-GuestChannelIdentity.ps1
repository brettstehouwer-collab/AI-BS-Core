$ErrorActionPreference='Stop'
# Run once inside the VM as its current non-elevated user. Public export only.
# A filtered administrator token can also be non-elevated; this is not
# nonadministrator worker admission and grants no code-execution authority.
$computer=Get-CimInstance Win32_ComputerSystem
$bios=Get-CimInstance Win32_BIOS
if(($computer.Model+' '+$computer.Manufacturer+' '+$bios.Manufacturer)-notmatch 'VirtualBox|innotek|Oracle'){throw 'VIRTUALBOX_GUEST_REQUIRED_NO_KEY_CREATED'}
$windowsIdentity=[Security.Principal.WindowsIdentity]::GetCurrent()
$principal=New-Object Security.Principal.WindowsPrincipal($windowsIdentity)
if($principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){throw 'NON_ELEVATED_GUEST_REQUIRED_NO_KEY_CREATED'}
$identityId=[guid]::NewGuid().ToString('N')
$root=Join-Path $env:LOCALAPPDATA ('AI-BS\guest_channel_'+$identityId)
if(Test-Path -LiteralPath $root){throw 'FRESH_IDENTITY_DIRECTORY_REQUIRED'}
$null=New-Item -ItemType Directory -Path $root
$parameters=@{
 Type='Custom';Subject=('CN=AI-BS guest channel '+$identityId)
 FriendlyName=('AI-BS status channel '+$identityId)
 CertStoreLocation='Cert:\CurrentUser\My'
 KeyAlgorithm='ECDSA_nistP256';HashAlgorithm='SHA256'
 Provider='Microsoft Software Key Storage Provider'
 KeyExportPolicy='NonExportable';KeyUsage='DigitalSignature'
 TextExtension=@('2.5.29.37={text}1.3.6.1.5.5.7.3.2')
 Extension=@((New-Object Security.Cryptography.X509Certificates.X509BasicConstraintsExtension($false,$false,0,$true)))
 NotBefore=(Get-Date).AddMinutes(-5);NotAfter=(Get-Date).AddDays(1)
}
$certificate=New-SelfSignedCertificate @parameters
if(-not $certificate.HasPrivateKey){throw 'PRIVATE_KEY_NOT_AVAILABLE'}
$privateKey=[Security.Cryptography.X509Certificates.ECDsaCertificateExtensions]::GetECDsaPrivateKey($certificate)
if($privateKey-isnot [Security.Cryptography.ECDsaCng]-or $privateKey.Key.ExportPolicy-ne [Security.Cryptography.CngExportPolicies]::None){throw 'NONEXPORTABLE_CNG_KEY_REQUIRED'}
$exportRefused=$false
try{$unexpected=$privateKey.Key.Export([Security.Cryptography.CngKeyBlobFormat]::Pkcs8PrivateBlob);[Array]::Clear($unexpected,0,$unexpected.Length)}catch [Security.Cryptography.CryptographicException]{$exportRefused=$true}finally{$privateKey.Dispose()}
if(-not $exportRefused){throw 'PRIVATE_EXPORT_UNEXPECTEDLY_SUCCEEDED'}
$publicPath=Join-Path $root 'public-certificate.cer'
[IO.File]::WriteAllBytes($publicPath,$certificate.RawData)
$algorithm=[Security.Cryptography.SHA256]::Create()
try{$fingerprint=[BitConverter]::ToString($algorithm.ComputeHash($certificate.RawData)).Replace('-','').ToLowerInvariant()}finally{$algorithm.Dispose()}
$record=[ordered]@{
 schema=1;kind='AIBS_GUEST_PUBLIC_IDENTITY';certificate_sha256=$fingerprint
 certificate_der_b64=[Convert]::ToBase64String($certificate.RawData)
 store='CurrentUser\My';store_thumbprint=$certificate.Thumbprint
 private_key_exported=$false;requested_key_export_policy='NonExportable'
 private_key_export_refused=$exportRefused
 valid_from_utc=$certificate.NotBefore.ToUniversalTime().ToString('o')
 valid_until_utc=$certificate.NotAfter.ToUniversalTime().ToString('o')
 guest_process_elevated=$false;guest_identity_directory=$root
 worker_admitted=$false;execution_authorized=$false
}
$json=$record|ConvertTo-Json -Depth 4
[IO.File]::WriteAllText((Join-Path $root 'public-identity.json'),$json)
Write-Output $json
