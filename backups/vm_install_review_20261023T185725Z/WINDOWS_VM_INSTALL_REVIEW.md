# Windows VM installation review

October 23, 2026 | Application v5.329.17 | Plan revision 1.8

## Exact candidate verified from Oracle metadata

Oracle LATEST-STABLE.TXT returned **7.2.22**. Its SHA256SUMS names **VirtualBox-7.2.22-175245-Win.exe** with SHA-256:

`afd0ff1656cbe04ed88ce619594ae021419d97cce89fa9bdc443e9a963f1713f`

[Installer](https://download.virtualbox.org/virtualbox/7.2.22/VirtualBox-7.2.22-175245-Win.exe) | [Official checksums](https://download.virtualbox.org/virtualbox/7.2.22/SHA256SUMS)

Only small metadata files were read over HTTPS. The installer has NOT been downloaded, its Authenticode signature has NOT been verified, and nothing has been installed. This pins a review candidate, not a tested build-26300 configuration. Do not silently substitute a newer version after approval.

## Proposed bounded installation authorization

Install only the Oracle base package to its default Program Files location; omit Extension Pack, USB, bridged/host-only networking and Python bindings when exposed as optional components. Do not change Windows edition, WSL, VBS, boot configuration, GPU drivers, DNS or personal files. No automatic reboot. If the installer requires reboot or unplanned network/security changes, stop at that boundary and ask. Expected scope includes installation of required VirtualBox virtualization drivers and may display an elevation prompt.

Before executing: download the pinned file into a labeled private staging folder; independently compare Get-FileHash SHA256 against the pinned official value; require Get-AuthenticodeSignature Status Valid and verify the expected Oracle publisher/certificate chain. Reject signature warnings or mismatches; do not follow documentation advice to accept unsigned drivers. Capture current named AI-BS service states, listeners and relevant host network/boot configuration without dumping environment values or credentials. Recheck storage headroom and pending reboot state. Stop on any mismatch before launching the installer.

After installation: verify installed version and executable signature, unchanged service health/network settings and no unapproved reboot. Keep expanded execution disabled. Run compatibility checks only against a new disposable guest, never by opening original document stores. Save installer metadata and actual results locally. Missing features or failed compatibility are failures, not reasons to disable host protections.

## Guest prerequisite — still unresolved

Confirm an existing license that permits this Windows guest, or review a purchase separately. Do not assume host activation grants a second installation; do not store license keys in this document or chat. Obtain the Windows x64 ISO from [Microsoft](https://www.microsoft.com/software-download/windows11), record edition/language/version and verify against Microsoft's published hash for that exact ISO. Do not run the host Installation Assistant or write installation media to a user's disk. Guest setup, activation or patching that needs network access requires a separately bounded maintenance session; task guests remain disconnected.

## Failure and rollback

If checks fail before installation, preserve the downloaded artifact and failure log without running it. If installation fails, preserve logs, leave VM-required tasks disabled and compare captured host state. Do not automatically uninstall drivers, reboot, reset networking or delete VM images. Present a scoped rollback for review. Document preservation and existing trusted-host workflow remain unchanged.

## Review decision needed

1. Approve or decline the bounded base-package installation above (system drivers, no automatic reboot or optional network drivers).
2. Confirm whether a suitable Windows guest license/media already exists; licensing status is unknown.

These decisions are required by the existing Phase 4 installation/host-change boundary, not by a new restriction on routine source edits. No VM controller implementation or VM acceptance case has passed yet.

Sources: [Oracle Windows installation documentation](https://docs.oracle.com/en/virtualization/virtualbox/7.2/user/installation.html), [Oracle security guide](https://docs.oracle.com/en/virtualization/virtualbox/7.2/user/Security.html), and the Microsoft media page above. Installer options must be confirmed against this exact package before execution; no guessed unattended command is supplied.
