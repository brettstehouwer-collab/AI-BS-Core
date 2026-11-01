<#
.SYNOPSIS
  Official Windows Directory Installer Wizard for October 7 Vocal Studio DAW
.DESCRIPTION
  Modern native Windows GUI installer featuring:
  - UAC Administrator Elevation
  - End-User License Agreement (EULA) Acceptance
  - Customizable Destination Directory with Folder Browser Dialog
  - Desktop & Start Menu Shortcut Integration
  - Optional certificate fingerprint review (no trust store changes)
#>

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# 1. Verify and Request Administrator Elevation
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Start-Process powershell.exe -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

$ScriptDir = Split-Path -Parent $PSCommandPath
$SourceDir = Join-Path $ScriptDir "dist\October7_VocalStudio_Native"
if (-not (Test-Path -LiteralPath (Join-Path $SourceDir 'October7_VocalStudio_Native.exe'))) {
    $SourceDir = Join-Path $ScriptDir "dist\October7_VocalStudio_DAW"
}
if (-not (Test-Path -LiteralPath (Join-Path $SourceDir 'October7_VocalStudio_DAW.exe')) -and
    -not (Test-Path -LiteralPath (Join-Path $SourceDir 'October7_VocalStudio_Native.exe'))) {
    $SourceDir = $ScriptDir
}

$DefaultInstallPath = Join-Path $env:ProgramFiles "October7_VocalStudio_DAW"
$AltInstallPath = Join-Path $env:LOCALAPPDATA "October7_VocalStudio_DAW"

$EulaText = @"
================================================================================
OCTOBER 7 VOCAL STUDIO & PERFORMANCE ENGINE - END USER LICENSE AGREEMENT (EULA)
================================================================================
VERSION 1.0 - WINDOWS CORE PRO EDITION (RELEASE CANDIDATE)

1. LICENSE GRANT & LOCAL SOVEREIGNTY:
October 7 Vocal Studio is licensed as a sovereign, local-first digital audio
workstation (DAW) for vocal tracking, real-time bio-acoustic telemetry, and stem
management. All audio recordings, vocal stems, bio-acoustic measurements, and AI
music latents are processed and retained 100% locally on your machine. No voice
samples or session data are transmitted to external cloud servers.

2. HARDWARE & REALTIME OS OPTIMIZATIONS:
This software executes with Windows Administrator privileges to engage:
- Windows Multimedia Class Scheduler Service (MMCSS) Pro Audio thread priority.
- Direct WASAPI Exclusive buffer management and low-latency round-trip alignment.
- Local NVIDIA GeForce CUDA acceleration (Demucs stem separation, ACE-Step 1.5).

3. LOCAL AI MODELS & DISK ALLOCATION:
Any local AI components (Ollama, ACE-Step 1.5, Demucs) run within local hardware
bounds. The software includes automatic thread-safe CUDA VRAM management to protect
system resources.

4. USER ACCEPTANCE:
By installing or using this software, you confirm acceptance of these terms and
authorize the installer to deploy the audio engine, configure system audio priority,
and register the local Authenticode digital signature for trusted execution.
================================================================================
"@

# Initialize Form
$form = New-Object System.Windows.Forms.Form
$form.Text = "October 7 Vocal Studio DAW - Windows Setup Wizard"
$form.Size = New-Object System.Drawing.Size(680, 560)
$form.StartPosition = "CenterScreen"
$form.FormBorderStyle = "FixedDialog"
$form.MaximizeBox = $false
$form.BackColor = [System.Drawing.Color]::FromArgb(12, 15, 23)

# Header Banner
$headerPanel = New-Object System.Windows.Forms.Panel
$headerPanel.Size = New-Object System.Drawing.Size(680, 70)
$headerPanel.Dock = "Top"
$headerPanel.BackColor = [System.Drawing.Color]::FromArgb(17, 22, 34)
$form.Controls.Add($headerPanel)

