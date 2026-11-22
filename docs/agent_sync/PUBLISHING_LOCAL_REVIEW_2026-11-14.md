# Publishing website: local review only

User authorized technical repairs, layout/clarity improvements, and verification
of the existing `http://localhost:5173/?tab=beta` statistics dashboard. Publication
is explicitly held for review.

Review source: `C:/AI-BS/work/publishing-review-20261114`. Baseline preserved in
its separate local Git repository; 33 original-source comparisons pass after
normalizing Git line endings. This does not assert byte equality across Git
newline normalization. Original website source/dist, running Nginx, tunnel,
backend/dashboard and telemetry records remain unchanged.

Local preview: `http://127.0.0.1:4178/`. Build passes; 14 HTTP/browser smoke groups
cover eight pages at 1440/390/320 widths, metadata, assets, 404s and old URL
redirects. 24 Node tests pass including 18 collector assertions and unchanged
live-signal/navigation suites. Statistics candidate passes 18 synthetic SQLite
assertions. Dashboard patch parses as JSX. All four configuration/statistics
patches pass `git apply --check`; none is applied to active services.

Existing authenticated dashboard refresh was observed. Its current pageview
total incorrectly counts all events. Separate backend/dashboard candidates count
pageviews, identify browser sessions honestly, reduce cumulative observations
per site/session/page, and display unavailable measurements without fabricated
fallbacks. Public collector adds client-navigation views and queue fallback.
Live statistics corrections await later reviewed application/restart; no test
events were seeded into production. Historical records remain intact.

Website fixes include route metadata, real contact/sample-request paths,
responsive layout, accessible navigation, clear indicative service pricing and
email-draft actions. Approved PDF samples, package inclusions/surcharge basis,
AI terms and input/copy telemetry disclosure remain owner review items.
Nginx routing and coordinated backend/dashboard activation are held. No Drive
upload or publication. Local failed evidence and final receipts are retained
under `review-evidence` and `review-artifacts`; authoritative review notes are
`work/publishing-review-20261114/REVIEW.md`.

Next step: owner reviews the local site and focused diffs, confirms outstanding
content/terms, then separately authorizes publishing and coordinated statistics
activation. Unrelated ACTIVE AI-BS program state is not advanced by this task.
