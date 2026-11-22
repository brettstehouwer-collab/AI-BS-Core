$nodeDir = "C:\AI-BS\runtime\devtools\node-v24.22.1-win-x64"
$env:Path = "$nodeDir;" + $env:Path
Set-Location "C:\AI-BS\frontend"
& "$nodeDir\npm.cmd" run build

