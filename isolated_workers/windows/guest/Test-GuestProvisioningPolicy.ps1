# Trusted infrastructure tests. Never launch an installer or project check.
$ErrorActionPreference = 'Stop'
$policy = Join-Path $PSScriptRoot 'Guest-ProvisioningPolicy.ps1'
if (-not (Test-Path -LiteralPath $policy)) { throw 'Required guest provisioning policy is missing.' }
. $policy
$script:passed = 0
function Check([string]$Name, [scriptblock]$Body) {
    & $Body
    $script:passed++
    Write-Output "PASS $Name"
}
function Reject([scriptblock]$Body) {
    $rejected = $false
    try { & $Body } catch { $rejected = $true }
    if (-not $rejected) { throw 'Expected rejection did not occur.' }
}
function GuestFacts {
    return @{
        UUID = '6c5a53da-ab80-4ecb-8be6-4059266f736e'
        Manufacturer = 'innotek GmbH'; Model = 'VirtualBox'
        SID = 'S-1-5-21-100-200-300-1000'; Elevated = $true
        EnabledNICCount = 0; Is64Bit = $true
    }
}
Check 'exact isolated guest admitted' { Assert-AIBSGuestFacts (GuestFacts) }
Check 'host manufacturer rejected' {
    $f = GuestFacts; $f.Manufacturer = 'ASUSTeK COMPUTER INC.'; Reject { Assert-AIBSGuestFacts $f }
}
Check 'another virtual machine rejected' {
    $f = GuestFacts; $f.UUID = '6c5a53da-ab80-4ecb-8be6-4059266f736f'; Reject { Assert-AIBSGuestFacts $f }
}
Check 'host worker SID rejected' {
    $f = GuestFacts; $f.SID = 'S-1-5-21-2133766663-4066672948-2456486318-1005'; Reject { Assert-AIBSGuestFacts $f }
}
Check 'host operator SID rejected' {
    $f = GuestFacts; $f.SID = 'S-1-5-21-2133766663-4066672948-2456486318-1001'; Reject { Assert-AIBSGuestFacts $f }
}
Check 'non-elevated guest rejected before installation' {
    $f = GuestFacts; $f.Elevated = $false; Reject { Assert-AIBSGuestFacts $f }
}
Check 'enabled guest adapter rejected' {
    $f = GuestFacts; $f.EnabledNICCount = 1; Reject { Assert-AIBSGuestFacts $f }
}
Check 'unknown NIC observation rejected' {
    $f = GuestFacts; $f.EnabledNICCount = $null; Reject { Assert-AIBSGuestFacts $f }
}
Check 'missing identity rejected' {
    $f = GuestFacts; $f.Remove('UUID'); Reject { Assert-AIBSGuestFacts $f }
}
Check '32-bit process rejected' {
    $f = GuestFacts; $f.Is64Bit = $false; Reject { Assert-AIBSGuestFacts $f }
}
Check 'exact optical media root admitted' {
    Assert-AIBSGuestMedia 'D:\' @{DeviceID='D:'; DriveType=5; VolumeName='AIBS_PROV'}
}
Check 'host folder media rejected' {
    Reject { Assert-AIBSGuestMedia 'C:\AI-BS\' @{DeviceID='C:'; DriveType=3; VolumeName='AIBS_PROV'} }
}
Check 'writable volume rejected' {
    Reject { Assert-AIBSGuestMedia 'D:\' @{DeviceID='D:'; DriveType=3; VolumeName='AIBS_PROV'} }
}
Check 'optical identity mismatch rejected' {
    Reject { Assert-AIBSGuestMedia 'D:\' @{DeviceID='E:'; DriveType=5; VolumeName='AIBS_PROV'} }
}
Check 'wrong volume rejected' {
    Reject { Assert-AIBSGuestMedia 'D:\' @{DeviceID='D:'; DriveType=5; VolumeName='OTHER'} }
}
Check 'UNC media rejected' {
    Reject { Assert-AIBSGuestMedia '\\server\share\' @{DeviceID='D:'; DriveType=5; VolumeName='AIBS_PROV'} }
}
Check 'optical subdirectory rejected' {
    Reject { Assert-AIBSGuestMedia 'D:\nested\' @{DeviceID='D:'; DriveType=5; VolumeName='AIBS_PROV'} }
}
Check 'exact runtime report admitted' {
    Assert-AIBSRuntimeReport @{Node='v24.22.1';Python='Python 3.13.17';Pywin32='312';Psutil='7.2.2';Imports=$true}
}
foreach ($name in @('Node','Python','Pywin32','Psutil','Imports')) {
    Check "incorrect $name rejected" {
        $r=@{Node='v24.22.1';Python='Python 3.13.17';Pywin32='312';Psutil='7.2.2';Imports=$true}
        $r[$name] = if ($name -eq 'Imports') {$false} else {'unexpected'}
        Reject { Assert-AIBSRuntimeReport $r }
    }
}
Check 'reboot required is not success' { Reject { Assert-AIBSInstallerExit 3010 } }
Check 'installer failure is not success' { Reject { Assert-AIBSInstallerExit 1603 } }
Check 'zero installer exit accepted' { Assert-AIBSInstallerExit 0 }
Check 'pure policy has no top-level process or filesystem mutation' {
    $tokens=$null; $errors=$null
    $ast=[Management.Automation.Language.Parser]::ParseFile($policy,[ref]$tokens,[ref]$errors)
    if (@($errors).Count) {throw 'Policy syntax errors'}
    foreach ($statement in $ast.EndBlock.Statements) {
        if ($statement -isnot [Management.Automation.Language.FunctionDefinitionAst]) {
            throw 'Policy must contain functions only.'
        }
    }
}
Write-Output "RESULT $script:passed tests passed; no installers or project checks executed."
