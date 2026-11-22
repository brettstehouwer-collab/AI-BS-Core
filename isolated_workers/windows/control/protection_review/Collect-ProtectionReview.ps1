# Dormant metadata collector. No provisioning, imports of project code or authority.
[CmdletBinding()]
param()
$ErrorActionPreference='Stop'
$expectedRoot='C:\ProgramData\AI-BS-WorkerControl'
$policyPath=Join-Path $PSScriptRoot 'policy.review.json'
$policy=Get-Content -LiteralPath $policyPath -Raw | ConvertFrom-Json
if($policy.schema_version-ne 1-or $policy.mode-cne 'review_only'-or $policy.root-cne $expectedRoot){throw 'REVIEW_POLICY_SCOPE_REQUIRED'}
$roles=@('deployment','state','sealed_inputs','incoming_outputs','receipts')
if(@($policy.roots.PSObject.Properties).Count-ne $roles.Count){throw 'EXACT_ROOT_ROLES_REQUIRED'}
$paths=New-Object 'System.Collections.Generic.List[string]'
$paths.Add($expectedRoot)
foreach($role in $roles){
 $property=$policy.roots.PSObject.Properties[$role]
 if($null-eq $property-or $property.Value-cne ($expectedRoot+'\'+$role)){throw 'FIXED_ROOT_PATH_REQUIRED'}
 $paths.Add($property.Value)
}
$files=@{}
if(@($policy.files).Count-lt 1-or @($policy.files).Count-gt 64){throw 'LOAD_FILE_BOUND'}
foreach($file in $policy.files){
 $name=[string]$file.path
 if(-not $name.StartsWith($expectedRoot+'\deployment\',[StringComparison]::Ordinal)-or [IO.Path]::GetFullPath($name)-cne $name-or $name.Contains('/')-or $name.Substring(3).Contains(':')){throw 'FIXED_DEPLOYMENT_FILE_REQUIRED'}
 foreach($part in $name.Substring(3).Split('\')){if($part-in @('','.', '..')-or $part.EndsWith('.')-or $part.EndsWith(' ')){throw 'CANONICAL_COMPONENT_REQUIRED'}}
 if($files.ContainsKey($name)-or $file.sha256-cnotmatch '^[a-f0-9]{64}$'-or $file.kind-cnotin @('runtime','controller','dependency')){throw 'LOAD_FILE_IDENTITY_REQUIRED'}
 $files[$name]=$file;$paths.Add($name)
}
$findings=New-Object 'System.Collections.Generic.List[object]'
$nodes=New-Object 'System.Collections.Generic.List[object]'
foreach($name in $paths){
 if(-not(Test-Path -LiteralPath $name)){$nodes.Add([ordered]@{path=$name;exists=$false});continue}
 $item=Get-Item -LiteralPath $name -Force
 $node=$item;$linked=$false
 while($null-ne $node){
  if($node.Attributes-band [IO.FileAttributes]::ReparsePoint){$linked=$true;break}
  $node=if($node-is [IO.FileInfo]){$node.Directory}else{$node.Parent}
 }
 if($linked){$findings.Add([ordered]@{path=$name;code='LINKED_PATH_SKIPPED'});$nodes.Add([ordered]@{path=$name;exists=$false});continue}
 $acl=Get-Acl -LiteralPath $name
 $record=[ordered]@{path=$name;exists=$true;owner_sid=$acl.GetOwner([Security.Principal.SecurityIdentifier]).Value;protected_dacl=$acl.AreAccessRulesProtected;reparse=$false;grants=@($acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])|ForEach-Object{[ordered]@{sid=$_.IdentityReference.Value;rights=[string]$_.FileSystemRights;type=[string]$_.AccessControlType}})}
 if($files.ContainsKey($name)){
  if($item.PSIsContainer){throw 'REGULAR_LOAD_FILE_REQUIRED'}
  $record.sha256=(Get-FileHash -LiteralPath $name -Algorithm SHA256).Hash.ToLowerInvariant()
  $record.signature_valid=$false;$record.signer=''
  if($files[$name].kind-ceq 'runtime'){
   $signature=Get-AuthenticodeSignature -LiteralPath $name
   $record.signature_valid=($signature.Status-eq 'Valid')
   if($null-ne $signature.SignerCertificate){$record.signer=$signature.SignerCertificate.GetNameInfo([Security.Cryptography.X509Certificates.X509NameType]::SimpleName,$false)}
  }
 }
 $nodes.Add($record)
}
[ordered]@{state='REVIEW_ONLY';observed_utc=[DateTime]::UtcNow.ToString('o');snapshot=[ordered]@{schema_version=1;nodes=@($nodes.ToArray())};collection_findings=@($findings.ToArray());held_object_identity_verified=$false;effective_access_verified=$false;dependency_inventory_complete=$false;worker_admitted=$false;execution_authorized=$false;apply_authorized=$false;verification_status='not_run'}|ConvertTo-Json -Depth 10
