<#
.SYNOPSIS
    Synchronizes primary Google Chrome profile data to the AI-BS developer Chrome profile.

.DESCRIPTION
    Safely backs up the target developer Chrome profile and migrates authentication
    cookies, login data, bookmarks, history, extensions, sessions, and web storage from
    the host Chrome installation (C:\Users\footb\AppData\Local\Google\Chrome\User Data)
    to the automated developer Chrome instance (C:\Users\footb\.cache\chrome-devtools-mcp\chrome-profile).

.PARAMETER Fast
    If specified (default), skips massive disposable video editor blob caches and transient
    network/GPU caches, reducing the transfer from ~29 GB to ~150 MB in ~3 seconds.

.PARAMETER Full
    If specified, performs an exact 1:1 raw copy of the entire 29 GB profile tree.

.PARAMETER IncludeWorkProfile
    Copies 'Profile 1' (Work profile: brett.stehouwer@ubreakifix.com) in addition to 'Default'.
    Default is $true.

.PARAMETER KillChrome
    Forces closure of running Chrome processes before copying to release exclusive SQLite locks.
    Default is $true.
#>

[CmdletBinding()]
param(
    [switch]$Full = $false,
    [bool]$IncludeWorkProfile = $true,
    [bool]$KillChrome = $true
)

$ErrorActionPreference = "Stop"

$sourceUserData = "C:\Users\footb\AppData\Local\Google\Chrome\User Data"
$targetUserData = "C:\Users\footb\.cache\chrome-devtools-mcp\chrome-profile"

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "  AI-BS Ecosystem: Chrome Profile -> Developer Chrome Sync" -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

# 1. Validate Source Paths
if (-not (Test-Path -Path $sourceUserData)) {
    Write-Error "Source Chrome User Data folder does not exist at: $sourceUserData"
}

$sourceDefault = Join-Path $sourceUserData "Default"
if (-not (Test-Path -Path $sourceDefault)) {
    Write-Error "Source 'Default' profile does not exist at: $sourceDefault"
}

# 2. Handle Running Chrome Processes
$chromeProcesses = Get-Process -Name "chrome" -ErrorAction SilentlyContinue
if ($chromeProcesses) {
    if ($KillChrome) {
        Write-Host "Closing active Chrome processes ($($chromeProcesses.Count) instances) to release SQLite database locks..." -ForegroundColor Yellow
        Stop-Process -Name "chrome" -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 3
        # Double check
        $remaining = Get-Process -Name "chrome" -ErrorAction SilentlyContinue
        if ($remaining) {
            Write-Host "Waiting for remaining processes to exit..." -ForegroundColor Yellow
            $remaining | Stop-Process -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 2
        }
        Write-Host "All Chrome processes terminated successfully." -ForegroundColor Green
    } else {
        Write-Error "Chrome processes are currently running. Pass -KillChrome or manually close Chrome before syncing."
    }
}

# 3. Create Safety Backup of Existing Developer Profile
if (Test-Path -Path $targetUserData) {
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $backupDir = "C:\Users\footb\.cache\chrome-devtools-mcp\chrome-profile_backup_$timestamp"
    Write-Host "Backing up existing developer profile to: $backupDir" -ForegroundColor Cyan
    try {
        Copy-Item -Path $targetUserData -Destination $backupDir -Recurse -Force
        Write-Host "Backup created successfully." -ForegroundColor Green
    } catch {
        Write-Warning "Failed to create full backup: $($_.Exception.Message)"
    }
} else {
    New-Item -Path $targetUserData -ItemType Directory -Force | Out-Null
}

# 4. Copy Root Files (Local State is critical for DPAPI os_crypt keys)
Write-Host "Copying Local State and system configuration..." -ForegroundColor Cyan
$sourceLocalState = Join-Path $sourceUserData "Local State"
if (Test-Path -Path $sourceLocalState) {
    Copy-Item -Path $sourceLocalState -Destination (Join-Path $targetUserData "Local State") -Force
    Write-Host "Local State copied." -ForegroundColor Green
}

