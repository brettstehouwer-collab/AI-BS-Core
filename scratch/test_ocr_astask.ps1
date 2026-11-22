Add-Type -AssemblyName System.Runtime.WindowsRuntime
Add-Type -AssemblyName System.Drawing

[Windows.Security.Cryptography.CryptographicBuffer, Windows.Security.Cryptography, ContentType = WindowsRuntime] | Out-Null
[Windows.Media.Ocr.OcrEngine, Windows.Foundation.UniversalApiContract, ContentType = WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.BitmapDecoder, Windows.Foundation.UniversalApiContract, ContentType = WindowsRuntime] | Out-Null
[Windows.Storage.StorageFile, Windows.Foundation.UniversalApiContract, ContentType = WindowsRuntime] | Out-Null

function Await-AsyncOp($asyncOp) {
    $netTask = [System.WindowsRuntimeSystemExtensions]::AsTask($asyncOp)
    $netTask.Wait()
    return $netTask.Result
}

$fileOp = [Windows.Storage.StorageFile]::GetFileFromPathAsync("C:\AI-BS\scratch\ocr_test\page_1.png")
$file = Await-AsyncOp $fileOp

$streamOp = $file.OpenAsync([Windows.Storage.FileAccessMode]::Read)
$stream = Await-AsyncOp $streamOp

$decoderOp = [Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)
$decoder = Await-AsyncOp $decoderOp

$bitmapOp = $decoder.GetSoftwareBitmapAsync()
$bitmap = Await-AsyncOp $bitmapOp

$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
$ocrOp = $engine.RecognizeAsync($bitmap)
$result = Await-AsyncOp $ocrOp

Write-Output "OCR SUCCESS! Text length: $($result.Text.Length)"
Write-Output "Lines recognized: $($result.Lines.Count)"
Write-Output $result.Text