$titleLbl = New-Object System.Windows.Forms.Label
$titleLbl.Text = "October 7 Vocal Studio DAW"
$titleLbl.Font = New-Object System.Drawing.Font("Segoe UI", 14, [System.Drawing.FontStyle]::Bold)
$titleLbl.ForeColor = [System.Drawing.Color]::FromArgb(245, 158, 11)
$titleLbl.Location = New-Object System.Drawing.Point(20, 12)
$titleLbl.AutoSize = $true
$headerPanel.Controls.Add($titleLbl)

$subLbl = New-Object System.Windows.Forms.Label
$subLbl.Text = "Official Windows Directory Installer (WASAPI Exclusive & MMCSS Pro Audio)"
$subLbl.Font = New-Object System.Drawing.Font("Segoe UI", 9)
$subLbl.ForeColor = [System.Drawing.Color]::FromArgb(148, 163, 184)
$subLbl.Location = New-Object System.Drawing.Point(22, 40)
$subLbl.AutoSize = $true
$headerPanel.Controls.Add($subLbl)

# Main Container Panel
$contentPanel = New-Object System.Windows.Forms.Panel
$contentPanel.Location = New-Object System.Drawing.Point(20, 85)
$contentPanel.Size = New-Object System.Drawing.Size(625, 385)
$contentPanel.BackColor = [System.Drawing.Color]::FromArgb(12, 15, 23)
$form.Controls.Add($contentPanel)

# Footer Panel
$footerPanel = New-Object System.Windows.Forms.Panel
$footerPanel.Size = New-Object System.Drawing.Size(680, 60)
$footerPanel.Dock = "Bottom"
$footerPanel.BackColor = [System.Drawing.Color]::FromArgb(17, 22, 34)
$form.Controls.Add($footerPanel)

$btnCancel = New-Object System.Windows.Forms.Button
$btnCancel.Text = "Cancel"
$btnCancel.Size = New-Object System.Drawing.Size(85, 32)
$btnCancel.Location = New-Object System.Drawing.Point(560, 14)
$btnCancel.FlatStyle = "Flat"
$btnCancel.BackColor = [System.Drawing.Color]::FromArgb(34, 44, 61)
$btnCancel.ForeColor = [System.Drawing.Color]::White
$btnCancel.Add_Click({ $form.Close() })
$footerPanel.Controls.Add($btnCancel)

$btnNext = New-Object System.Windows.Forms.Button
$btnNext.Text = "Next >"
$btnNext.Size = New-Object System.Drawing.Size(110, 32)
$btnNext.Location = New-Object System.Drawing.Point(440, 14)
$btnNext.FlatStyle = "Flat"
$btnNext.BackColor = [System.Drawing.Color]::FromArgb(245, 158, 11)
$btnNext.ForeColor = [System.Drawing.Color]::Black
$btnNext.Font = New-Object System.Drawing.Font("Segoe UI", 9, [System.Drawing.FontStyle]::Bold)
$footerPanel.Controls.Add($btnNext)

$btnBack = New-Object System.Windows.Forms.Button
$btnBack.Text = "< Back"
$btnBack.Size = New-Object System.Drawing.Size(85, 32)
$btnBack.Location = New-Object System.Drawing.Point(345, 14)
$btnBack.FlatStyle = "Flat"
$btnBack.BackColor = [System.Drawing.Color]::FromArgb(34, 44, 61)
$btnBack.ForeColor = [System.Drawing.Color]::White
$footerPanel.Controls.Add($btnBack)

# Global Wizard State
$currentStep = 0
$selectedInstallPath = $DefaultInstallPath

# Controls for Step 1 (EULA)
$eulaHeader = New-Object System.Windows.Forms.Label
$eulaHeader.Text = "End-User License Agreement & Core PC Authorization"
$eulaHeader.Font = New-Object System.Drawing.Font("Segoe UI", 11, [System.Drawing.FontStyle]::Bold)
$eulaHeader.ForeColor = [System.Drawing.Color]::White
$eulaHeader.Location = New-Object System.Drawing.Point(0, 0)
$eulaHeader.AutoSize = $true

