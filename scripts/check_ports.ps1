$ports = @(
    @{ Name = 'Main FastAPI Backend'; Port = 8000; Url = 'http://127.0.0.1:8000/'; Desc = 'FastAPI core engine & reasoning' },
    @{ Name = 'Live Crypto Scalp Telemetry'; Port = 8007; Url = 'http://127.0.0.1:8007/api/live-telemetry'; Desc = '0.8s micro-scalp execution daemon' },
    @{ Name = 'Vite Web Frontend'; Port = 5173; Url = 'http://127.0.0.1:5173/'; Desc = 'Vite React cockpit (livestream tab)' },
    @{ Name = 'Ollama Local LLM Host'; Port = 11434; Url = 'http://127.0.0.1:11434/'; Desc = 'Local AI models (Qwen, Llama, Stehouwer)' },
    @{ Name = 'Nginx Web Gateway'; Port = 80; Url = $null; Desc = 'Local reverse proxy gateway' }
)

Write-Host ('{0,-30} | {1,-6} | {2,-12} | {3}' -f 'SERVICE NAME', 'PORT', 'STATUS', 'DETAILS') -ForegroundColor Yellow
Write-Host ('-' * 85) -ForegroundColor DarkGray

foreach ($item in $ports) {
    $conn = Get-NetTCPConnection -LocalPort $item.Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($conn) {
        $status = 'ONLINE'
        $color = 'Green'
        if ($item.Url) {
            try {
                $res = Invoke-WebRequest -Uri $item.Url -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
                $status = 'ONLINE (200)'
            } catch {
                $status = 'LISTENING'
                $color = 'Cyan'
            }
        }
        Write-Host ('{0,-30} | {1,-6} | ' -f $item.Name, $item.Port) -NoNewline
        Write-Host ('{0,-12}' -f $status) -ForegroundColor $color -NoNewline
        Write-Host (' | PID {0} - {1}' -f $conn.OwningProcess, $item.Desc)
    } else {
        Write-Host ('{0,-30} | {1,-6} | ' -f $item.Name, $item.Port) -NoNewline
        Write-Host ('{0,-12}' -f 'OFFLINE') -ForegroundColor Red -NoNewline
        Write-Host (' | NOT LISTENING - {0}' -f $item.Desc)
    }
}

Write-Host ''
Write-Host 'Check complete.' -ForegroundColor Cyan

