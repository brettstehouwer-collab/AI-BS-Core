# Operator-authorized trusted host provisioning only; no guest or task execution.
[CmdletBinding()]
param([switch]$Provision)
$ErrorActionPreference='Stop'
$target='C:\ProgramData\AI-BS-WorkerControl'
$evidence='C:\AI-BS\backups\host_protection_candidate_20261026_record118'
$controller='S-1-5-21-2133766663-4066672948-2456486318-1001'
$worker='S-1-5-21-2133766663-4066672948-2456486318-1005'
$admin='S-1-5-32-544';$system='S-1-5-18'
if(-not $Provision){[pscustomobject]@{state='DESCRIBE_ONLY';target=$target;existing_permissions_changed=$false;worker_admitted=$false;execution_authorized=$false;apply_authorized=$false}|ConvertTo-Json;exit 0}
$identity=[Security.Principal.WindowsIdentity]::GetCurrent()
$principal=New-Object Security.Principal.WindowsPrincipal($identity)
if($identity.User.Value-cne $controller-or -not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)-or -not [Environment]::Is64BitProcess){throw 'EXACT_X64_TRUSTED_ADMIN_PROVISIONER_REQUIRED'}
if(Test-Path -LiteralPath $target){throw 'EXISTING_TARGET_PRESERVED_NO_ADOPTION'}
foreach($parent in @('C:\','C:\ProgramData')){
 $item=Get-Item -LiteralPath $parent -Force
 if($item.Attributes-band [IO.FileAttributes]::ReparsePoint){throw 'LINKED_PROVISIONING_ANCESTOR_REFUSED'}
 $acl=Get-Acl -LiteralPath $parent
 foreach($ace in $acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])){
  if($ace.PropagationFlags-band [Security.AccessControl.PropagationFlags]::InheritOnly){continue}
  if($ace.AccessControlType-eq 'Allow'-and $ace.IdentityReference.Value-cnotin @($admin,$system)-and ([long]$ace.FileSystemRights-band 0xD0040)){throw 'UNTRUSTED_ANCESTOR_REPLACEMENT_RIGHTS'}
 }
}
$source=Join-Path $PSScriptRoot 'AtomicDirectory.cs'
$held=[IO.File]::Open($source,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
try{
 $hash=[Security.Cryptography.SHA256]::Create()
 try{$digest=[BitConverter]::ToString($hash.ComputeHash($held)).Replace('-','')}finally{$hash.Dispose();$held.Position=0}
 if($digest-cne 'ABA03C7EB66471D241232FE5DEB4E158F2D2CE7F54ED32CCFA1DE1BD4AF24F89'){throw 'PROVISIONING_NATIVE_SOURCE_PIN_CHANGED'}
 if('AIBS.HostProtection118.AtomicDirectory'-as [type]){throw 'FRESH_PROCESS_REQUIRED'}
 $reader=New-Object IO.StreamReader($held,[Text.Encoding]::UTF8,$true,4096,$true)
 try{$text=$reader.ReadToEnd()}finally{$reader.Dispose()}
 Add-Type -TypeDefinition $text
 function Write-NewJson([string]$Path,$Value){
  $bytes=[Text.Encoding]::UTF8.GetBytes(($Value|ConvertTo-Json -Depth 12))
  $file=[IO.File]::Open($Path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
  try{$file.Write($bytes,0,$bytes.Length);$file.Flush($true)}finally{$file.Dispose()}
 }
 function New-Descriptor([string]$Role){
  $security=New-Object Security.AccessControl.DirectorySecurity
  $security.SetOwner((New-Object Security.Principal.SecurityIdentifier($admin)))
  $security.SetAccessRuleProtection($true,$false)
  foreach($id in @($admin,$system)){
   $sid=New-Object Security.Principal.SecurityIdentifier($id)
   $security.AddAccessRule((New-Object Security.AccessControl.FileSystemAccessRule($sid,'FullControl','ContainerInherit,ObjectInherit','None','Allow')))
  }
  $ownerRights=New-Object Security.Principal.SecurityIdentifier('S-1-3-4')
  $security.AddAccessRule((New-Object Security.AccessControl.FileSystemAccessRule($ownerRights,'ReadPermissions','ContainerInherit,ObjectInherit','None','Allow')))
  $readers=if($Role-in @('state','receipts')){@($controller)}else{@($controller,$worker)}
  foreach($id in $readers){
   $sid=New-Object Security.Principal.SecurityIdentifier($id)
   $inherit=if($Role-ceq 'root'){'None'}else{'ContainerInherit,ObjectInherit'}
   $security.AddAccessRule((New-Object Security.AccessControl.FileSystemAccessRule($sid,'ReadAndExecute',$inherit,'None','Allow')))
  }
  $writers=if($Role-ceq 'incoming_outputs'){@($controller,$worker)}elseif($Role-in @('state','sealed_inputs','receipts')){@($controller)}else{@()}
  foreach($id in $writers){
   $sid=New-Object Security.Principal.SecurityIdentifier($id)
   # No DELETE on the protected subtree itself; Modify applies to descendants.
   $security.AddAccessRule((New-Object Security.AccessControl.FileSystemAccessRule($sid,'ReadAndExecute,Write','None','None','Allow')))
   $security.AddAccessRule((New-Object Security.AccessControl.FileSystemAccessRule($sid,'Modify','ContainerInherit,ObjectInherit','InheritOnly','Allow')))
  }
  return $security
 }
 function Rules($Security){return @($Security.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])|ForEach-Object{'{0}|{1}|{2}|{3}|{4}|{5}'-f $_.IdentityReference.Value,[int]$_.AccessControlType,[long]$_.FileSystemRights,[int]$_.InheritanceFlags,[int]$_.PropagationFlags,$_.IsInherited}|Sort-Object)}
 $receipt=[ordered]@{state='PROVISIONING';started_utc=[DateTime]::UtcNow.ToString('o');target=$target;directories=@();deployed_files=@();existing_permissions_changed=$false;runtime_or_connector_started=$false;worker_admitted=$false;execution_authorized=$false;apply_authorized=$false;verification_status='not_run'}
 $step=0
 foreach($role in @('root','deployment','policy','state','sealed_inputs','incoming_outputs','receipts','review_candidate')){
  $name=if($role-ceq 'root'){$target}elseif($role-ceq 'review_candidate'){Join-Path $target 'deployment\review_candidate'}else{Join-Path $target $role}
  $security=New-Descriptor $role
  Write-NewJson (Join-Path $evidence ('provision_'+$step+'_intent.json')) ([ordered]@{path=$name;role=$role;descriptor_sha256=([BitConverter]::ToString([Security.Cryptography.SHA256]::HashData($security.GetSecurityDescriptorBinaryForm())).Replace('-','').ToLowerInvariant());authority=$false})
  [AIBS.HostProtection118.AtomicDirectory]::CreateNew($name,$security.GetSecurityDescriptorBinaryForm())
  $actual=Get-Acl -LiteralPath $name
  if(-not $actual.AreAccessRulesProtected-or $actual.GetOwner([Security.Principal.SecurityIdentifier]).Value-cne $admin-or (Compare-Object (Rules $security) (Rules $actual))){throw ('CREATED_DESCRIPTOR_READBACK_FAILED '+$role)}
  $entry=[ordered]@{path=$name;role=$role;owner_sid=$admin;protected_dacl=$true;rules=(Rules $actual)}
  $receipt.directories+=,$entry
  Write-NewJson (Join-Path $evidence ('provision_'+$step+'_result.json')) $entry
  $step++
 }
 $destination=Join-Path $target 'deployment\review_candidate'
 foreach($name in @('README.md','policy.review.json','review_policy.py','test_review_policy.py','Collect-ProtectionReview.ps1','AtomicDirectory.cs','Test-AtomicDirectory.ps1','Provision-HostProtectionRoot.ps1')){
  $from=Join-Path $PSScriptRoot $name;$to=Join-Path $destination $name
  $item=Get-Item -LiteralPath $from -Force
  if($item.Attributes-band [IO.FileAttributes]::ReparsePoint-or $item.Length-gt 1048576){throw 'DEPLOYMENT_SOURCE_REFUSED'}
  $input=[IO.File]::Open($from,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
  try{
   $buffer=New-Object byte[] $input.Length;$used=0
   while($used-lt $buffer.Length){$read=$input.Read($buffer,$used,$buffer.Length-$used);if($read-le 0){throw 'SHORT_SOURCE_READ'};$used+=$read}
   $output=[IO.File]::Open($to,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
   try{$output.Write($buffer,0,$buffer.Length);$output.Flush($true)}finally{$output.Dispose()}
   $expected=[BitConverter]::ToString([Security.Cryptography.SHA256]::HashData($buffer)).Replace('-','').ToLowerInvariant()
   if((Get-FileHash -LiteralPath $to -Algorithm SHA256).Hash.ToLowerInvariant()-cne $expected){throw 'DEPLOYED_READBACK_HASH_FAILED'}
   $receipt.deployed_files+=,[ordered]@{name=$name;sha256=$expected;bytes=$buffer.Length}
  }finally{$input.Dispose()}
 }
 $receipt.state='PROTECTED_ROOTS_AND_REVIEW_PACKAGE_CREATED';$receipt.completed_utc=[DateTime]::UtcNow.ToString('o')
 Write-NewJson (Join-Path $target 'receipts\protection_provisioned_v1.json') $receipt
 Write-NewJson (Join-Path $evidence 'protection_provisioned_v1.json') $receipt
 $receipt|ConvertTo-Json -Depth 12
}finally{$held.Dispose()}