$eulaBox = New-Object System.Windows.Forms.TextBox
$eulaBox.Multiline = $true
$eulaBox.ScrollBars = "Vertical"
$eulaBox.ReadOnly = $true
$eulaBox.Location = New-Object System.Drawing.Point(0, 28)
$eulaBox.Size = New-Object System.Drawing.Size(625, 310)
$eulaBox.BackColor = [System.Drawing.Color]::FromArgb(20, 26, 36)
$eulaBox.ForeColor = [System.Drawing.Color]::FromArgb(203, 213, 225)
$eulaBox.Font = New-Object System.Drawing.Font("Consolas", 8.5)
$eulaBox.Text = $EulaText

$chkEula = New-Object System.Windows.Forms.CheckBox
$chkEula.Text = "I accept the terms in the License Agreement and authorize elevated audio tuning"
$chkEula.Font = New-Object System.Drawing.Font("Segoe UI", 9, [System.Drawing.FontStyle]::Bold)
$chkEula.ForeColor = [System.Drawing.Color]::FromArgb(245, 158, 11)
$chkEula.Location = New-Object System.Drawing.Point(0, 350)
$chkEula.Size = New-Object System.Drawing.Size(625, 25)
$chkEula.Add_CheckedChanged({
    $btnNext.Enabled = $chkEula.Checked
})

# Controls for Step 2 (Path & Options)
$pathHeader = New-Object System.Windows.Forms.Label
$pathHeader.Text = "Select Destination Directory & Components"
$pathHeader.Font = New-Object System.Drawing.Font("Segoe UI", 11, [System.Drawing.FontStyle]::Bold)
$pathHeader.ForeColor = [System.Drawing.Color]::White
$pathHeader.Location = New-Object System.Drawing.Point(0, 0)
$pathHeader.AutoSize = $true

$pathPanel = New-Object System.Windows.Forms.Panel
$pathPanel.Location = New-Object System.Drawing.Point(0, 28)
$pathPanel.Size = New-Object System.Drawing.Size(625, 120)
$pathPanel.BackColor = [System.Drawing.Color]::FromArgb(20, 26, 36)

$lblPath = New-Object System.Windows.Forms.Label
$lblPath.Text = "Installation Directory:"
$lblPath.Font = New-Object System.Drawing.Font("Segoe UI", 9, [System.Drawing.FontStyle]::Bold)
$lblPath.ForeColor = [System.Drawing.Color]::White
$lblPath.Location = New-Object System.Drawing.Point(12, 10)
$lblPath.AutoSize = $true
$pathPanel.Controls.Add($lblPath)

$txtPath = New-Object System.Windows.Forms.TextBox
$txtPath.Text = $DefaultInstallPath
$txtPath.Location = New-Object System.Drawing.Point(12, 34)
$txtPath.Size = New-Object System.Drawing.Size(490, 24)
$txtPath.BackColor = [System.Drawing.Color]::FromArgb(15, 20, 28)
$txtPath.ForeColor = [System.Drawing.Color]::White
$pathPanel.Controls.Add($txtPath)

$btnBrowse = New-Object System.Windows.Forms.Button
$btnBrowse.Text = "Browse..."
$btnBrowse.Location = New-Object System.Drawing.Point(510, 32)
$btnBrowse.Size = New-Object System.Drawing.Size(95, 28)
$btnBrowse.FlatStyle = "Flat"
$btnBrowse.BackColor = [System.Drawing.Color]::FromArgb(34, 44, 61)
$btnBrowse.ForeColor = [System.Drawing.Color]::White
$btnBrowse.Add_Click({
    $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
    $dialog.SelectedPath = $txtPath.Text
    $dialog.Description = "Select Installation Directory for October 7 Vocal Studio DAW"
    if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
        $txtPath.Text = $dialog.SelectedPath
    }
})
$pathPanel.Controls.Add($btnBrowse)