# 5. Define Copy Helper Using Robocopy
function Sync-Directory {
    param(
        [string]$Source,
        [string]$Destination,
        [bool]$IsFastMode
    )

    if (-not (Test-Path -Path $Destination)) {
        New-Item -Path $Destination -ItemType Directory -Force | Out-Null
    }

    $excludedFiles = @("lockfile", "DevToolsActivePort", "*.pma", "LOG", "LOG.old")

    if ($IsFastMode) {
        # Exclude disposable cache directories and large video editor temp blobs
        $excludedDirs = @(
            "Cache",
            "Code Cache",
            "DawnGraphiteCache",
            "DawnWebGPUCache",
            "GPUCache",
            "CacheStorage",
            "ScriptCache",
            "Crashpad",
            "*streamlabs*.indexeddb.blob",
            "*visla*.indexeddb.blob"
        )
        
        Write-Host "Executing lean sync (excluding video blobs and disposable cache)..." -ForegroundColor Yellow
        $args = @(
            "`"$Source`"",
            "`"$Destination`"",
            "/E",
            "/R:1",
            "/W:1",
            "/NP",
            "/NFL",
            "/NDL",
            "/NJH",
            "/NJS"
        )

        if ($excludedDirs.Count -gt 0) {
            $args += "/XD"
            $args += $excludedDirs
        }

        if ($excludedFiles.Count -gt 0) {
            $args += "/XF"
            $args += $excludedFiles
        }
    } else {
        Write-Host "Executing full 1:1 sync (including all caches and video blobs)..." -ForegroundColor Yellow
        $args = @(
            "`"$Source`"",
            "`"$Destination`"",
            "/E",
            "/R:2",
            "/W:1",
            "/NP",
            "/NFL",
            "/NDL",
            "/NJH",
            "/NJS"
        )
        if ($excludedFiles.Count -gt 0) {
            $args += "/XF"
            $args += $excludedFiles
        }
    }

    $process = Start-Process -FilePath "robocopy.exe" -ArgumentList ($args -join " ") -Wait -PassThru -NoNewWindow
    
    # Robocopy exit code < 8 indicates success
    if ($process.ExitCode -ge 8) {
        throw "Robocopy failed with exit code $($process.ExitCode)"
    }
}

# 6. Copy Default Profile
$isFast = -not $Full
Write-Host "Synchronizing 'Default' profile..." -ForegroundColor Cyan
Sync-Directory -Source $sourceDefault -Destination (Join-Path $targetUserData "Default") -IsFastMode $isFast
Write-Host "'Default' profile synchronized." -ForegroundColor Green

# 7. Copy Profile 1 (Work) if requested
$sourceProfile1 = Join-Path $sourceUserData "Profile 1"
if ($IncludeWorkProfile -and (Test-Path -Path $sourceProfile1)) {
    Write-Host "Synchronizing 'Profile 1' (Work) profile..." -ForegroundColor Cyan
    Sync-Directory -Source $sourceProfile1 -Destination (Join-Path $targetUserData "Profile 1") -IsFastMode $isFast
    Write-Host "'Profile 1' synchronized." -ForegroundColor Green
}

# 8. Post-Sync Lock Cleanup
Write-Host "Sanitizing lockfiles in target developer profile..." -ForegroundColor Cyan
$staleLocks = Get-ChildItem -Path $targetUserData -Recurse -Force -Include "lockfile", "DevToolsActivePort", "*.pma" -ErrorAction SilentlyContinue
foreach ($lock in $staleLocks) {
    Remove-Item -Path $lock.FullName -Force -ErrorAction SilentlyContinue
}

# 9. Report Resulting Stats
$totalMB = (Get-ChildItem -Path $targetUserData -Recurse -File -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum / 1MB
Write-Host "=================================================================" -ForegroundColor Green
Write-Host "  Profile Migration Completed Successfully!" -ForegroundColor Green
Write-Host "  Target Location : $targetUserData" -ForegroundColor Green
Write-Host "  Target Size     : $([math]::Round($totalMB, 2)) MB" -ForegroundColor Green
Write-Host "=================================================================" -ForegroundColor Green
