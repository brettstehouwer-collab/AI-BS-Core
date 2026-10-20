$urls = @(
    "https://stehouwer-publishing.com",
    "https://thesimplechef.web.app",
    "https://thesimplecheff.com",
    "https://ai-bs-dashboard.web.app",
    "https://api.brettstehouwer.live/health"
)

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "      EXTERNAL WEBSITE HEALTH CHECK       " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

foreach ($target in $urls) {
    try {
        $code = curl.exe -s -o /dev/null -w "%{http_code}" --connect-timeout 6 -m 10 $target
        if ($code -ge 200 -and $code -lt 400) {
            Write-Host "[ONLINE] $target -> HTTP $code" -ForegroundColor Green
        } else {
            Write-Host "[ALERT]  $target -> HTTP $code" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "[ERROR]  $target -> FAILED TO REACH" -ForegroundColor Red
    }
}
Write-Host "==========================================" -ForegroundColor Cyan
