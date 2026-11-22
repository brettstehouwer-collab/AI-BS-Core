$testScript = @'
Add-Type -AssemblyName System.Drawing
[Windows.Security.Cryptography.CryptographicBuffer, Windows.Security.Cryptography, ContentType = WindowsRuntime] | Out-Null
[Windows.Media.Ocr.OcrEngine, Windows.Foundation.UniversalApiContract, ContentType = WindowsRuntime] | Out-Null
$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
if ($engine -ne $null) {
    Write-Output "Windows OCR Engine is AVAILABLE! Language: $($engine.RecognizerLanguage.DisplayName)"
} else {
    Write-Output "Windows OCR Engine returned null."
}
'@
Set-Content -Path "C:\AI-BS\scratch\test_win_ocr.ps1" -Value $testScript
