# Pure predicates only. Safe to dot-source in trusted infrastructure tests.
function Assert-AIBSGuestFacts([hashtable]$Facts) {
    if ($null -eq $Facts -or $Facts.Count -ne 7) { throw 'Guest identity observation is incomplete.' }
    if ($Facts.UUID -isnot [string] -or
        $Facts.UUID -ine '6c5a53da-ab80-4ecb-8be6-4059266f736e' -or
        $Facts.Model -cne 'VirtualBox' -or
        $Facts.Manufacturer -cnotin @('innotek GmbH','Oracle Corporation')) {
        throw 'This installer is restricted to the exact AI-BS VirtualBox guest.'
    }
    if ($Facts.SID -isnot [string] -or $Facts.SID -notmatch '^S-1-5-21-\d+-\d+-\d+-\d+$' -or
        $Facts.SID.StartsWith('S-1-5-21-2133766663-4066672948-2456486318-', [StringComparison]::Ordinal)) {
        throw 'Host or unknown account identity rejected.'
    }
    if ($Facts.Elevated -isnot [bool] -or -not $Facts.Elevated) {
        throw 'Run the reviewed installer in an elevated guest session; no automatic elevation.'
    }
    if ($Facts.Is64Bit -isnot [bool] -or -not $Facts.Is64Bit) { throw 'A 64-bit guest process is required.' }
    if (($Facts.EnabledNICCount -isnot [int] -and $Facts.EnabledNICCount -isnot [long]) -or
        $Facts.EnabledNICCount -ne 0) { throw 'Guest network observation must show zero enabled adapters.' }
}

function Assert-AIBSGuestMedia([string]$Root, [hashtable]$Volume) {
    if ($Root -cnotmatch '^[D-Z]:\\$' -or $null -eq $Volume -or
        $Volume.DeviceID -cne $Root.Substring(0,2) -or
        $Volume.DriveType -ne 5 -or $Volume.VolumeName -cne 'AIBS_PROV') {
        throw 'Expected the AIBS_PROV optical volume root.'
    }
}

function Assert-AIBSRuntimeReport([hashtable]$Report) {
    if ($null -eq $Report -or $Report.Count -ne 5 -or
        $Report.Node -cne 'v24.22.1' -or $Report.Python -cne 'Python 3.13.17' -or
        $Report.Pywin32 -cne '312' -or $Report.Psutil -cne '7.2.2' -or
        $Report.Imports -isnot [bool] -or -not $Report.Imports) {
        throw 'Exact guest runtime/package versions and imports were not verified.'
    }
}

function Assert-AIBSInstallerExit([int]$Code) {
    if ($Code -eq 3010 -or $Code -eq 1641) { throw 'REBOOT_REQUIRED: provisioning is not complete.' }
    if ($Code -ne 0) { throw "Installer failed with exit code $Code." }
}
