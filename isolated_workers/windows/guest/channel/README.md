# Provisional guest status channel

Prepare-GuestChannelIdentity.ps1 runs only in a VirtualBox guest with a
non-elevated token. It creates a dedicated non-exportable ECDSA client certificate
in CurrentUser/My and exports public certificate data only. A non-elevated token
does not prove a nonadministrator account. No credential from the Codex login is
read or copied.

GuestStatusClient.cs uses the existing Windows CNG private key through Schannel,
pins the host certificate SHA-256 per connection and validates the host-controlled
worker/owner/base/channel epoch and response nonce. It provides only status,
gateway health and Ollama version requests. The server requires the exact approved
client certificate and keeps all execution/apply/worker admission flags false.

The guest public JSON can be relayed through this chat. Private keys must remain
in the guest store. The private key's non-exportability does not stop another
program running as the same guest user from using that identity; the separate
disposable execution environment must not inherit this credential or Codex login.
Certificate possession does not prove VM/hypervisor identity or containment.

A reviewed public bootstrap downloads only the fixed source bundle through mTLS,
checks the archive and source hashes, and compiles the client. It does not install
global trust or change execution policy. Signed-message/provisional mTLS status
acceptance is separate from code execution, artifact publication and the fourteen
containment cases. The guest message is authenticated by mTLS, not HMAC-signed.