$btnProgFiles = New-Object System.Windows.Forms.Button
$btnProgFiles.Text = "Program Files (System)"
$btnProgFiles.Location = New-Object System.Drawing.Point(12, 70)
$btnProgFiles.Size = New-Object System.Drawing.Size(150, 26)
$btnProgFiles.FlatStyle = "Flat"
$btnProgFiles.BackColor = [System.Drawing.Color]::FromArgb(26, 35, 51)
$btnProgFiles.ForeColor = [System.Drawing.Color]::FromArgb(6, 182, 212)
$btnProgFiles.Add_Click({ $txtPath.Text = $DefaultInstallPath })
$pathPanel.Controls.Add($btnProgFiles)

$btnAppData = New-Object System.Windows.Forms.Button
$btnAppData.Text = "AppData (User)"
$btnAppData.Location = New-Object System.Drawing.Point(170, 70)
$btnAppData.Size = New-Object System.Drawing.Size(150, 26)
$btnAppData.FlatStyle = "Flat"
$btnAppData.BackColor = [System.Drawing.Color]::FromArgb(26, 35, 51)
$btnAppData.ForeColor = [System.Drawing.Color]::FromArgb(6, 182, 212)
$btnAppData.Add_Click({ $txtPath.Text = $AltInstallPath })
$pathPanel.Controls.Add($btnAppData)

$lblSpace = New-Object System.Windows.Forms.Label
$lblSpace.Text = "Space Required: ~260 MB | Available Space: Calculating..."
$lblSpace.ForeColor = [System.Drawing.Color]::FromArgb(148, 163, 184)
$lblSpace.Location = New-Object System.Drawing.Point(330, 75)
$lblSpace.AutoSize = $true
$pathPanel.Controls.Add($lblSpace)

# Options Panel
$optPanel = New-Object System.Windows.Forms.Panel
$optPanel.Location = New-Object System.Drawing.Point(0, 160)
$optPanel.Size = New-Object System.Drawing.Size(625, 210)
$optPanel.BackColor = [System.Drawing.Color]::FromArgb(20, 26, 36)

$lblOptTitle = New-Object System.Windows.Forms.Label
$lblOptTitle.Text = "Windows Audio & Integration Options:"
$lblOptTitle.Font = New-Object System.Drawing.Font("Segoe UI", 9, [System.Drawing.FontStyle]::Bold)
$lblOptTitle.ForeColor = [System.Drawing.Color]::White
$lblOptTitle.Location = New-Object System.Drawing.Point(12, 10)
$lblOptTitle.AutoSize = $true
$optPanel.Controls.Add($lblOptTitle)

$chkDesktop = New-Object System.Windows.Forms.CheckBox
$chkDesktop.Text = "Create Desktop Shortcut ('October 7 Vocal Studio DAW')"
$chkDesktop.Checked = $true
$chkDesktop.ForeColor = [System.Drawing.Color]::White
$chkDesktop.Location = New-Object System.Drawing.Point(15, 36)
$chkDesktop.Size = New-Object System.Drawing.Size(580, 22)
$optPanel.Controls.Add($chkDesktop)

$chkStart = New-Object System.Windows.Forms.CheckBox
$chkStart.Text = "Create Start Menu Program Entry"
$chkStart.Checked = $true
$chkStart.ForeColor = [System.Drawing.Color]::White
$chkStart.Location = New-Object System.Drawing.Point(15, 62)
$chkStart.Size = New-Object System.Drawing.Size(580, 22)
$optPanel.Controls.Add($chkStart)

$chkCert = New-Object System.Windows.Forms.CheckBox
$chkCert.Text = "Review certificate fingerprint only (no Windows trust changes)"
$chkCert.Checked = $false
$chkCert.ForeColor = [System.Drawing.Color]::White
$chkCert.Location = New-Object System.Drawing.Point(15, 88)
$chkCert.Size = New-Object System.Drawing.Size(580, 22)
$optPanel.Controls.Add($chkCert)

$chkMmcss = New-Object System.Windows.Forms.CheckBox
$chkMmcss.Text = "Audio scheduling requires a runtime engine check"
$chkMmcss.Checked = $false
$chkMmcss.Enabled = $false
$chkMmcss.ForeColor = [System.Drawing.Color]::White
$chkMmcss.Location = New-Object System.Drawing.Point(15, 114)
$chkMmcss.Size = New-Object System.Drawing.Size(580, 22)
$optPanel.Controls.Add($chkMmcss)

