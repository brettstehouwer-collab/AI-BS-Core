param([Parameter(Mandatory=$true)][string]$GuestPublicIdentityPath,[ValidateRange(1,1800)][int]$LifetimeSeconds=900)
$ErrorActionPreference='Stop'
$env:PSModulePath=(Join-Path $PSHOME 'Modules')+';'+(Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\Modules')
# Reviewed source pins checked and locked before either Python process imports.
$reviewed=[ordered]@{
'isolated_workers/connector/provision_connector.py'='DF8C707E59757C619C6664C381850141AE6FA4BEF4EDC29603633BBFDF016C5C'
'isolated_workers/connector/tls_channel.py'='769E15403FFAB8D32357DBAC935E249847C34CEAD10DA6DF6F36BCF362541739'
'isolated_workers/protocol/scoped_exchange.py'='FFDF1C1E45405906A77B66A01ACC666F46DAEE0651D8DF1FE92DFA1AC683B985'
'isolated_workers/protocol/replay_claims.py'='BFEF0A001B5D2CB705F9FCDE3021DCC95621952A255E2C52ABA186FB331943D9'
'isolated_workers/connector/guest_pairing.py'='FC147C962D81D31BF26719377DCE388157FB21FE9D34531390713D8165BE0CB3'
'isolated_workers/connector/provision_paired.py'='BCBD8A0FC3542635400C3BDF28EEC2F8C9CF00003C71F4777FBC69B3377A400B'
'isolated_workers/connector/run_paired.py'='8BCF16D8C9C6DD7B252F1450D73E0EACAB79E5950A956AF7B02CB8E4BAACEE49'
'isolated_workers/windows/guest/channel/GuestStatusClient.cs'='1595C7B4B4D0E648E6144414B5164247A7D66A1D3697EEC07E1C36D95960B53D'
'isolated_workers/windows/guest/channel/Invoke-GuestChannelStatus.ps1'='0493C72CD23AB79FFE060589D41A2110F8D45B504AB5F4C0550755F0565EE84B'
}
$sourceLocks=New-Object 'System.Collections.Generic.List[System.IO.FileStream]'
try {
 foreach($relative in $reviewed.Keys){
  $path=Join-Path 'C:\AI-BS' $relative
  $node=Get-Item -LiteralPath $path -Force
  while($null-ne $node){if($node.Attributes-band [IO.FileAttributes]::ReparsePoint){throw 'LINKED_SOURCE_REFUSED'};$node=if($node-is [IO.FileInfo]){$node.Directory}else{$node.Parent}}
  $stream=[IO.File]::Open($path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
  $sourceLocks.Add($stream);$algorithm=[Security.Cryptography.SHA256]::Create()
  try{$actual=[BitConverter]::ToString($algorithm.ComputeHash($stream)).Replace('-','')}finally{$algorithm.Dispose()}
  if($actual-cne $reviewed[$relative]){throw 'REVIEWED_SOURCE_IDENTITY_CHANGED'}
 }
$ErrorActionPreference='Stop'
# Host companion only. No VM command, worker impersonation, execution or login.
$existing=@(Get-NetTCPConnection -State Listen -ErrorAction Stop|Where-Object LocalPort -eq 18443)
if($existing.Count){throw 'EXISTING_CONNECTOR_LISTENER_PRESERVED'}
$publicNode=Get-Item -LiteralPath $GuestPublicIdentityPath -Force
if($publicNode.PSIsContainer-or $publicNode.Length-gt 16384-or ($publicNode.Attributes-band [IO.FileAttributes]::ReparsePoint)){throw 'PUBLIC_IDENTITY_FILE_REQUIRED'}
$actor=[Security.Principal.WindowsIdentity]::GetCurrent().User
$container=Join-Path $env:LOCALAPPDATA 'AI-BS'
if(-not(Test-Path -LiteralPath $container)){$null=New-Item -ItemType Directory -Path $container}
$root=Join-Path $container ('private_connector_'+[guid]::NewGuid().ToString('N'))
$null=New-Item -ItemType Directory -Path $root
$node=Get-Item -LiteralPath $root -Force
while($null-ne $node){if($node.Attributes-band [IO.FileAttributes]::ReparsePoint){throw 'LINKED_PRIVATE_PATH_REFUSED'};$node=$node.Parent}
# Modify ACL only on the freshly created empty leaf, never an existing directory.
$acl=New-Object Security.AccessControl.DirectorySecurity
$acl.SetOwner($actor);$acl.SetAccessRuleProtection($true,$false)
foreach($sid in @($actor.Value,'S-1-5-18','S-1-5-32-544')){
 $identity=New-Object Security.Principal.SecurityIdentifier($sid)
 $rule=New-Object Security.AccessControl.FileSystemAccessRule($identity,'FullControl','ContainerInherit,ObjectInherit','None','Allow')
 $acl.AddAccessRule($rule)
}
Set-Acl -LiteralPath $root -AclObject $acl
$actual=Get-Acl -LiteralPath $root
if(-not $actual.AreAccessRulesProtected-or $actual.GetOwner([Security.Principal.SecurityIdentifier]).Value-cne $actor.Value){throw 'PRIVATE_OWNER_REQUIRED'}
foreach($rule in $actual.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])){
 if($rule.IdentityReference.Value-cnotin @($actor.Value,'S-1-5-18','S-1-5-32-544')-or $rule.AccessControlType-ne 'Allow'){throw 'PRIVATE_ACL_REQUIRED'}
}
$python=(Get-Command python.exe -ErrorAction Stop).Source
$provisionOutput=& $python 'C:\AI-BS\isolated_workers\connector\provision_paired.py' --private-root $root --public-identity $GuestPublicIdentityPath
$provisionOutput | Out-File -LiteralPath (Join-Path $root 'provision.log') -Encoding utf8
if($LASTEXITCODE-ne 0){throw 'PROVISION_FAILED_RETAIN_EVIDENCE'}
$arguments=@('-u','C:\AI-BS\isolated_workers\connector\run_paired.py','--private-root',('"'+$root+'"'),'--lifetime',[string]$LifetimeSeconds)
$child=Start-Process -FilePath $python -ArgumentList $arguments -WindowStyle Hidden -RedirectStandardOutput (Join-Path $root 'stdout.log') -RedirectStandardError (Join-Path $root 'stderr.log') -PassThru
$ready=Join-Path $root 'ready.json'
for($n=0;$n-lt 30;$n++){
 if(Test-Path -LiteralPath $ready){break}
 $child.Refresh();if($child.HasExited){throw 'CONNECTOR_EXITED_RETAIN_PRIVATE_LOGS'}
 Start-Sleep -Milliseconds 100
}
if(-not(Test-Path -LiteralPath $ready)){throw 'STARTUP_UNCONFIRMED_NO_RESTART'}
$receipt=[IO.File]::ReadAllText($ready)|ConvertFrom-Json
$listeners=@(Get-NetTCPConnection -State Listen|Where-Object LocalPort -eq 18443)
if($receipt.pid-ne $child.Id-or $listeners.Count-ne 1-or $listeners[0].OwningProcess-ne $child.Id-or $listeners[0].LocalAddress-cne '127.0.0.1'){throw 'CONNECTOR_IDENTITY_REQUIRES_REVIEW'}
[pscustomobject]@{state='LISTENING_MUTUAL_TLS_STATUS_ONLY';port=18443;bind='127.0.0.1';pid=$receipt.pid;created=$receipt.created;expires_unix=$receipt.expires_unix;private_root=$root;worker_admitted=$false;execution_authorized=$false;private_ACL_verified=$true;public_recipe=(Join-Path $root 'public-live-recipe.json');guest_certificate_sha256=$receipt.guest_certificate_sha256;channel_epoch=$receipt.channel_epoch}|ConvertTo-Json -Compress
} finally {foreach($stream in $sourceLocks){$stream.Dispose()}}
