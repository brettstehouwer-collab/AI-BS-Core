param([string]$EvidenceRoot='C:\AI-BS\backups\windows_exchange_20261025_record112\file_tests')
$ErrorActionPreference='Stop'
$source=Join-Path $PSScriptRoot 'ExchangeFiles.cs'
if(-not (Test-Path -LiteralPath $source)){throw 'RED: ExchangeFiles.cs absent'}
Add-Type -Path $source
$root=Join-Path $EvidenceRoot ([guid]::NewGuid().ToString('N'))
$exchange=Join-Path $root 'exchange';$outside=Join-Path $root 'outside'
foreach($p in @($exchange,$outside,(Join-Path $exchange 'inputs'),(Join-Path $exchange 'outputs'),(Join-Path $exchange 'outputs\nested'))){$null=New-Item -ItemType Directory -Path $p}
$count=0;$cases=New-Object 'System.Collections.Generic.List[object]'
function Pass([string]$Name,[ScriptBlock]$Action){$null=& $Action;$script:count++;$script:cases.Add([pscustomobject]@{case=$Name;passed=$true})}
function Denied([string]$Name,[ScriptBlock]$Action){$failed=$false;try{$null=& $Action}catch{$failed=$true};if(-not $failed){throw ('UNEXPECTED_ACCEPTANCE_'+$Name)};$script:count++;$script:cases.Add([pscustomobject]@{case=$Name;passed=$true})}
$data=[Text.Encoding]::UTF8.GetBytes('disposable exchange bytes')
$sha=[Security.Cryptography.SHA256]::Create();try{$hash=[BitConverter]::ToString($sha.ComputeHash($data)).Replace('-','').ToLowerInvariant()}finally{$sha.Dispose()}
$identity=[AIBS.ExchangeIO.ExchangeRoot]::Describe($exchange)
$allowed=[string[]]@('outputs/result.txt','outputs/nested/second.txt','outputs/hard.txt','outputs/jump/escape.txt','outputs/badlink.txt','outputs/empty.txt','inputs/selected.txt')
$session=[AIBS.ExchangeIO.ExchangeRoot]::Open($exchange,$identity,$allowed)
try{
 Pass 'create and verify bytes by handle' {$r=$session.Publish('outputs/result.txt',$data,$hash);if($r.Length-ne $data.Length-or $r.SHA256-cne $hash-or $r.ExecutionAuthorized-or $r.ApplyAuthorized){throw 'WRONG_RECEIPT'}}
 Pass 'bounded verified read' {$got=$session.ReadVerified('outputs/result.txt',$data.Length,$hash);if([Convert]::ToBase64String($got)-cne [Convert]::ToBase64String($data)){throw 'WRONG_BYTES'}}
 Pass 'nested preprovisioned directory' {$null=$session.Publish('outputs/nested/second.txt',$data,$hash)}
 Denied 'existing file never overwritten' {$session.Publish('outputs/result.txt',[byte[]]@(1),'0'*64)}
 Denied 'hash mismatch before create' {$session.Publish('outputs/empty.txt',$data,'0'*64)}
 if(Test-Path (Join-Path $exchange 'outputs\empty.txt')){throw 'HASH_FAILURE_CREATED_FILE'}
 Denied 'unapproved path' {$session.Publish('outputs/unapproved.txt',$data,$hash)}
 foreach($bad in @('../outside/x','outputs/../x','C:/private','outputs\result.txt','outputs/result.txt:ads','outputs/CON','outputs/aux.txt','outputs/a.','outputs//a','outputs/.env','outputs/a.db','outputs/RESULT.txt')){
  Denied ('path refused '+$bad) {$session.Publish($bad,$data,$hash)}
 }
 Denied 'wrong expected read hash' {$session.ReadVerified('outputs/result.txt',$data.Length,('0'*64))}
 Denied 'wrong expected read length' {$session.ReadVerified('outputs/result.txt',1,$hash)}
 Denied 'oversized bytes' {$session.Publish('outputs/empty.txt',(New-Object byte[] 1048577),$hash)}
 # Windows may allow a directory rename despite open handles. Test object
 # confinement instead of assuming names cannot move: the held root must remain
 # the approved object and a replacement directory must not inherit its pin.
 $moved=$exchange+'_moved';$renamed=$false
 try{Move-Item -LiteralPath $exchange -Destination $moved -ErrorAction Stop;$renamed=$true}catch{}
 if($renamed){
  $null=New-Item -ItemType Directory -Path $exchange
  Denied 'replacement root cannot reuse object identity' {$s=[AIBS.ExchangeIO.ExchangeRoot]::Open($exchange,$identity,$allowed);$s.Dispose()}
  Pass 'held root survives rename without redirecting writes' {$null=$session.Publish('outputs/empty.txt',$data,$hash);if(-not (Test-Path (Join-Path $moved 'outputs\empty.txt'))-or (Test-Path (Join-Path $exchange 'outputs\empty.txt'))){throw 'ROOT_REDIRECTED'}}
  $exchange=$moved
 }else{Pass 'root rename refused by operating system' {}}
 Denied 'wrong root identity' {$s=[AIBS.ExchangeIO.ExchangeRoot]::Open($exchange,('0'*25),$allowed);$s.Dispose()}
 Denied 'case collision allowlist' {$s=[AIBS.ExchangeIO.ExchangeRoot]::Open($exchange,$identity,[string[]]@('outputs/A.txt','outputs/a.txt'));$s.Dispose()}
 $sentinel=Join-Path $outside 'sentinel.txt';[IO.File]::WriteAllBytes($sentinel,$data)
 $null=New-Item -ItemType HardLink -Path (Join-Path $exchange 'outputs\hard.txt') -Target $sentinel
 Denied 'existing hardlink create refused' {$session.Publish('outputs/hard.txt',$data,$hash)}
 Denied 'multiple-link read refused' {$session.ReadVerified('outputs/hard.txt',$data.Length,$hash)}
 $null=New-Item -ItemType Junction -Path (Join-Path $exchange 'outputs\jump') -Target $outside
 Denied 'junction traversal refused' {$session.Publish('outputs/jump/escape.txt',$data,$hash)}
 if(Test-Path (Join-Path $outside 'escape.txt')){throw 'ESCAPED_WRITE'}
 Denied 'linked root refused' {$linked=Join-Path $root 'linked';$null=New-Item -ItemType Junction -Path $linked -Target $exchange;[AIBS.ExchangeIO.ExchangeRoot]::Describe($linked)}
 Pass 'external sentinel preserved' {if([Convert]::ToBase64String([IO.File]::ReadAllBytes($sentinel))-cne [Convert]::ToBase64String($data)){throw 'SENTINEL_CHANGED'}}
}finally{$session.Dispose()}
Denied 'disposed root rejects publication' {$session.Publish('outputs/empty.txt',$data,$hash)}
$report=[pscustomobject]@{passed=$count;cases=$cases;fixture_root=$root;scope='Actual Windows handle/file/junction/hardlink infrastructure only, not standard-worker/guest/containment acceptance';files_preserved=$true}
$report|ConvertTo-Json -Depth 5|Set-Content -LiteralPath (Join-Path $root 'results.json') -Encoding UTF8
Write-Output ('RESULT passed='+$count+'; actual Windows disposable file operations only; no guest or execution authority.')