$chkLaunch = New-Object System.Windows.Forms.CheckBox
$chkLaunch.Text = "Launch October 7 Vocal Studio DAW when setup completes"
$chkLaunch.Checked = $false
$chkLaunch.ForeColor = [System.Drawing.Color]::FromArgb(245, 158, 11)
$chkLaunch.Font = New-Object System.Drawing.Font("Segoe UI", 9, [System.Drawing.FontStyle]::Bold)
$chkLaunch.Location = New-Object System.Drawing.Point(15, 144)
$chkLaunch.Size = New-Object System.Drawing.Size(580, 22)
$optPanel.Controls.Add($chkLaunch)

# Controls for Step 3 (Progress)
$progTitle = New-Object System.Windows.Forms.Label
$progTitle.Text = "Installing Engine Binaries..."
$progTitle.Font = New-Object System.Drawing.Font("Segoe UI", 12, [System.Drawing.FontStyle]::Bold)
$progTitle.ForeColor = [System.Drawing.Color]::FromArgb(245, 158, 11)
$progTitle.Location = New-Object System.Drawing.Point(0, 20)
$progTitle.AutoSize = $true

$progBar = New-Object System.Windows.Forms.ProgressBar
$progBar.Location = New-Object System.Drawing.Point(0, 60)
$progBar.Size = New-Object System.Drawing.Size(625, 24)
$progBar.Style = "Marquee"
$progBar.MarqueeAnimationSpeed = 20

$logTxt = New-Object System.Windows.Forms.TextBox
$logTxt.Multiline = $true
$logTxt.ScrollBars = "Vertical"
$logTxt.ReadOnly = $true
$logTxt.Location = New-Object System.Drawing.Point(0, 100)
$logTxt.Size = New-Object System.Drawing.Size(625, 270)
$logTxt.BackColor = [System.Drawing.Color]::FromArgb(20, 26, 36)
$logTxt.ForeColor = [System.Drawing.Color]::FromArgb(148, 163, 184)
$logTxt.Font = New-Object System.Drawing.Font("Consolas", 8.5)

# Controls for Step 4 (Finished)
$finTitle = New-Object System.Windows.Forms.Label
$finTitle.Text = "[OK] Installation Complete!"
$finTitle.Font = New-Object System.Drawing.Font("Segoe UI", 16, [System.Drawing.FontStyle]::Bold)
$finTitle.ForeColor = [System.Drawing.Color]::FromArgb(16, 185, 129)
$finTitle.Location = New-Object System.Drawing.Point(0, 20)
$finTitle.AutoSize = $true

$finSummary = New-Object System.Windows.Forms.TextBox
$finSummary.Multiline = $true
$finSummary.ReadOnly = $true
$finSummary.Location = New-Object System.Drawing.Point(0, 70)
$finSummary.Size = New-Object System.Drawing.Size(625, 220)
$finSummary.BackColor = [System.Drawing.Color]::FromArgb(20, 26, 36)
$finSummary.ForeColor = [System.Drawing.Color]::White
$finSummary.Font = New-Object System.Drawing.Font("Segoe UI", 9.5)

