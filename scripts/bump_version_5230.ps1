$files = @(
    "C:\AI-BS\frontend\package.json",
    "C:\AI-BS\frontend\App.jsx",
    "C:\AI-BS\frontend\public\sw.js",
    "C:\AI-BS\frontend\public\version.json",
    "C:\AI-BS\frontend\public\updates\version.json",
    "C:\AI-BS\frontend\src\components\ChatTab.jsx",
    "C:\AI-BS\frontend\src\components\components\ChatTab.jsx",
    "C:\AI-BS\frontend\components\ChatTab.jsx",
    "C:\AI-BS\frontend\src\components\MobileGeminiChat.jsx",
    "C:\AI-BS\frontend\src\components\MobileStehouwerChat.jsx",
    "C:\AI-BS\frontend\components\MobileStehouwerChat.jsx",
    "C:\AI-BS\frontend\src\components\PersonalBrandStudioTab.jsx",
    "C:\AI-BS\frontend\src\components\components\PersonalBrandStudioTab.jsx",
    "C:\AI-BS\frontend\components\PersonalBrandStudioTab.jsx",
    "C:\AI-BS\frontend\src\components\PhoneRepairGuideTab.jsx",
    "C:\AI-BS\frontend\src\components\components\PhoneRepairGuideTab.jsx",
    "C:\AI-BS\frontend\components\PhoneRepairGuideTab.jsx",
    "C:\AI-BS\frontend\src\components\Sidebar.jsx",
    "C:\AI-BS\frontend\src\components\components\Sidebar.jsx",
    "C:\AI-BS\frontend\components\Sidebar.jsx",
    "C:\AI-BS\frontend\src\components\SystemUpdateModal.jsx",
    "C:\AI-BS\frontend\src\components\components\SystemUpdateModal.jsx",
    "C:\AI-BS\frontend\components\SystemUpdateModal.jsx",
    "C:\AI-BS\frontend\src\components\TopNavbar.jsx",
    "C:\AI-BS\frontend\src\components\components\TopNavbar.jsx",
    "C:\AI-BS\frontend\components\TopNavbar.jsx"
)

foreach ($f in $files) {
    if (Test-Path $f) {
        $content = Get-Content -Path $f -Raw
        if ($content -match "5\.229\.0") {
            $updated = $content -replace "5\.229\.0", "5.230.0"
            Set-Content -Path $f -Value $updated -NoNewline
            Write-Host "Updated version in $f"
        }
    }
}
Write-Host "All frontend files updated to v5.230.0"
