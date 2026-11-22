# Gateway149 configured backend routing

Source is now5.329.149. The gateway constructor accepted a Python port, but both
HTTP proxy handlers ignored it and hard-coded8080. Generic `/api/`/`/v1/` and
Comfy media forwarding now use the existing IPC bridge's configured loopback
port. Invalid/missing ports fail500 before forwarding, with no silent fallback.
The normal constructor's8080 behavior remains unchanged. No IPC transport,
authentication, supervisor, Win32 process primitive or running service was changed.

The production route table is exposed through `Gateway.Handler()` and used by
`Serve()` itself. The verification fixture uses this exact table, not its own
catch-all reverse proxy. No route registration, middleware ordering or daemon
startup policy was changed by that extraction.

Three focused Go regression groups pass: configured targets receive portal,
`/v1/` and Comfy requests with original credentials/query/private headers;
invalid/missing ports fail closed; and the default target/direct health route
remain separate. Twelve signed HTTP composition groups also pass using the
actual production table, SDK RSA verification against a synthetic certificate
transport/root, and disposable databases. This15-group profile covers owner
isolation, original-byte downloads, retries and fresh API/gateway process reopen.
The four owned child processes exit0. Earlier v01/v02 fixtures and failed
response-envelope evidence remain retained; no passing tests were rewritten.

Evidence: `backups/portal_owner_composition_20261114_v03/result.json` and
`backups/gateway_routing_20261114_v01/checkpoint.json`. A fresh executable is
compiled with `main.buildVersion=5.329.149`; its version-only invocation prints
`AI-BS Engine 5.329.149` without opening listeners or managing daemons. The
candidate is retained under the backup directory, not installed or started.

This proves the selected portal paths use the production route table in a
controlled runtime. It does not qualify every gateway route, full monolithic
backend startup, real Firebase identity, phone/browser private-record workflows,
or production deployment. Live gateway/backend, feature flags and private data
remain unchanged. Source149, native148 candidate, combined web148 candidate and
hosted146 are distinct. The16-file version change has its original preimages in
`backups/release_versioning/20261114T194325284Z_gateway149-backend-port_79e91f22`.

Next: actual-owner/device identity and reviewed activation/release gates; retain
the original game/creative and other ten-goal/six-addition requirements. Scoped
source/handoff and clean gateway runtime archives use separate manifests and
receipts. They exclude private databases, environment, signing material and the
rest of the project/runtime dependencies. No whole-ecosystem restore is claimed.

Drive source34members/249462bytes and clean gateway3members/6201213bytes were
downloaded and every archive member/hash/CRC verified. Receipts are in the
checkpoint's `source-backup` and `runtime-backup` directories. The original parent
and sharing were preserved. Closing continuity pointers postdate those archives.