# Function to Update View
function Show-Step([int]$step) {
    $script:currentStep = $step
    $contentPanel.Controls.Clear()

    if ($step -eq 0) {
        $btnBack.Enabled = $false
        $btnNext.Text = "Accept & Next >"
        $btnNext.Enabled = $chkEula.Checked
        $contentPanel.Controls.Add($eulaHeader)
        $contentPanel.Controls.Add($eulaBox)
        $contentPanel.Controls.Add($chkEula)
    }
    elseif ($step -eq 1) {
        $btnBack.Enabled = $true
        $btnNext.Text = "Install Now"
        $btnNext.Enabled = $true
        $contentPanel.Controls.Add($pathHeader)
        $contentPanel.Controls.Add($pathPanel)
        $contentPanel.Controls.Add($optPanel)
    }
    elseif ($step -eq 2) {
        $btnBack.Enabled = $false
        $btnNext.Enabled = $false
        $btnCancel.Enabled = $false
        $contentPanel.Controls.Add($progTitle)
        $contentPanel.Controls.Add($progBar)
        $contentPanel.Controls.Add($logTxt)

        # Execute deployment in background job
        Start-Installation
    }
    elseif ($step -eq 3) {
        $btnBack.Enabled = $false
        $btnCancel.Enabled = $false
        $btnNext.Text = "Finish & Launch"
        $btnNext.Enabled = $true

        $finSummary.Text = @"
October 7 Vocal Tracking Studio DAW has been successfully installed.

• Destination Path: $($txtPath.Text)
• Windows certificate trust: unchanged
• Existing recordings and session directories: preserved
• Audio devices, scheduling and AI services: require a runtime check
• Automatic uninstall: disabled until a safe ownership manifest exists

Click 'Finish & Launch' to begin using the DAW.
"@
        $contentPanel.Controls.Add($finTitle)
        $contentPanel.Controls.Add($finSummary)
    }
}

