# Candidate replacement for setup status publication; not loaded by live controller yet.
function Publish-ImmutableSetupStatus([string]$Channel,[Collections.IDictionary]$Status,[int]$Publication){
    if($Publication -lt 1 -or $Publication -gt 4096){throw 'Status publication bound exceeded.'}
    $directory=Get-Item -LiteralPath $Channel -Force -ErrorAction Stop
    if(-not $directory.PSIsContainer -or ($directory.Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'Regular status directory required.'}
    $record=[ordered]@{}
    foreach($key in $Status.Keys){$record[$key]=$Status[$key]}
    $record.Publication=$Publication
    $bytes=[Text.Encoding]::UTF8.GetBytes(($record | ConvertTo-Json -Depth 8))
    if($bytes.Length -gt 2097152){throw 'Status record exceeds2MiB.'}
    $stem='status_{0:d8}' -f $Publication
    $pending=Join-Path $Channel ($stem+'.pending')
    $dest=Join-Path $Channel ($stem+'.json')
    if(Test-Path -LiteralPath $dest){throw 'Status publication already exists.'}
    $file=[IO.File]::Open($pending,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try{$file.Write($bytes,0,$bytes.Length);$file.Flush($true)}finally{$file.Dispose()}
    [IO.File]::Move($pending,$dest)
    return $dest
}
function Read-ImmutableSetupStatus([string]$Channel){
    $latest=@(Get-ChildItem -LiteralPath $Channel -File -Filter 'status_????????.json' | Where-Object {$_.Name -cmatch '^status_[0-9]{8}\.json$'} | Sort-Object Name -Descending | Select-Object -First 1)
    if($latest.Count -ne 1){throw 'No complete status publication.'}
    $node=$latest[0]
    if(($node.Attributes -band [IO.FileAttributes]::ReparsePoint) -or $node.Length -gt 2097152){throw 'Invalid status publication file.'}
    $file=[IO.File]::Open($node.FullName,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
    $reader=New-Object IO.StreamReader($file)
    try{$raw=$reader.ReadToEnd()}finally{$reader.Dispose()}
    $status=$raw | ConvertFrom-Json -ErrorAction Stop
    $number=[int]$node.BaseName.Substring(7)
    if(($status.Publication -isnot [int] -and $status.Publication -isnot [long]) -or $status.Publication -ne $number -or $number -lt 1 -or $number -gt 4096){throw 'Status publication identity differs.'}
    return $status
}
