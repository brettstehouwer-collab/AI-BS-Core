# Nginx and Cloudflare recovery — November 11, 2026

User-authorized server repair; the broader ten-goal program remains paused.

## Restored and checked

- Recovered the existing Nginx 1.31.3 package from Windows.old into its original launcher path: `C:\Users\footb\AppData\Local\Microsoft\WinGet\Packages\nginxinc.nginx_Microsoft.Winget.Source_8wekyb3d8bbwe\nginx-1.31.3\nginx.exe`. No download or old-package deletion.
- Preserved original publishing configuration at `backups/nginx_restore_20261111_v01/publishing-nginx.before.conf`.
- Primary configuration: `C:\StehouwerPublishing.com\nginx.conf`; website root: `C:\StehouwerPublishing.com\website-rebuild\dist`.
- Recovered Chef virtual host from the package configuration into `C:\StehouwerPublishing.com\conf.d\thesimplechef.conf`. Missing old root `E:\thesimplechef\public` replaced by surviving built site `G:\simplecheff\dist`. Original package config and Chef source are unchanged.
- Added one include, hostname hash bucket 64 and explicit publishing default-server selection. The first 32-byte hash-bucket validation failure is retained in the existing error log; no invalid configuration was reloaded.
- `nginx -t` passed before successful reload. Publishing remains bound only to loopback, with the existing Cloudflare tunnel providing public HTTPS.
- Added `runtime/devtools/Start-Publishing-Nginx.cmd` and scheduled task `AI-BS-Publishing-Nginx` at the current administrator's sign-in. The startup helper checks for the owned Nginx process and validates before starting. Actual task execution returned 0 without a duplicate instance. Reboot/logon execution itself is untested.
- Existing tunnel configuration: `C:\Users\footb\.cloudflared\config.yml`; credential file remained in place and was not printed or copied into evidence. Existing ingress validation passed.
- Initial public request returned HTTP530 / Cloudflare1033. An assistant command containing tunnel startup was rejected by automatic approval review with only `blocked by policy`, so it was not retried. Following the user's terminal action, cloudflared PID42832 was observed using the expected config and tunnel, and public publishing HTTPS returned200.
- Read-only HTTP verifier completed20 checks, all HTTP200: publishing aliases locally, Chef hosts locally, public publishing root/assets, local Chef assets, direct8000/8080 health and publishing `/api/health`. Sixteen file comparisons were exact. Public HTML differs from source bytes; a separate normalized-text comparison found only one Cloudflare beacon insertion. This is not a byte-identical public HTML claim.

## Existing routing retained

| Use | Origin / state |
|---|---|
| Publishing aliases, including stehouwer-publishing.com | Local80 → preserved built site; requested public publishing HTTPS checked200. Other aliases checked locally only. |
| stehouwerproductions.com and www | Existing Nginx alias retained; local200. No new DNS/tunnel ingress added. |
| General `/api/` | Existing127.0.0.1:8000 upstream; direct and proxied health200. |
| RecDebut `/api/v1/recdebut/` and `/r/` | Existing8080 forwarding retained. No messages, tracking links, campaign actions or dispatch tests invoked. |
| Chef hosts | Recovered local static site200; existing `/api/v1/chef/`→8080 retained. No public Chef routing added. |
| `/hls/` | Existing8089 forwarding retained, but origin connection refused. No streaming service activated. |
| api.brettstehouwer.live / ai-bs.brettstehouwer.live | Existing shared tunnel ingress retained; not independently qualified publicly in this repair. |
| Alternate WSL Chef8055 | WSL inventory returns Class not registered / REGDB_E_CLASSNOTREG. No operational or recovery claim. |

## AI-BS control-center relationship

`native_studio/engine.py` already lists Nginx80 in its port matrix; `backend/routers/system_router.py` includes Nginx in system topology. Their presence is source evidence, not an observed control-center GUI status refresh. Restoring Nginx does not establish that every monitored subsystem or cloud integration works. Current actual HTTP probes are stronger evidence for the named routes than failed/empty host networking inventory commands.

The tunnel is presently running from the user's launch. This repair added Nginx sign-in persistence only; it did not install Cloudflare tunnel persistence. Closing that tunnel process can take the public sites offline again. The old `scripts/register_cloudflare_persistence.ps1` points to a missing Program Files installation and is not a verified current startup mechanism.

## Evidence and limits

Local evidence: `backups/nginx_restore_20261111_v01/local-host-checks.json`, `http-verification.json` (initial raw HTML difference retained), `http-verification-v02.json`, and `http-verification-v03.json` (final scoped checks). Original website assets/config preimage and Windows.old remain preserved. Public HTML capture is local only. No new Drive checkpoint was created by this repair.

No firewall/Access/DNS/TLS policy was relaxed, no source build was run, and no AI/business/trading/campaign activation was requested. Nginx restoration and website availability are qualified separately from WSL, live streaming, public alias coverage, tunnel reboot persistence and complete control-center monitoring.
