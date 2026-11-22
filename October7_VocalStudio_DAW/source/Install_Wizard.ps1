# Reference-source entry point. Installation logic belongs to the repaired package root.
$ErrorActionPreference = 'Stop'
$RootInstaller = Join-Path (Split-Path -Parent $PSScriptRoot) 'Install_Wizard.ps1'
if (-not (Test-Path -LiteralPath $RootInstaller -PathType Leaf)) {
    throw 'The repaired root installer is missing. No installation was attempted.'
}
& $RootInstaller @args
if ($LASTEXITCODE) { exit $LASTEXITCODE }
