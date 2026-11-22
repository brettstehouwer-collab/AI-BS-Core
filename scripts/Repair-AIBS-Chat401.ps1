# AI-BS Chat HTTP 401: evidence-based repair and diagnostics
# PowerShell 5.1. Run from an elevated PowerShell window.
# Defaults to audit-only. -Apply implements ONLY a narrowly verified missing-header repair.
[CmdletBinding()]
param([switch]$Apply)
$ErrorActionPreference = 'Stop'
$root = 'C:\AI-BS'
$front = Join-Path $root 'frontend'
$ide = Join-Path $front 'components\SplitPaneIDEWorkspace.jsx'
$helper = Join-Path $front 'src\utils\chatAuth.js'
$report = Join-Path $env:TEMP ('AI-BS-Chat401-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.txt')
$lines = New-Object 'System.Collections.Generic.List[string]'
function Record([string]$message) { $lines.Add($message); Write-Host $message }
function Save-Report { $lines | Set-Content -LiteralPath $report -Encoding UTF8; Write-Host "Report: $report" }
function Stop-Repair([string]$reason) { Record "HALT: $reason"; Save-Report; return }
Record 'AI-BS CHAT 401 ANALYSIS (no credentials included)'
Record ('Mode: ' + $(if($Apply){'NARROW REPAIR'}else{'AUDIT ONLY'}))
Record ('When: ' + (Get-Date).ToString('s'))
$failures = 0
foreach($endpoint in @('http://127.0.0.1:8000/api/health','http://127.0.0.1:8080/api/health','https://api.brettstehouwer.live/api/health')) {
  try {
    $r = Invoke-WebRequest -Uri $endpoint -UseBasicParsing -TimeoutSec 6 -ErrorAction Stop
    Record ("HEALTH " + $endpoint + ' = ' + [int]$r.StatusCode)
    $failures = 0
  } catch {
    $http = if($_.Exception.Response){[string][int]$_.Exception.Response.StatusCode}else{'NO HTTP RESPONSE'}
    Record ("HEALTH " + $endpoint + ' = ' + $http)
    $failures++
    if($failures -ge 2) { Stop-Repair 'Two consecutive connectivity failures; original AI-BS halt rule applied.'; return }
  }
}
if(-not (Test-Path -LiteralPath $helper -PathType Leaf)) { Stop-Repair "Missing helper: $helper"; return }
if(-not (Test-Path -LiteralPath $ide -PathType Leaf)) { Stop-Repair "Missing chat component: $ide"; return }
$htext = [IO.File]::ReadAllText($helper)
$itext = [IO.File]::ReadAllText($ide)
Record ('Helper found: ' + $helper)
Record ('Chat component found: ' + $ide)
Record ('Helper references getIdToken: ' + [bool]($htext -match '\bgetIdToken\b'))
Record ('Helper references Bearer: ' + [bool]($htext -match '\bBearer\b'))
Record ('IDE references chatAuthHeaders: ' + [bool]($itext -match '\bchatAuthHeaders\b'))
Record ('IDE references Authorization: ' + [bool]($itext -match '\bAuthorization\b'))
Record ('IDE references getIdToken: ' + [bool]($itext -match '\bgetIdToken\b'))
Record ('IDE references /api/chat: ' + [bool]($itext -match '/api/(?:chat|ai/chat|chat/stream)'))
# Only disclose line numbers, never source lines or tokens.
foreach($item in @(@($helper,$htext), @($ide,$itext))) {
  $name = [string]$item[0]
  $count = 0
  foreach($line in ([string]$item[1] -split '\r?\n')) {
    $count++
    if($line -match 'chatAuthHeaders|getIdToken|Authorization|/api/(chat|ai/chat|chat/stream)|\bfetch\(') {
      Record ("SOURCE " + (Split-Path $name -Leaf) + ':' + $count + ' [auth/chat-related line]')
    }
  }
}
# The following conditional repair is intentionally narrow: it applies only when
# a literal missing-header call is verified and the surrounding call is async.
# Because the current deployment's chat source is not uploaded, ambiguous changes halt.
if(-not $Apply) {
  Record 'AUDIT COMPLETE. No source files changed.'
  Record 'If the frontend sends Authorization but gets HTTP 401, inspect Go Gateway Firebase project/audience and token validation; do not bypass authorization.'
  Save-Report; return
}
# Minimal safe repair: A preexisting helper must contain a known broken empty-return
# sentinel. Otherwise no automatic source edits are authorized.
$knownBroken = 'return { ...headers }; // AI-BS-401-MISSING-BEARER'
if($htext.Contains($knownBroken)) {
  # Only replace the explicit sentinel, retaining Firebase token refresh and UID semantics.
  # Import paths vary, so require an existing auth binding and no other exports removed.
  if($htext -notmatch 'import\s*\{?[^;\r\n]*auth|\bauth\s*=') {
    Stop-Repair 'Known broken helper found, but auth binding is unverified; refusing to patch.'; return
  }
  $replacement = 'const user = auth.currentUser; if (!user) return { ...headers }; const token = await user.getIdToken(); return { ...headers, Authorization: `Bearer ${token}` };'
  # The original helper must be async for await to be valid.
  if($htext -notmatch 'async\s+function\s+chatAuthHeaders|(?:async\s*\([^)]*\)\s*=>)') {
    Stop-Repair 'Known broken helper found, but async function context was not verified.'; return
  }
  $backup = $helper + '.pre-chat401-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.bak'
  Copy-Item -LiteralPath $helper -Destination $backup -ErrorAction Stop
  $updated = $htext.Replace($knownBroken, $replacement)
  [IO.File]::WriteAllText($helper, $updated, (New-Object System.Text.UTF8Encoding($false)))
  Record ('PATCH APPLIED to helper. Original backed up to: ' + $backup)
  Record 'A frontend rebuild/redeploy and a fresh Firebase sign-in are required before testing hosted chat.'
} else {
  Record 'NO SAFE AUTOMATIC PATCH: No exact known missing-Bearer sentinel was found.'
  Record 'A 401 can originate from token omission, token expiration, project mismatch, or gateway verification. Do not rewrite source blindly.'
}
Save-Report
