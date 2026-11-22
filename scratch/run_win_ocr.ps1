param([string]$ImagePath)

Add-Type -AssemblyName System.Drawing
[Windows.Security.Cryptography.CryptographicBuffer, Windows.Security.Cryptography, ContentType = WindowsRuntime] | Out-Null
[Windows.Media.Ocr.OcrEngine, Windows.Foundation.UniversalApiContract, ContentType = WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.BitmapDecoder, Windows.Foundation.UniversalApiContract, ContentType = WindowsRuntime] | Out-Null
[Windows.Storage.StorageFile, Windows.Foundation.UniversalApiContract, ContentType = WindowsRuntime] | Out-Null

function Get-OcrText {
    param([string]$Path)
    $fileTask = [Windows.Storage.StorageFile]::GetFileFromPathAsync($Path)
    $file = $fileTask.GetAwaiter().GetResult()
    
    $streamTask = $file.OpenAsync([Windows.Storage.FileAccessMode]::Read)
    $stream = $streamTask.GetAwaiter().GetResult()
    
    $decoderTask = [Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)
    $decoder = $decoderTask.GetAwaiter().GetResult()
    
    $bitmapTask = $decoder.GetSoftwareBitmapAsync()
    $bitmap = $bitmapTask.GetAwaiter().GetResult()
    
    $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
    $ocrTask = $engine.RecognizeAsync($bitmap)
    $result = $ocrTask.GetAwaiter().GetResult()
    
    return $result.Text
}

if ($ImagePath) {
    Get-OcrText -Path $ImagePath
} else {
    for ($i=1; $i -le 5; $i++) {
        $p = "C:\AI-BS\scratch\ocr_test\page_$i.png"
        Write-Output "================ PAGE $i ================"
        $txt = Get-OcrText -Path $p
        Write-Output $txt
    }
}
