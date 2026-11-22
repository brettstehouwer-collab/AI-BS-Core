$ErrorActionPreference = "Stop"
Set-Location -LiteralPath "C:\AI-BS"
$archive = "C:\AI-BS\trade\market_news"
if ((Get-Item -LiteralPath $archive -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Redirected archive refused" }
& "C:\Users\footb\AppData\Local\Programs\Python\Python312\python.exe" -B -X utf8 "C:\AI-BS\scripts\collect_crypto_market_news.py" *> "C:\AI-BS\trade\market_news\collector.log"
exit $LASTEXITCODE
