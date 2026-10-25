# Read-only existing API tunnel audit

Audit observations: 2026-10-24T21:19:14Z through 21:24:05Z. No service, process, registry, DNS, remote configuration, original config, application source, VM, listener or activation-flag changes were made. New evidence files were written only in this private checkpoint.

## Verified cause

- Public API health returned HTTP530, Cloudflare subcode1033.
- Cloudflare's existing exact DNS record `6a929167aa8efa6d6896f9aff7280577` is a proxied CNAME from `api.brettstehouwer.live` to `d1acbd25-06c3-4be0-a7f4-ae3943263aed.cfargotunnel.com`, last modified July22.
- Existing tunnel `d1acbd25-06c3-4be0-a7f4-ae3943263aed` (`ai-bs`) has zero connections and is not deleted.
- Existing Windows service `Cloudflared` is running as LocalSystem, PID42424, created2026-10-22T07:41:30.387666Z. It uses a token file for a different existing tunnel, `7cd0399e-bc71-45ef-851c-0d8261ca03ec` (`aibs`). Its ready endpoint returns200 and metrics report4HA connections, zero HTTP requests. Remote configuration is null/version0. Restarting this healthy service does not repair the DNS target mismatch.
- Installed binary is cloudflared2026.10.0. Service metrics bind127.0.0.1:20242.

## Existing local configuration and credentials

Original `C:\Users\footb\.cloudflared\config.yml` SHA256 remained `305CD3471BD06BAC31B7614DEFC0B851EBB5F40CC16AF9B8077FA87241D39A68` across this audit.

Its API routes are, in order:

1. API hostname, path `/sse` -> `http://127.0.0.1:8099`.
2. API hostname, path `/messages` -> `http://127.0.0.1:8099`.
3. API hostname, all other paths -> `http://127.0.0.1:8000`.

Other unrelated hostname rules exist in the original, followed by default404. There is no8099listener. Do not launch the original broad config for this web-only restoration.

The referenced credential file exists, is a regular non-reparse file, has the correct d1TunnelID, an account matching the existing origin cert, and a present32byte base64-decoded tunnel secret. No credential contents were printed or copied. This is structural validation, not cryptographic validation; actual credential validity remains UNVERIFIED until a connector authenticates.

The repository `.env` API token could list no exact target zone and returned401/code1001 for the running tunnel's config. The pre-existing cloudflared origin cert successfully read the exact DNS record and remote config. No login, token generation, rotation or permission changes occurred.

## Preferred concrete restoration

Root may create a separate private reviewed config for existing d1tunnel, referencing its existing credential file in place, containing only `api.brettstehouwer.live` -> `http://127.0.0.1:8000`, then a final `http_status:404` catch-all. No DNS or cloud configuration changes are required. For the two currently unavailable8099routes, explicit404rules before the general API rule preserve their closed status instead of accidentally routing them to Go8000. Whether to preserve those two path exceptions is a concrete root review decision; they are absent from the simple API-only proposal.

Use a separate hidden process, not the installed Windows service. A candidate launch form, after local validation, is:

`cloudflared.exe tunnel --config <private-candidate.yml> --no-autoupdate --metrics 127.0.0.1:20243 run d1acbd25-06c3-4be0-a7f4-ae3943263aed`

Port20243 was free at21:24:05Z; recheck immediately before launch. Original config/credential/Windows service/DNS remain unchanged. Keep stdout/stderr/info logs private. Do not use debug logs or place credential values on the command line.

Validate the candidate without launching using installedCLI `tunnel --config <candidate> ingress validate` and `tunnel --config <candidate> ingress rule <URL>`. Test exact API URLs and an unrelated hostname selecting404. Check global process identity/config args before starting so there is no duplicate d1connector using broader rules. Freshly confirm d1still has zero remote connections.

## Preconditions and acceptance

- Read-only local probes with Origin `https://ai-bs-dashboard.web.app` at21:24:05Z returned health200JSON and anonymous `/api/chat/coding-tasks`401; both echo the exact allowed origin.
- Required8000/8080/5173/11434listeners remain127.0.0.1, PIDs25576/80276/111704/148912. This audit did not read/change the six activation flags; use root's existing validated flag evidence and recheck before publication.
- Before launch, freeze candidate/config hashes, exact source config and DNS metadata, and confirm required current authentication rejects obsolete credentials and anonymous protected routes. A healthy tunnel is connectivity evidence only.
- After launch, require localready200/4HA connections and publichealth200JSON, anonymous protected401/403, obsolete exposed-key rejection, expected Firebase CORS, and an existing legitimate authenticated read-only flow if available. No write/action/model/VM endpoint execution is needed for connectivity acceptance.
- If auth or scope verification fails, stop only this new process after revalidating its PID/creation/exe/config identity. This returns the API to its prior unavailable state. Leave PID42424/service/DNS/original config/credentials untouched. No broad hostname rollback is required because no broad hostname mapping was introduced.

## Evidence and limits

`tunnel_list_summary.json`, `tunnel_routes_summary.json`, `tunnel_routes_cert_summary.json`, associated raw responses and trusted read-only helpers are retained in this ACL-private checkpoint. Raw account responses are local-only. One PowerShell summary command had a parse error before executing; it was corrected once. One official raw-source URL404 and one documentation capability fetch error were not tunnel failures.

Primary documentation checked:

- https://developers.cloudflare.com/tunnel/troubleshooting/ —1033 means no healthy connector is found for the requested tunnel.
- https://developers.cloudflare.com/tunnel/features/locally-managed-tunnels/configuration-file/ — ordered ingress, final catch-all, validate and rule commands.
- https://developers.cloudflare.com/tunnel/reference/run-parameters/ — custom config, metrics and no-autoupdate options.
- https://developers.cloudflare.com/api/resources/dns/subresources/records/methods/list/
- https://developers.cloudflare.com/api/resources/zero_trust/subresources/tunnels/subresources/cloudflared/subresources/configurations/methods/get/

This proposal has NOT been launched or applied. Existing credential authentication and public app authentication remain to be proved by root's actual acceptance checks.
