$targets = @(80, 5173, 8000, 8080, 11434, 3001, 8002)
foreach ($port in $targets) {
    $res = Test-NetConnection -ComputerName 127.0.0.1 -Port $port -WarningAction SilentlyContinue
    if ($res.TcpTestSucceeded) {
        Write-Host "PORT $port : ONLINE"
    } else {
        Write-Host "PORT $port : OFFLINE"
    }
}
