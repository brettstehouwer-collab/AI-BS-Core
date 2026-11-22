$ports = @(8000, 8080, 11434)
foreach ($p in $ports) {
    $conn = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue
    if ($conn) {
        Write-Output "PORT $p : LISTENING (PID $($conn[0].OwningProcess))"
    } else {
        Write-Output "PORT $p : NOT_LISTENING"
    }
}

