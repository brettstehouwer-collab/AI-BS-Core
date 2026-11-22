param([Parameter(Mandatory=$true)][string]$EvidenceRoot)
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath($EvidenceRoot)
if($root-notmatch '^C:\\AI-BS\\backups\\worker_config_gate_\d{8}T\d{6,}Z$'-or (Test-Path -LiteralPath $root)){throw 'FRESH_FIXED_GATE_FIXTURE_ROOT_REQUIRED'}
. (Join-Path $PSScriptRoot 'WorkerInspectionPolicy.ps1')
New-Item -ItemType Directory -Path $root|Out-Null
$f=Join-Path $root 'synthetic.vbox';[IO.File]::WriteAllText($f,'synthetic offline configuration')
$hash=(Get-FileHash -LiteralPath $f -Algorithm SHA256).Hash
$null=Assert-WorkerInspectionConfiguration $f $hash;$passed=1
function Expect-Refusal([scriptblock]$Action){$refused=$false;try{$null=& $Action}catch{$refused=$true};if(-not $refused){throw 'UNEXPECTED_CONFIG_ADMISSION'}}
Expect-Refusal {Assert-WorkerInspectionConfiguration $f 'not-a-hash'};$passed++
Expect-Refusal {Assert-WorkerInspectionConfiguration (Join-Path $root 'missing.vbox') $hash};$passed++
Expect-Refusal {Assert-WorkerInspectionConfiguration $root $hash};$passed++
[IO.File]::WriteAllText($f,'changed synthetic configuration')
Expect-Refusal {Assert-WorkerInspectionConfiguration $f $hash};$passed++
$spec=Get-WorkerInspectionSpec
$current=Get-FileHash -LiteralPath $spec.ConfigurationPath -Algorithm SHA256
if($current.Hash-cne $spec.ConfigurationSHA256){
    Expect-Refusal {Assert-WorkerInspectionConfiguration $spec.ConfigurationPath $spec.ConfigurationSHA256};$passed++
    Write-Output 'PASS current VM drift requires review before obsolete offline-task registration'
}
Write-Output ('RESULT passed='+$passed+'; configuration admission only; no scheduler or VM changes.')
