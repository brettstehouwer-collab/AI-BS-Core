param([ValidateSet('sample1','sample2','final')][string]$Sample = 'sample1')
$ErrorActionPreference = 'Stop'
$taskRoot = $PSScriptRoot
$os = Get-CimInstance Win32_OperatingSystem
$mem = Get-CimInstance Win32_PerfFormattedData_PerfOS_Memory
$pc = Get-CimInstance Win32_ComputerSystem
$pageItem = Get-Item -LiteralPath 'C:\pagefile.sys' -Force
$processes = @(Get-Process)
$top = @($processes | Sort-Object PrivateMemorySize64 -Descending | Select-Object -First 12 | ForEach-Object {
    [pscustomobject]@{pid=$_.Id;name=$_.ProcessName;private_bytes=$_.PrivateMemorySize64;working_set_bytes=$_.WorkingSet64;created_utc=$_.StartTime.ToUniversalTime().ToString('o')}
})
$codex = @($processes | Where-Object ProcessName -eq 'codex' | ForEach-Object {
    [pscustomobject]@{pid=$_.Id;name=$_.ProcessName;exe=$_.Path;private_bytes=$_.PrivateMemorySize64;working_set_bytes=$_.WorkingSet64;created_utc=$_.StartTime.ToUniversalTime().ToString('o')}
})
$snapshot = [ordered]@{
    observed_utc=(Get-Date).ToUniversalTime().ToString('o');
    last_boot_utc=$os.LastBootUpTime.ToUniversalTime().ToString('o');
    windows_user=[Environment]::UserName;
    total_physical_bytes=([uint64]$os.TotalVisibleMemorySize * 1024);
    free_physical_bytes=([uint64]$os.FreePhysicalMemory * 1024);
    committed_bytes=$mem.CommittedBytes;commit_limit_bytes=$mem.CommitLimit;
    commit_percent=([double]$mem.CommittedBytes / [double]$mem.CommitLimit * 100);
    pagefiles=@(Get-CimInstance Win32_PageFileUsage | Select-Object Name,AllocatedBaseSize,CurrentUsage,PeakUsage);
    pagefile_file_bytes=$pageItem.Length;
    automatic_managed_pagefile=$pc.AutomaticManagedPagefile;
    pagefile_settings=@(Get-CimInstance Win32_PageFileSetting | Select-Object Name,InitialSize,MaximumSize);
    registry_paging_files=@((Get-ItemProperty -LiteralPath 'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management').PagingFiles);
    drives=@(Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=3' | Select-Object DeviceID,Size,FreeSpace);
    codex=$codex;top_processes=$top;
    scope='Read-only OS/process queries; no environment, command line, memory dump, deletion or settings changes'
}
$snapshot | ConvertTo-Json -Depth 7 | Set-Content -LiteralPath (Join-Path $taskRoot ($Sample + '.json')) -Encoding UTF8
$cDrive = $snapshot.drives | Where-Object DeviceID -eq 'C:'
[pscustomobject]@{sample=$Sample;observed_utc=$snapshot.observed_utc;last_boot_utc=$snapshot.last_boot_utc;commit_gib=[math]::Round($snapshot.committed_bytes/1GB,3);commit_percent=[math]::Round($snapshot.commit_percent,2);ram_used_gib=[math]::Round(($snapshot.total_physical_bytes-$snapshot.free_physical_bytes)/1GB,3);c_free_gib=[math]::Round($cDrive.FreeSpace/1GB,3);pagefile_allocated_mb=$snapshot.pagefiles[0].AllocatedBaseSize;pagefile_used_mb=$snapshot.pagefiles[0].CurrentUsage;codex=$codex} | ConvertTo-Json -Depth 4
