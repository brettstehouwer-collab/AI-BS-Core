$ports = @(
    80, 443, 3001, 5173, 8000, 8002, 8010, 8080, 8085, 8099, 11434,
    1935, 4173, 4455, 5174, 8001, 8005, 8006, 8008, 8013, 8088, 8188,
    8189, 8765, 8888, 11435, 8007, 8095, 5180
)

foreach ($p in $ports) {
    $conn = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue
    if ($conn) {
        $pidVal = ($conn | Select-Object -First 1).OwningProcess
        Write-Output "PORT $p : ONLINE (PID $pidVal)"
    } else {
        Write-Output "PORT $p : OFFLINE"
    }
}

