param()
$ErrorActionPreference='Stop'
$source=$PSScriptRoot
$compiler='C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe'
if(-not(Test-Path -LiteralPath $compiler)){throw 'Installed x64 .NET Framework compiler unavailable.'}
$build=Join-Path $source 'build'
if(Test-Path -LiteralPath $build){throw 'Fresh build directory required; preserve prior outputs.'}
New-Item -ItemType Directory -Path $build -ErrorAction Stop | Out-Null
$core=@((Join-Path $source 'WheelSetupCore.cs'),(Join-Path $source 'WheelMedia.cs'),(Join-Path $source 'WheelInstall.cs'))
& $compiler /nologo /platform:x64 /target:winexe /optimize+ /reference:System.Management.dll /reference:System.Windows.Forms.dll /reference:System.Drawing.dll /reference:System.Web.Extensions.dll "/win32manifest:$source\WheelSetup.exe.manifest" "/out:$build\AI-BS Wheel Setup.exe" $core (Join-Path $source 'WheelWindow.cs')
if($LASTEXITCODE -ne 0){throw 'Helper compilation failed.'}
& $compiler /nologo /platform:x64 /target:exe "/out:$build\WheelProcessFixture.exe" (Join-Path $source 'WheelProcessFixture.cs')
if($LASTEXITCODE -ne 0){throw 'Trusted fixed fixture compilation failed.'}
& $compiler /nologo /platform:x64 /target:exe /reference:System.Management.dll /reference:System.Web.Extensions.dll "/out:$build\WheelSetupTests.exe" $core (Join-Path $source 'WheelSetupTests.cs')
if($LASTEXITCODE -ne 0){throw 'Infrastructure test compilation failed.'}
& $compiler /nologo /platform:x64 /target:exe "/out:$build\WheelManifestTests.exe" (Join-Path $source 'WheelManifestTests.cs')
if($LASTEXITCODE -ne 0){throw 'Trusted manifest reader compilation failed.'}
& (Join-Path $build 'WheelManifestTests.exe') (Join-Path $build 'AI-BS Wheel Setup.exe') 2>&1 | Tee-Object -FilePath (Join-Path $build 'embedded_manifest_tests.txt')
if($LASTEXITCODE -ne 0){throw 'Actual embedded manifest verification failed.'}
$testRoot=Join-Path $build 'infrastructure_test_data'
New-Item -ItemType Directory -Path $testRoot -ErrorAction Stop | Out-Null
$reparseTarget=Join-Path $testRoot 'reparseTarget'
New-Item -ItemType Directory -Path $reparseTarget -ErrorAction Stop | Out-Null
New-Item -ItemType Junction -Path (Join-Path $testRoot 'reparseLink') -Target $reparseTarget -ErrorAction Stop | Out-Null
& (Join-Path $build 'WheelSetupTests.exe') (Join-Path $build 'WheelProcessFixture.exe') $testRoot 2>&1 | Tee-Object -FilePath (Join-Path $build 'infrastructure_tests.txt')
if($LASTEXITCODE -ne 0){throw 'Infrastructure tests failed.'}
# These production-entry invocations must refuse the actual host before GUI,
# native runtime probes or application writes. Neither invocation uses pip.
$cases=@([pscustomobject]@{Argument='';Expected=2},[pscustomobject]@{Argument='--check-identity';Expected=2},[pscustomobject]@{Argument='--test-bypass';Expected=64})
foreach($case in $cases){
    $expected=$case.Expected
    $process=New-Object System.Diagnostics.Process
    $process.StartInfo.FileName=Join-Path $build 'AI-BS Wheel Setup.exe'
    $process.StartInfo.Arguments=$case.Argument
    $process.StartInfo.UseShellExecute=$false
    $process.StartInfo.CreateNoWindow=$true
    if(-not $process.Start()){throw 'Host refusal process did not start.'}
    if(-not $process.WaitForExit(15000)){try{$process.Kill()}catch{};throw 'Host refusal deadline failed.'}
    if($process.ExitCode -ne $expected){throw "Host refusal exit differed from expected $expected"}
    "PASS actual host entry [$($case.Argument)] exit=$($process.ExitCode)" | Tee-Object -FilePath (Join-Path $build 'host_refusal_tests.txt') -Append
    $process.Dispose()
}
Get-FileHash -LiteralPath (Join-Path $build 'AI-BS Wheel Setup.exe') -Algorithm SHA256 | Format-List
