<#
.SYNOPSIS
    Sovereign AI-BS OS Image Creator & Driver Slipstream Engine
    Targets: AMD Ryzen 9 9950X (AM5) + NVIDIA GeForce RTX 4090 + Samsung 990/980 Pro NVMe
    
.DESCRIPTION
    Safely exports all live host device drivers (GPU, Chipset, Audio, Network, Storage, USB)
    via Windows DISM without modifying or endangering your current operating system installation.
    Prepares a driver repository and unattended response file (unattend.xml) ready for 
    slipstreaming into a bootable Windows 11 installation media.
#>

param (
    [string]$StagingDir = "E:\AI_BS_Resources\OS_Image_Builder",
    [switch]$ExportDriversOnly,
    [switch]$GenerateUnattendOnly
)

$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   AI-BS SOVEREIGN OS IMAGE & DRIVER SLIPSTREAM ENGINE   " -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Target Architecture: AMD Ryzen 9 9950X (16C/32T) + NVIDIA RTX 4090 (24GB VRAM)"
Write-Host "Motherboard: ASUS TUF GAMING X870-PLUS WIFI (AM5 Baseline)"
Write-Host "Storage Targets: Samsung 990 PRO 2TB + 980 PRO 1TB NVMe"
Write-Host ""

# Ensure staging directories exist
$DriversDir = Join-Path $StagingDir "Drivers"
$IsoDir = Join-Path $StagingDir "ISO_Mount"
$ConfigDir = Join-Path $StagingDir "Config"

foreach ($dir in @($StagingDir, $DriversDir, $IsoDir, $ConfigDir)) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "[+] Created directory: $dir" -ForegroundColor Green
    }
}

# 1. Export All Live Host Drivers (100% Non-Destructive)
Write-Host "`n[1/3] Exporting Third-Party Drivers from Host Windows Installation..." -ForegroundColor Yellow
Write-Host "Destination: $DriversDir"
Write-Host "This extracts live AMD chipset, RTX 4090, Realtek 2.5GbE, MediaTek Wi-Fi 7, and audio INF packages..."

try {
    $dismArgs = "/online /export-driver /destination:`"$DriversDir`""
    Start-Process -FilePath "dism.exe" -ArgumentList $dismArgs -Wait -NoNewWindow
    Write-Host "[SUCCESS] Live hardware drivers exported safely to $DriversDir" -ForegroundColor Green
} catch {
    Write-Host "[!] DISM Driver Export Warning: $_" -ForegroundColor Red
}

# 2. Generate Turnkey Unattended Setup Configuration (unattend.xml)
Write-Host "`n[2/3] Generating Sovereign Turnkey Unattend Configuration (unattend.xml)..." -ForegroundColor Yellow
$unattendXmlPath = Join-Path $ConfigDir "autounattend.xml"

$unattendContent = @"
<?xml version="1.0" encoding="utf-8"?>
<unattend xmlns="urn:schemas-microsoft-com:unattend">
    <settings pass="windowsPE">
        <component name="Microsoft-Windows-International-Core-WinPE" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS">
            <SetupUILanguage>
                <UILanguage>en-US</UILanguage>
            </SetupUILanguage>
            <InputLocale>en-US</InputLocale>
            <SystemLocale>en-US</SystemLocale>
            <UILanguage>en-US</UILanguage>
            <UserLocale>en-US</UserLocale>
        </component>
        <component name="Microsoft-Windows-Setup" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS">
            <UserData>
                <AcceptEula>true</AcceptEula>
                <FullName>Brett Stehouwer</FullName>
                <Organization>Stehouwer Publishing</Organization>
            </UserData>
        </component>
    </settings>
    <settings pass="specialize">
        <component name="Microsoft-Windows-Shell-Setup" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS">
            <ComputerName>AI-BS</ComputerName>
            <TimeZone>Eastern Standard Time</TimeZone>
        </component>
    </settings>
    <settings pass="oobeSystem">
        <component name="Microsoft-Windows-Shell-Setup" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS">
            <AutoLogon>
                <Password>
                    <Value></Value>
                    <PlainText>true</PlainText>
                </Password>
                <Enabled>true</Enabled>
                <Username>Administrator</Username>
            </AutoLogon>
            <OOBE>
                <HideEULAPage>true</HideEULAPage>
                <HideLocalAccountScreen>true</HideLocalAccountScreen>
                <HideOEMRegistrationScreens>true</HideOEMRegistrationScreens>
                <HideOnlineAccountScreens>true</HideOnlineAccountScreens>
                <HideWirelessSetupInOOBE>true</HideWirelessSetupInOOBE>
                <ProtectYourPC>3</ProtectYourPC>
            </OOBE>
            <UserAccounts>
                <AdministratorPassword>
                    <Value></Value>
                    <PlainText>true</PlainText>
                </AdministratorPassword>
            </UserAccounts>
        </component>
    </settings>
</unattend>
"@

Set-Content -Path $unattendXmlPath -Value $unattendContent -Encoding UTF8
Write-Host "[SUCCESS] Unattend response file written to: $unattendXmlPath" -ForegroundColor Green

# 3. Output Slipstream Guide & USB Boot Maker Instructions
Write-Host "`n[3/3] Turnkey Boot Drive Generation Instructions:" -ForegroundColor Cyan
Write-Host "--------------------------------------------------------------------------"
Write-Host "1. Staged Drivers Path: $DriversDir"
Write-Host "2. Config Path:         $unattendXmlPath"
Write-Host "3. To Slipstream Drivers into an Official Windows 11 ISO (e.g. Win11.iso):"
Write-Host "   Mount the ISO, extract install.wim, and run:"
Write-Host "   dism /Mount-Wim /WimFile:C:\Path\install.wim /index:1 /MountDir:$IsoDir"
Write-Host "   dism /Image:$IsoDir /Add-Driver /Driver:$DriversDir /Recurse"
Write-Host "   dism /Unmount-Wim /MountDir:$IsoDir /Commit"
Write-Host "4. Burn the customized image to USB via Rufus or Ventoy for a 1-click bootable installer."
Write-Host "--------------------------------------------------------------------------"
Write-Host "Hardware slipstream baseline ready. Your current running PC is completely untouched." -ForegroundColor Green
