param([Parameter(Mandatory=$true)][string]$EvidenceRoot,[switch]$ExpectedRed)
$ErrorActionPreference='Stop'
$target=[IO.Path]::GetFullPath($EvidenceRoot)
if($target -notmatch '^C:\\AI-BS\\backups\\phase4_desktop_query_\d{8}T\d{6,}Z$' -or (Test-Path -LiteralPath $target)){throw 'A fresh timestamped desktop-query evidence folder is required.'}
New-Item -ItemType Directory -Path $target -ErrorAction Stop | Out-Null
$compiler='C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe'
& $compiler /nologo /platform:x64 /define:DESKTOP_QUERY_FIXTURE "/out:$target\DesktopQueryFixture.exe" (Join-Path $PSScriptRoot 'DesktopQueryFixture.cs') 2>&1 | Tee-Object -FilePath (Join-Path $target 'fixture_compiler.txt')
if($LASTEXITCODE -ne 0){throw 'Fixed fixture compilation failed.'}
& $compiler /nologo /platform:x64 "/out:$target\DesktopQueryTests.exe" (Join-Path $PSScriptRoot 'DesktopQuery.cs') (Join-Path $PSScriptRoot 'DesktopQueryFixture.cs') 2>&1 | Tee-Object -FilePath (Join-Path $target 'test_compiler.txt')
if($LASTEXITCODE -ne 0){throw 'Infrastructure test compilation failed.'}
& (Join-Path $target 'DesktopQueryTests.exe') (Join-Path $target 'DesktopQueryFixture.exe') 2>&1 | Tee-Object -FilePath (Join-Path $target 'test_output.txt')
$testExit=$LASTEXITCODE
if($ExpectedRed){if($testExit -eq 0){throw 'Expected behavioral RED did not fail.'};Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'DesktopQuery.cs') -Destination (Join-Path $target 'DesktopQuery.red.cs');Write-Output "VERIFIED behavioral RED exit=$testExit";exit 0}
if($testExit -ne 0){throw 'Focused infrastructure checks failed.'}
Get-FileHash -LiteralPath (Join-Path $PSScriptRoot 'DesktopQuery.cs') -Algorithm SHA256 | Format-List
Write-Output "Evidence: $target"
