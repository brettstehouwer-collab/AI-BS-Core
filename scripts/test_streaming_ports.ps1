$ip = [System.Net.IPAddress]::Loopback
$ports = @(4173, 8000, 8005, 8006, 8013, 8080, 8088, 8888)

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "         AI-BS STREAMING PORTS LIVE CONNECTIVITY TEST           " -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan

foreach ($p in $ports) {
    $c = New-Object System.Net.Sockets.TcpClient
    try {
        $c.Connect($ip, $p)
        Write-Host "  [+] Port $p : CONNECTED (OK)" -ForegroundColor Green
    } catch {
        Write-Host "  [-] Port $p : FAILED - $($_.Exception.Message)" -ForegroundColor Red
    } finally {
        $c.Close()
    }
}
