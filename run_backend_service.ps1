Set-Location "C:\AI-BS\backend"
$env:PYTHONUNBUFFERED = "1"

# Load backend configuration safely
$envFile = "C:\AI-BS\backend\.env"
if (Test-Path $envFile) {
    foreach ($line in [System.IO.File]::ReadAllLines($envFile)) {
        $t = $line.Trim()
        if ($t -and -not $t.StartsWith("#") -and $t.Contains("=")) {
            $idx = $t.IndexOf("=")
            $k = $t.Substring(0, $idx).Trim()
            $v = $t.Substring($idx + 1).Trim().Trim('"').Trim("'")
            if ($k) {
                [System.Environment]::SetEnvironmentVariable($k, $v, "Process")
            }
        }
    }
}

$pythonExe = "C:\AI-BS\backend\.venv\Scripts\python.exe"
& $pythonExe AI_BS_Backend.py