function Start-Installation {
    $script:InstallSucceeded = $false
    try {
        $source = [System.IO.Path]::GetFullPath($SourceDir).TrimEnd('\')
        $targetDir = [System.IO.Path]::GetFullPath($txtPath.Text).TrimEnd('\')
        $comparison = [System.StringComparison]::OrdinalIgnoreCase
        if ($source.Equals($targetDir, $comparison) -or
            $targetDir.StartsWith($source + '\', $comparison) -or
            $source.StartsWith($targetDir + '\', $comparison)) {
            throw 'Choose a destination separate from the source package (no nested paths).'
        }
        if ($targetDir -eq [System.IO.Path]::GetPathRoot($targetDir).TrimEnd('\')) {
            throw 'A drive root cannot be an installation directory.'
        }
        $sourceInfo = Get-Item -LiteralPath $source -ErrorAction Stop
        if (-not $sourceInfo.PSIsContainer -or ($sourceInfo.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
            throw 'The source must be an ordinary package directory.'
        }
        # Reject linked destination ancestors before any copy follows them outside the target.
        $ancestor = $targetDir
        while ($ancestor) {
            if (Test-Path -LiteralPath $ancestor) {
                $info = Get-Item -LiteralPath $ancestor -ErrorAction Stop
                if ($info.Attributes -band [IO.FileAttributes]::ReparsePoint) {
                    throw 'Linked installation paths are not supported.'
                }
            }
            $parent = Split-Path -Parent $ancestor
            if ($parent -eq $ancestor) { break }
            $ancestor = $parent
        }
        New-Item -Path $targetDir -ItemType Directory -Force -ErrorAction Stop | Out-Null
        $preservedDirs = @('takes', 'stems', 'recordings', 'projects', 'sessions', 'backups')
        $preservedMedia = @('.wav', '.mp3', '.flac', '.ogg', '.aif', '.aiff', '.mid', '.midi')

        function Copy-PackageEntry($item, [string]$destination) {
            if ($preservedDirs -contains $item.Name.ToLowerInvariant() -or
                ((Test-Path -LiteralPath $destination) -and $preservedMedia -contains $item.Extension.ToLowerInvariant())) {
                $logTxt.AppendText("[PRESERVED] Media/session path: $($item.Name)`r`n")
                return
            }
            if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
                throw "Linked source entries are not supported: $($item.Name)"
            }
            if (Test-Path -LiteralPath $destination) {
                $existing = Get-Item -LiteralPath $destination -ErrorAction Stop
                if ($existing.Attributes -band [IO.FileAttributes]::ReparsePoint) {
                    throw "Linked destination entries are not supported: $($item.Name)"
                }
            }
            if ($item.PSIsContainer) {
                New-Item -Path $destination -ItemType Directory -Force -ErrorAction Stop | Out-Null
                foreach ($child in Get-ChildItem -LiteralPath $item.FullName -Force -ErrorAction Stop) {
                    Copy-PackageEntry $child (Join-Path $destination $child.Name)
                }
            } else {
                Copy-Item -LiteralPath $item.FullName -Destination $destination -Force -ErrorAction Stop
            }
        }
        foreach ($item in Get-ChildItem -LiteralPath $source -Force -ErrorAction Stop) {
            Copy-PackageEntry $item (Join-Path $targetDir $item.Name)
        }
        $logTxt.AppendText("[OK] Application files copied; media and session directories preserved.`r`n")

        if ($chkCert.Checked) {
            $cer = Join-Path $targetDir 'October7_CodeSigning.cer'
            if (Test-Path -LiteralPath $cer) {
                $hash = (Get-FileHash -LiteralPath $cer -Algorithm SHA256 -ErrorAction Stop).Hash
                $logTxt.AppendText("[REVIEW] Certificate file SHA-256: $hash`r`n")
            }
            $logTxt.AppendText("[NOTICE] Review the signer independently before any manual trust change. No trust store was changed.`r`n")
        }

        $desktop = [System.Environment]::GetFolderPath('Desktop')
        $startMenu = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\October 7 Vocal Studio'
        $exePath = Join-Path $targetDir 'October7_VocalStudio_Native.exe'
        if (-not (Test-Path -LiteralPath $exePath -PathType Leaf)) {
            $exePath = Join-Path $targetDir 'October7_VocalStudio_DAW.exe'
        }
        foreach ($shortcut in @(
            @{ Enabled = $chkDesktop.Checked; Folder = $desktop; Label = 'Desktop' },
            @{ Enabled = $chkStart.Checked; Folder = $startMenu; Label = 'Start Menu' }
        )) {
            if (-not $shortcut.Enabled) { continue }
            New-Item -Path $shortcut.Folder -ItemType Directory -Force -ErrorAction Stop | Out-Null
            $wsh = New-Object -ComObject WScript.Shell -ErrorAction Stop
            $sc = $wsh.CreateShortcut((Join-Path $shortcut.Folder 'October 7 Vocal Studio DAW.lnk'))
            $sc.TargetPath = $exePath
            $sc.WorkingDirectory = $targetDir
            $sc.Save()
            $logTxt.AppendText("[OK] $($shortcut.Label) shortcut created.`r`n")
        }

        # Do not delete recordings or an untracked application tree during uninstall.
        $uninstScript = @'
@echo off
title October 7 Vocal Studio - Data Preservation
echo Automatic uninstall is disabled to preserve recordings and project data.
echo No files or shortcuts have been removed.
echo Back up your media and use a reviewed install manifest before removal.
exit /b 1
'@
        Set-Content -LiteralPath (Join-Path $targetDir 'Uninstall_October7_DAW.bat') -Value $uninstScript -Encoding Ascii -ErrorAction Stop
        $logTxt.AppendText("[SUCCESS] Deployment completed. Windows trust and audio settings were not changed.`r`n")
        $script:InstallSucceeded = $true
        Show-Step 3
    } catch {
        $logTxt.AppendText("[ERROR] Installation stopped: $($_.Exception.Message)`r`n")
        $btnCancel.Enabled = $true
        [System.Windows.Forms.MessageBox]::Show($_.Exception.Message, 'Installation error') | Out-Null
    }
}


$btnNext.Add_Click({
    if ($script:currentStep -eq 0) {
        Show-Step 1
    }
    elseif ($script:currentStep -eq 1) {
        Show-Step 2
    }
    elseif ($script:currentStep -eq 3) {
        if ($chkLaunch.Checked) {
            $exe = Join-Path $txtPath.Text "October7_VocalStudio_Native.exe"
            if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) {
                $exe = Join-Path $txtPath.Text "October7_VocalStudio_DAW.exe"
            }
            if (Test-Path $exe) {
                Start-Process -FilePath $exe -WorkingDirectory $txtPath.Text
            }
        }
        $form.Close()
    }
})

$btnBack.Add_Click({
    if ($script:currentStep -gt 0) {
        Show-Step ($script:currentStep - 1)
    }
})

# Show Initial Step
Show-Step 0
[void]$form.ShowDialog()
if (-not $script:InstallSucceeded) { exit 1 }
