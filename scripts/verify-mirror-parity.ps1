<#
.SYNOPSIS
    Verifies 100% SHA-256 byte parity across all AI-BS frontend mirror paths.

.DESCRIPTION
    Scans a canonical reference directory, calculates SHA-256 hashes for all 
    tracked source files, and validates that all mirror directories contain 
    identical file structures and byte-identical hashes. Exits with code 0 on 
    parity, or code 1 on mismatch/missing files.

.NOTES
    Execution: powershell.exe -ExecutionPolicy Bypass -File .\verify-mirror-parity.ps1
#>

[CmdletBinding()]
param (
    [Parameter(Mandatory = $false)]
    [string]$SourcePath = "C:\AI-BS\frontend\src\components",

    [Parameter(Mandatory = $false)]
    [string[]]$MirrorPaths = @(
        "C:\AI-BS\frontend\components",
        "C:\AI-BS\frontend\src\components\components",
        "C:\AI-BS\frontend\components\components"
    ),

    [Parameter(Mandatory = $false)]
    [string[]]$ExcludePatterns = @(
        "node_modules",
        "dist",
        "build",
        ".git",
        ".next",
        "*.log",
        "*.bak",
        ".DS_Store",
        "components"
    )
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-RelativePath {
    param (
        [string]$BasePath,
        [string]$FullPath
    )
    $normalizedBase = $BasePath.TrimEnd('\') + '\'
    if ($FullPath.StartsWith($normalizedBase, [System.StringComparison]::OrdinalIgnoreCase)) {
        return $FullPath.Substring($normalizedBase.Length)
    }
    return $FullPath
}

function Should-Exclude {
    param (
        [string]$RelativePath,
        [string[]]$Patterns
    )
    foreach ($pattern in $Patterns) {
        if ($pattern.StartsWith("*")) {
            $extension = $pattern.Substring(1)
            if ($RelativePath.EndsWith($extension, [System.StringComparison]::OrdinalIgnoreCase)) {
                return $true
            }
        } else {
            $pathSegments = $RelativePath.Split([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar)
            if ($pathSegments -contains $pattern) {
                return $true
            }
        }
    }
    return $false
}

function Compute-DirectoryHashMap {
    param (
        [string]$RootPath,
        [string[]]$Exclusions
    )
    
    if (-not (Test-Path -LiteralPath $RootPath)) {
        throw "Target directory does not exist: $RootPath"
    }

    $hashMap = @{}
    $files = Get-ChildItem -LiteralPath $RootPath -Recurse -File

    foreach ($file in $files) {
        $relPath = Get-RelativePath -BasePath $RootPath -FullPath $file.FullName
        
        if (Should-Exclude -RelativePath $relPath -Patterns $Exclusions) {
            continue
        }

        $hashResult = Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256
        $hashMap[$relPath] = $hashResult.Hash
    }

    return $hashMap
}

# --- Execution Entry Point ---

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " AI-BS MULTI-MIRROR SHA-256 PARITY AUDITOR" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Canonical Reference: $SourcePath"
Write-Host "Target Mirrors:      $($MirrorPaths.Count)"
Write-Host ""

if (-not (Test-Path -LiteralPath $SourcePath)) {
    Write-Error "Canonical source path not found: $SourcePath"
    exit 1
}

Write-Host "[1/2] Indexing and hashing canonical source files..." -ForegroundColor Yellow
$sourceMap = Compute-DirectoryHashMap -RootPath $SourcePath -Exclusions $ExcludePatterns
Write-Host "Indexed $($sourceMap.Count) files in canonical source." -ForegroundColor Green
Write-Host ""

$totalFailures = 0
$mirrorIndex = 1

Write-Host "[2/2] Validating mirrors..." -ForegroundColor Yellow

foreach ($mirror in $MirrorPaths) {
    Write-Host "------------------------------------------------------------"
    Write-Host "Checking Mirror [$mirrorIndex/$($MirrorPaths.Count)]: $mirror" -ForegroundColor Cyan

    if (-not (Test-Path -LiteralPath $mirror)) {
        Write-Host "  [CRITICAL] Mirror directory missing: $mirror" -ForegroundColor Red
        $totalFailures++
        $mirrorIndex++
        continue
    }

    $mirrorMap = Compute-DirectoryHashMap -RootPath $mirror -Exclusions $ExcludePatterns
    $mirrorMismatches = 0
    $missingInMirror = 0
    $extraInMirror = 0

    # 1. Verify all source files exist in mirror with identical SHA-256 hashes
    foreach ($relPath in $sourceMap.Keys) {
        if (-not $mirrorMap.ContainsKey($relPath)) {
            Write-Host "  [MISSING] $relPath" -ForegroundColor Red
            $missingInMirror++
            $mirrorMismatches++
            continue
        }

        if ($sourceMap[$relPath] -ne $mirrorMap[$relPath]) {
            Write-Host "  [HASH MISMATCH] $relPath" -ForegroundColor Red
            Write-Host "    Expected: $($sourceMap[$relPath])" -ForegroundColor DarkGray
            Write-Host "    Actual:   $($mirrorMap[$relPath])" -ForegroundColor DarkRed
            $mirrorMismatches++
        }
    }

    # 2. Check for unindexed or orphaned files inside the mirror
    foreach ($relPath in $mirrorMap.Keys) {
        if (-not $sourceMap.ContainsKey($relPath)) {
            Write-Host "  [ORPHANED] $relPath exists in mirror but not in source" -ForegroundColor Yellow
            $extraInMirror++
            $mirrorMismatches++
        }
    }

    if ($mirrorMismatches -eq 0) {
        Write-Host "  [PARITY VERIFIED] 100% byte match ($($sourceMap.Count)/$($sourceMap.Count) files identical)" -ForegroundColor Green
    } else {
        Write-Host "  [FAILED] Violations detected: $mirrorMismatches (Missing: $missingInMirror, Mismatches: $($mirrorMismatches - $missingInMirror - $extraInMirror), Orphans: $extraInMirror)" -ForegroundColor Red
        $totalFailures++
    }

    $mirrorIndex++
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan

if ($totalFailures -gt 0) {
    Write-Host "AUDIT RESULT: FAILED ($totalFailures mirrors out of sync)" -ForegroundColor Red
    exit 1
} else {
    Write-Host "AUDIT RESULT: PASSED (100% SHA-256 byte parity confirmed)" -ForegroundColor Green
    exit 0
}
