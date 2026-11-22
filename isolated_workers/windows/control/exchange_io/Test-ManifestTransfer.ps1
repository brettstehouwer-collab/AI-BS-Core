param([Parameter(Mandatory=$true)][string]$FixtureRoot)
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath($FixtureRoot)
if($root-cne $FixtureRoot-or $root-cnotmatch '\AC:\\AI-BS\\backups\\manifest_chunk_transfer_20261026_record120\\native_[a-f0-9]{32}\z'){throw 'FIXTURE_SCOPE_REFUSED'}
$seedPath=Join-Path $root 'seed.json'
$seedItem=Get-Item -LiteralPath $seedPath -Force
if($seedItem.Length-gt 65536-or $seedItem.Attributes-band [IO.FileAttributes]::ReparsePoint){throw 'SEED_METADATA_REFUSED'}
$seed=Get-Content -LiteralPath $seedPath -Raw|ConvertFrom-Json
if($seed.files.Count-lt 1-or $seed.files.Count-gt 64){throw 'FILE_COUNT_BOUND'}
$allowed=New-Object 'System.Collections.Generic.List[string]'
foreach($entry in $seed.files){
 if($entry.path-cnotmatch '\A(?:inputs|outputs)/[a-f0-9]{32}/(?:manifest\.json|file_[0-9]{2}_[0-9]{2}\.bin)\z'-or $entry.source-cnotmatch '\Asource_[0-9]{3}\.bin\z'-or $entry.length-lt 0-or $entry.length-gt 1048576-or $entry.sha256-cnotmatch '\A[a-f0-9]{64}\z'){throw 'SEED_ENTRY_REFUSED'}
 $allowed.Add($entry.path)
}
Add-Type -Path (Join-Path $PSScriptRoot 'ExchangeFiles.cs')
$exchange=Join-Path $root 'exchange'
$readback=Join-Path $root 'readback'
if((Test-Path -LiteralPath $exchange)-or (Test-Path -LiteralPath $readback)){throw 'EXISTING_NATIVE_ATTEMPT_PRESERVED'}
$null=New-Item -ItemType Directory -Path $exchange
$null=New-Item -ItemType Directory -Path $readback
foreach($prefix in @($allowed|ForEach-Object {($_-split '/')[0]+'/'+($_-split '/')[1]}|Select-Object -Unique)){
 $null=New-Item -ItemType Directory -Path (Join-Path $exchange $prefix) -Force
}
$identity=[AIBS.ExchangeIO.ExchangeRoot]::Describe($exchange)
$session=[AIBS.ExchangeIO.ExchangeRoot]::Open($exchange,$identity,$allowed.ToArray())
$count=0;$negative=$false
try{
 foreach($entry in $seed.files){
  $source=Join-Path ($root+'\seed') $entry.source
  $item=Get-Item -LiteralPath $source -Force
  if($item.Length-ne $entry.length-or $item.Attributes-band [IO.FileAttributes]::ReparsePoint){throw 'SEED_SOURCE_REFUSED'}
  $bytes=[IO.File]::ReadAllBytes($source)
  $receipt=$session.Publish($entry.path,$bytes,$entry.sha256)
  if($receipt.ExecutionAuthorized-or $receipt.ApplyAuthorized-or $receipt.Length-ne $entry.length){throw 'WRONG_RECEIPT'}
  $returned=$session.ReadVerified($entry.path,$entry.length,$entry.sha256)
  $target=Join-Path $readback $entry.source
  $stream=[IO.File]::Open($target,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
  try{$stream.Write($returned,0,$returned.Length);$stream.Flush($true)}finally{$stream.Dispose()}
  $count++
 }
 $first=$seed.files[0]
 try{$null=$session.ReadVerified($first.path,$first.length,('0'*64))}catch{$negative=$true}
 if(-not $negative){throw 'ALTERED_READ_HASH_ACCEPTED'}
}finally{$session.Dispose()}
$result=[ordered]@{roundtrips=$count;altered_read_hash_refused=$negative;native_root_identity=$identity;all_files_preserved=$true;worker_admitted=$false;execution_authorized=$false;apply_authorized=$false;verification_status='not_run';actual_vm_cases_run=0;scope='Synthetic host Windows handle I/O only; no worker or guest isolation acceptance'}
$result|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $root 'native_result.json') -Encoding UTF8
Write-Output ('NATIVE_ROUNDTRIPS='+$count+'; HASH_REFUSAL='+$negative)
