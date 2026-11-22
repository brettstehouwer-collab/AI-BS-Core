param([Parameter(Mandatory=$true)][string]$EvidenceRoot,[switch]$ScalarCompatibility)
$ErrorActionPreference='Stop'
$target=[IO.Path]::GetFullPath($EvidenceRoot)
if($target-cne $EvidenceRoot-or $target-cnotmatch '\AC:\\AI-BS\\backups\\durable_packet_inbox_20261026_record122\\worker_observer\\(?:scalar_compatibility\\)?(?:red|green_[a-z0-9_]+)\z'-or (Test-Path -LiteralPath $target)){
 throw 'FRESH_SCOPED_OBSERVER_EVIDENCE_REQUIRED'
}
$null=New-Item -ItemType Directory -Path $target
$source=Join-Path $PSScriptRoot 'WorkerTokenObservation.cs'
if(-not (Test-Path -LiteralPath $source)){throw 'RED_WORKER_TOKEN_OBSERVER_SOURCE_ABSENT'}
Add-Type -Path $source -ErrorAction Stop
$cases=New-Object 'System.Collections.Generic.List[object]'
$failed=0
function Refused([string]$Name,[string]$Expected,[ScriptBlock]$Action){
 $found=$false
 try{$null=& $Action}catch{
  $failure=$_.Exception
  while($failure.InnerException){$failure=$failure.InnerException}
  if($failure.Message-cne $Expected){throw ('UNEXPECTED_REFUSAL_'+$Name+'_'+$failure.GetType().Name)}
  $found=$true
 }
 if(-not $found){throw ('UNEXPECTED_ACCEPTANCE_'+$Name)}
 $cases.Add([pscustomobject]@{name=$Name;passed=$true;expected=$Expected})
}
$process=[Diagnostics.Process]::GetCurrentProcess()
try{
 $creation=$process.StartTime.ToUniversalTime().ToFileTimeUtc()
 $exe=$process.MainModule.FileName
 Refused 'zero PID' 'WORKER_PROCESS_ID_REQUIRED' {[AIBS.WorkerObservation.WorkerTokenObservation]::ObserveWorker(0,$creation,$exe)}
 Refused 'wrong creation identity' 'PROCESS_CREATION_IDENTITY_MISMATCH' {[AIBS.WorkerObservation.WorkerTokenObservation]::ObserveWorker($process.Id,1,$exe)}
 Refused 'current caller cannot attest external worker' 'EXACT_EXTERNAL_WORKER_REQUIRED' {[AIBS.WorkerObservation.WorkerTokenObservation]::ObserveWorker($process.Id,$creation,$exe)}
}finally{$process.Dispose()}
function CompatibilityCase([string]$Name,[int]$Kind,[ScriptBlock]$Action){
 try{
  $details=& $Action
  if($details-isnot [Collections.IDictionary]-or $details['passed']-ne $true){throw 'OWN_TOKEN_COMPATIBILITY_ASSERTION'}
  $record=[ordered]@{name=$Name;information_class=$Kind;passed=$true}
  if($details.Contains('count')){$record['count']=$details['count']}
  $cases.Add([pscustomobject]$record)
 }catch{
  $failure=$_.Exception
  while($failure.InnerException){$failure=$failure.InnerException}
  $record=[ordered]@{name=$Name;information_class=$Kind;passed=$false;error_type=$failure.GetType().FullName;stage=if($failure.Message-cmatch '\A[A-Z0-9_]{1,96}\z'){$failure.Message}else{'OWN_TOKEN_COMPATIBILITY_FAILED'}}
  if($failure-is [ComponentModel.Win32Exception]){$record['native_error']=$failure.NativeErrorCode}
  foreach($property in @('InformationClass','RequiredLength','SuppliedLength','LengthUnit')){if($failure.PSObject.Properties[$property]){$record[$property]=$failure.$property}}
  $cases.Add([pscustomobject]$record)
  $script:failed++
 }
}
if($ScalarCompatibility){
 $helper=[AIBS.WorkerObservation.WorkerTokenObservation]
 $binding=[Reflection.BindingFlags]::Static-bor [Reflection.BindingFlags]::NonPublic
 $number=$helper.GetMethod('Number',$binding)
 $sid=$helper.GetMethod('TokenSID',$binding)
 $groupsMethod=$helper.GetMethod('ReadGroups',$binding)
 $privilegesMethod=$helper.GetMethod('ReadPrivileges',$binding)
 if($null-eq $number-or $null-eq $sid-or $null-eq $groupsMethod-or $null-eq $privilegesMethod){throw 'PRIVATE_COMPATIBILITY_METHOD_MISSING'}
 # The only native token passed to private helpers is this fixture's OWN token.
 $identity=[Security.Principal.WindowsIdentity]::GetCurrent()
 try{
  foreach($kind in @(8,12,18,20)){
   CompatibilityCase ('own scalar '+$kind) $kind {
    $value=$number.Invoke($null,[object[]]@($identity.Token,[int]$kind))
    $valid=($value-is [uint32])
    if($kind-eq 8){$valid=$valid-and $value-in @(1,2)}
    if($kind-eq 18){$valid=$valid-and $value-in @(1,2,3)}
    if($kind-eq 20){$valid=$valid-and $value-in @(0,1)}
    @{passed=$valid}
   }
  }
  CompatibilityCase 'own integrity SID' 25 {
   $value=$sid.Invoke($null,[object[]]@($identity.Token,[int]25))
   @{passed=($value-is [string]-and $value-cmatch '\AS-1-16-[0-9]+\z')}
  }
  CompatibilityCase 'own groups' 2 {
   $value=@($groupsMethod.Invoke($null,[object[]]@($identity.Token)))
   @{passed=($value.Count-le 256-and @($value|Where-Object {$_.SID-isnot [string]-or $_.Attributes-isnot [uint32]}).Count-eq 0);count=$value.Count}
  }
  CompatibilityCase 'own privileges' 3 {
   $value=@($privilegesMethod.Invoke($null,[object[]]@($identity.Token)))
   @{passed=($value.Count-le 128-and @($value|Where-Object {$_.Name-isnot [string]-or $_.Attributes-isnot [uint32]}).Count-eq 0);count=$value.Count}
  }
 }finally{$identity.Dispose()}
}
$result=[ordered]@{utc=[DateTime]::UtcNow.ToString('o');passed=($cases.Count-$failed);failed=$failed;cases=$cases;source_sha256=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash;own_token_compatibility=$ScalarCompatibility.IsPresent;personal_groups_or_privilege_names_dumped=$false;positive_worker_query_run=$false;worker_task_run=$false;task_or_permission_changes=$false;worker_admitted=$false;execution_authorized=$false;apply_authorized=$false;scope='Trusted QUERY-only helper own-token compatibility and negative infrastructure guards only; no worker acceptance'}
$result|ConvertTo-Json -Depth 6|Set-Content -LiteralPath (Join-Path $target 'result.json') -Encoding UTF8
Write-Output ('OBSERVER_INFRASTRUCTURE_PASSED='+($cases.Count-$failed)+';FAILED='+$failed)
if($failed){exit 1}
