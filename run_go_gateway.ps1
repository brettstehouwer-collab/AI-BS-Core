$f = "C:\AI-BS\.env"
if (Test-Path $f) {
    foreach ($line in [System.IO.File]::ReadAllLines($f)) {
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
Set-Location "C:\AI-BS\go-core"
& "C:\AI-BS\go-core\aibs_engine.exe"