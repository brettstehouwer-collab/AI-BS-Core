# Pure profile regression plus replay of one retained successful worker metadata query.
# No hypervisor/native process, guest command or task admission.
$ErrorActionPreference='Stop'
$tests=Join-Path $PSScriptRoot 'Test-DesktopProfile.ps1'
$null=& $tests
. (Join-Path $PSScriptRoot 'DesktopProfile.ps1')
$source=[IO.File]::ReadAllText($tests)
$tokens=$null;$errors=$null;$tree=[Management.Automation.Language.Parser]::ParseInput($source,[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'FIXTURE_PARSE_FAILED'}
# Extract only fixed fixture bindings, never the test script's orchestration.
foreach($name in @('profiles','binding','base','valid')){
 $assign=@($tree.FindAll({param($n)$n-is [Management.Automation.Language.AssignmentStatementAst]-and $n.Left.Extent.Text-ceq ('$'+$name)},$true))
 if($assign.Count-ne 1){throw 'FIXTURE_BINDING_NOT_UNIQUE'}
 . ([ScriptBlock]::Create($assign[0].Extent.Text))
}
foreach($n in 1..8){$valid["nic$n"]='none'}
$count=0
$v=$valid.Clone();$v['SnapshotName-1-1']='Retained snapshot';$v['SnapshotUUID-1-1']='73cdeb79-50d5-418b-810c-e38840094ea4';$v['SnapshotDescription-1-1']='Synthetic retained description'
$null=Assert-DesktopInspectionVMInfo $v 'running' $binding
$count++;Write-Output 'PASS recognized snapshot metadata is not storage'
foreach($key in @('SnapshotAttached-1-1','SnapshotName-0-1','SnapshotName-1-0','OtherController-0-0','SharedFolderNameMachineMapping1')){
 $v=$valid.Clone();$v[$key]='unexpected';$denied=$false
 try{$null=Assert-DesktopInspectionVMInfo $v 'running' $binding}catch{$denied=$true}
 if(-not $denied){throw ('UNEXPECTED_FIELD_ADMITTED_'+$key)}
 $count++;Write-Output ('PASS unexpected attachment/sharing field refused '+$key)
}
$path='C:\AI-BS\isolated_workers\windows\runtime\desktop_inspection_v1\inspection_20261026T0135210380212Z_4e248c90f4dc4748af3d1598ef26ed8e'
$query=Join-Path $path 'query-1-result.json'
if((Get-FileHash -LiteralPath $query -Algorithm SHA256).Hash-cne 'A5A929941FC9725401C21F66BC93C262DADA8078C4679E17368D4436D549633C'){throw 'RETAINED_QUERY_CHANGED'}
$native=([IO.File]::ReadAllText($query)|ConvertFrom-Json).Result
if($native.State-cne 'EXITED'-or $native.ExitCode-ne 0){throw 'SUCCESSFUL_RETAINED_METADATA_REQUIRED'}
$intent=[IO.File]::ReadAllText((Join-Path $path 'intent.json'))|ConvertFrom-Json
$observedBinding=@{UUID=[string]$intent.OpticalBinding.UUID;Path=[string]$intent.OpticalBinding.Path;Length=[long]$intent.OpticalBinding.Length;SHA256=[string]$intent.OpticalBinding.SHA256}
$observed=ConvertFrom-DesktopInspectionVMInfo $native.Stdout
$null=Assert-DesktopInspectionVMInfo $observed $observed.VMState $observedBinding
$count++;Write-Output 'PASS retained actual worker query profile replay; not a new native query'
$xml=Read-DesktopInspectionXmlSafe ([IO.File]::ReadAllText($observed.CfgFile))
$null=Assert-DesktopInspectionXml $xml $observed $observedBinding
$count++;Write-Output 'PASS actual preserved XML and retained worker metadata agree offline'
Write-Output ('RESULT passed='+$count+'; profile/data replay only, not worker or containment acceptance.')
