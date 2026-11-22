# Compatibility entry point. One explicit candidate, signed to a new path only.
# No automatic target selection, PFX import, or embedded credentials.
param(
 [string]$Source,
 [string]$ExpectedSha256,
 [string]$Destination,
 [string]$Thumbprint,
 [string]$TimestampUrl,
 [string]$PythonExe='python'
)
$ErrorActionPreference='Stop'
if (-not $Source -or -not $ExpectedSha256 -or -not $Destination -or -not $Thumbprint -or -not $TimestampUrl) {
 [Console]::Error.WriteLine('Required: -Source -ExpectedSha256 -Destination -Thumbprint -TimestampUrl. Destination must be new.')
 exit 2
}
$tool=Join-Path (Split-Path $PSScriptRoot -Parent) 'scripts\sign_native_candidate.py'
& $PythonExe -B $tool --source $Source --expected-sha256 $ExpectedSha256 --destination $Destination --thumbprint $Thumbprint --timestamp-url $TimestampUrl
exit $LASTEXITCODE
