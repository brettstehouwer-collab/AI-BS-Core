# Publishing website live release — November 14, 2026

User explicitly authorized live publication after local review. Public URL:
https://stehouwer-publishing.com/ . The website source and built output are now
promoted; earlier LOCAL_REVIEW_ONLY receipts remain dated historical evidence.

Rollback checkpoint: `backups/publishing_live_20261114T201454Z`.
Previous complete live output is retained at
`C:/StehouwerPublishing.com/website-rebuild/dist-before-20261114T201454Z`.
Exact preimages of changed original source and Nginx configuration, the applied
website patch and before/reviewed manifests are retained in the checkpoint.
All 37 reviewed output files match their local manifest; 17 existing extra files
are preserved unchanged, including public verification/feed/legacy resources.

Build, 24 Node tests, and 14 browser/HTTP smoke groups passed before publication.
Independent shipping-source inspection parsed 21 JS/JSX/MJS modules with no
undeclared imports or credential-pattern matches. Nginx configuration tests and
reloads passed. Initial relocated-config test required its unchanged mime.types
include alongside it; failed evidence is retained separately at
`backups/publishing_live_20261114T201441Z`.

Public verification passes 37/37 release-file checks plus 15/15 route, canonical,
sitemap, robots, legacy redirect, missing-file and API-method checks. Non-HTML
assets match exact SHA-256; HTML receives the existing Cloudflare beacon, and
robots preserves Cloudflare's managed prefix plus the exact clean origin body.
Public HTML metadata and live browser rendering were separately observed.

A necessary final Nginx correction serves route index files without an HTTP
trailing-slash redirect and makes legacy redirects relative, preserving HTTPS
behind the existing tunnel. Final configuration diff is in the checkpoint.
Cloudflare's existing account was accessed through its normal Google sign-in.
Custom purge covered 30 explicit release/stale URLs on bare and www hosts.
No zone-wide purge, security weakening, crawler-preference change or account
permission expansion. Earlier public cached robots/header-case verification
failures remain retained; corrected checks pass. Live proof: `live-home.png`.

Only website source/static output, its public collector and Nginx routing were
activated. Statistics aggregation/dashboard candidates remain staged, with
their 18 synthetic assertions retained. No running backend/dashboard replacement,
private-record change, inference, payment, broadcast activation or unrelated
business workflow. API-method checking does not prove an end-to-end visitor
record was ingested; the ordinary browser visit was not a synthetic event seed.

Next separate work: review/activate the coordinated statistics backend/dashboard
patches with their own service qualification; confirm sample PDFs, exact package
inclusions/surcharge basis, AI pass terms and input/copy telemetry disclosure.
