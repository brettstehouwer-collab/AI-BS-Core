#Requires -Version 5.1
<# Inspect the existing execution environment and optionally launch the verified native controls.
   Does not recursively change ownership, ACLs, file flags, execution policy, registry, or environment.
   PowerShell commands in the terminal use their own explicitly requested child-process arguments. #>
[CmdletBinding()]
param(
    [string]$WorkspaceRoot = 'C:\AI-BS',
    [switch]$Launch,
    [switch]$Elevated
)
$ErrorActionPreference = 'Stop'
$project = (Resolve-Path -LiteralPath $WorkspaceRoot -ErrorAction Stop).Path
$entry = Join-Path $project 'native_studio\work_controls_app.py'
$interpreter = 'C:\Users\Administrator\AppData\Local\AI-BS\packaging_python_20261111_v03\pythonw.exe'
if (-not (Test-Path -LiteralPath $entry -PathType Leaf)) { throw 'The verified source entry is unavailable.' }
if (-not (Test-Path -LiteralPath $interpreter -PathType Leaf)) { throw 'The verified Qt interpreter is unavailable.' }
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$administrator = ([Security.Principal.WindowsPrincipal]::new($identity)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
$report = [ordered]@{
    Workspace = $project
    Administrator = $administrator
    WorkspaceOwner = (Get-Acl -LiteralPath $project).Owner
    Entry = $entry
    Interpreter = $interpreter
    ExecutionPolicies = @(Get-ExecutionPolicy -List | ForEach-Object {
        @{ Scope = [string]$_.Scope; ExecutionPolicy = [string]$_.ExecutionPolicy }
    })
    RecursivePermissionChanges = $false
    PersistentPolicyChanges = $false
    RegistryChanges = $false
    GlobalEnvironmentChanges = $false
    LaunchRequested = [bool]$Launch
    ElevatedLaunchRequested = [bool]$Elevated
}
$report | ConvertTo-Json -Depth 4
if ($Launch) {
    $launchParameters = @{
        FilePath = $interpreter
        ArgumentList = @('-I', '-B', ('"' + $entry + '"'))
        WorkingDirectory = $project
        WindowStyle = 'Normal'
    }
    if ($Elevated -and -not $administrator) {
        # Windows UAC remains authoritative. No hidden elevation or persistent flag.
        $launchParameters.Verb = 'RunAs'
    }
    Start-Process @launchParameters
}
