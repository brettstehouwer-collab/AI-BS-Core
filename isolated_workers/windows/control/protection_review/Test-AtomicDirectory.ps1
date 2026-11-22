# Infrastructure fixtures only. Preserve every created directory; no VM operations.
$ErrorActionPreference='Stop'
$source=Join-Path $PSScriptRoot 'AtomicDirectory.cs'
if(-not(Test-Path -LiteralPath $source)){throw 'ATOMIC_DIRECTORY_IMPLEMENTATION_MISSING'}
if('AIBS.HostProtection118.AtomicDirectory'-as [type]){throw 'FRESH_PROCESS_REQUIRED'}
Add-Type -TypeDefinition ([IO.File]::ReadAllText($source))
$fixtureBase='C:\AI-BS\backups\host_protection_candidate_20261026_record118\native_fixture'
$null=New-Item -ItemType Directory -Path $fixtureBase -ErrorAction SilentlyContinue
$target=Join-Path $fixtureBase ([guid]::NewGuid().ToString('N'))
$security=New-Object Security.AccessControl.DirectorySecurity
$owner=New-Object Security.Principal.SecurityIdentifier('S-1-5-32-544')
$security.SetOwner($owner);$security.SetAccessRuleProtection($true,$false)
foreach($id in @('S-1-5-32-544','S-1-5-18')){
 $sid=New-Object Security.Principal.SecurityIdentifier($id)
 $security.AddAccessRule((New-Object Security.AccessControl.FileSystemAccessRule($sid,'FullControl','ContainerInherit,ObjectInherit','None','Allow')))
}
[AIBS.HostProtection118.AtomicDirectory]::CreateNew($target,$security.GetSecurityDescriptorBinaryForm())
$actual=Get-Acl -LiteralPath $target
if(-not $actual.AreAccessRulesProtected-or $actual.GetOwner([Security.Principal.SecurityIdentifier]).Value-cne $owner.Value){throw 'ATOMIC_DESCRIPTOR_MISMATCH'}
if(@($actual.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])).Count-ne 2){throw 'INHERITED_BROAD_GRANT_PRESENT'}
$before=$actual.Sddl;$refused=$false
try{[AIBS.HostProtection118.AtomicDirectory]::CreateNew($target,$security.GetSecurityDescriptorBinaryForm())}catch{$refused=$true}
if(-not $refused-or (Get-Acl -LiteralPath $target).Sddl-cne $before){throw 'EXISTING_ROOT_NOT_PRESERVED'}
foreach($bad in @('C:\Users\unused-protection-test','C:\ProgramData\AI-BS-WorkerControl\..\outside')){
 $denied=$false;try{[AIBS.HostProtection118.AtomicDirectory]::CreateNew($bad,$security.GetSecurityDescriptorBinaryForm())}catch{$denied=$true}
 if(-not $denied){throw 'OUTSIDE_SCOPE_ACCEPTED'}
}
[pscustomobject]@{AtomicDescriptorReadback=$true;ExistingRootRefusedUnchanged=$true;OutsideScopeRefused=$true;TraversalRefused=$true;FixturePath=$target;FixturePreserved=$true;Scope='Windows native creation infrastructure, not worker containment'}|ConvertTo-Json
