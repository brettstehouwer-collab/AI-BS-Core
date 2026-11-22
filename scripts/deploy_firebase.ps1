$nodeDir = "C:\AI-BS\runtime\devtools\node-v24.22.1-win-x64"
$env:Path = "$nodeDir;" + $env:Path
$firebaseCmd = "C:\Users\Administrator\AppData\Local\npm-cache\_npx\ba4f1959e38407b5\node_modules\.bin\firebase.cmd"
Set-Location "C:\AI-BS\frontend"
& $firebaseCmd deploy --only hosting
