$sh = New-Object -ComObject WScript.Shell
$targets = @(
    "C:\Users\Public\Desktop\AI-BS Broadcast Studio.lnk",
    "C:\Users\Public\Desktop\AI-BS Check Updates.lnk",
    "C:\Users\Public\Desktop\AI-BS Matrix Boot.lnk",
    "C:\Users\Public\Desktop\AI-BS Shutdown.lnk",
    "C:\Users\Public\Desktop\AI-BS Sovereign Studio.lnk",
    "C:\Users\footb\OneDrive\Desktop\Stehouwer AI • Sovereign Intelligence Studio.lnk",
    "C:\Users\footb\OneDrive\Desktop\AI-BS Main Workstation (Full Suite & DAW).lnk",
    "C:\Users\footb\OneDrive\Desktop\AI-BS Live Streaming & Video Stage.lnk",
    "C:\Users\footb\OneDrive\Desktop\AI-BS Master Server Boot (All 18 Engines).lnk",
    "C:\Users\footb\OneDrive\Desktop\Pearl Wallet.lnk",
    "C:\Users\footb\OneDrive\Desktop\AI-BS Shutdown.lnk",
    "C:\Users\footb\OneDrive\Desktop\AI-BS Executive Studio.lnk",
    "C:\Users\footb\Desktop\AI-BS Executive Studio.lnk"
)

$out = @()
foreach ($p in $targets) {
    if (Test-Path -LiteralPath $p) {
        $lnk = $sh.CreateShortcut($p)
        $tExists = if ($lnk.TargetPath) { Test-Path -LiteralPath $lnk.TargetPath } else { $false }
        $out += "SHORTCUT: $p"
        $out += "  TARGET: $($lnk.TargetPath)"
        $out += "  ARGS:   $($lnk.Arguments)"
        $out += "  DIR:    $($lnk.WorkingDirectory)"
        $out += "  EXISTS: $tExists"
        $out += "--------------------------------------------------"
    } else {
        $out += "SHORTCUT: $p [NOT FOUND]"
        $out += "--------------------------------------------------"
    }
}
$out | Set-Content -Path "C:\AI-BS\scripts\shortcut_analysis.txt" -Encoding utf8
Write-Host "Wrote shortcut analysis."
