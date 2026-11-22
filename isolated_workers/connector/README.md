# Private TLS control channel

Port18443 is the selected private host connector. It binds only127.0.0.1.
VM clients initiate connections using the VirtualBox host alias once the guest
profile/certificate/key enrollment is actually admitted. There is no guest inbound
listener, public forwarding or raw Codex app-server endpoint. Codex integration
is planned via a separate host-local stdio process; no Codex agent is launched here.

The current channel exposes authenticated status, fixed gateway8000 /health,
and fixed Ollama11434 /api/version only. It revalidates pinned owned upstream
listener/PID/creation/executable identities. It forwards no developer credential,
user-supplied URL, code, model-generation request or filesystem command. Returned
status explicitly keeps worker admission/execution/apply false. File delivery and
the complete BS-Chat/IDE/VM coding loop remain future integration.

HMAC envelopes/replies are scoped and replay-protected in a fresh dedicated disk
SQLite store. Persistence requires a durable journal and FULL/EXTRA synchronous
mode. HTTPServer serializes that store's connection; do not replace it with a
threaded server sharing this connection. The launch is capped at256POST requests
and at most30minutes; the reviewed demonstration uses15minutes. Each TLS
connection has an absolute three-second timer. The upstream probe receives the
remaining request budget, has its own absolute timer and is interrupted by global
expiry. Startup readiness is fsynced then atomically renamed into place.

The host controller checks four reviewed Python source pins and holds read locks
through provisioning/import/startup. It creates a new private leaf with protected
ACLs for the current user/System/Administrators only, and fresh short-lived
certificate/message keys. It never reads or copies an OpenAI login, installs
certificate trust globally, changes existing ACLs, enables a firewall rule, mutates
VM networking, or registers a service/task. Expired/failed launch roots and replay
evidence are retained. Never reuse a failed root or bypass source drift.

    powershell.exe -NoProfile -File C:\AI-BS\isolated_workers\windows\control\Start-PrivateConnector.ps1 -LifetimeSeconds 900

A fresh launch requires a free port. Source pins intentionally refuse changes;
review and update them with the engineering checkpoint rather than bypassing them.
The private certificate and message key must be enrolled through an authenticated
worker process before guest use; current host tests do not establish that gate.
Guest TCP checks alone do not prove TLS/HMAC, private-store access controls or
containment. SSH is a separate protocol and is not configured by this connector.

Tests cover actual localhost TLS and disposable persistence, with an additional
controlled process-expiry drill retained in Record113. Actual guest TLS, safe
multi-file delivery/receipts/recovery and fourteen execution containment cases
remain unaccepted.
