$dirs = @('C:\AI-BS\frontend\src', 'C:\AI-BS\frontend\components', 'C:\AI-BS\frontend\public')
$files = Get-ChildItem -Path $dirs -Include '*.jsx','*.json','*.js' -Recurse -File | Where-Object { $_.FullName -notmatch 'node_modules' }
$rootFiles = Get-ChildItem -Path 'C:\AI-BS\frontend' -File | Where-Object { $_.Name -match '\.(jsx|json|js)$' }
$allFiles = @($files) + @($rootFiles)

$count = 0
foreach ($f in $allFiles) {
    try {
        $content = [System.IO.File]::ReadAllText($f.FullName, [System.Text.Encoding]::UTF8)
        if ($content -match '5\.230\.[0-3]') {
            $updated = $content -replace '5\.230\.[0-3]', '5.230.4'
            [System.IO.File]::WriteAllText($f.FullName, $updated, [System.Text.Encoding]::UTF8)
            Write-Host "Updated: $($f.FullName)"
            $count++
        }
    } catch {}
}
Write-Host "Total files updated: $count"
