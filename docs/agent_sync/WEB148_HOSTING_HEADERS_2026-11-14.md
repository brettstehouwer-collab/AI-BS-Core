# Web148 Hosting headers — local HTTP gate passed

The exact combined web148 output now passes all12 assertions through the
unmodified Firebase CLI15.36.0 Windows demo Hosting emulator. Evidence is
`backups/web148_combined_20261114_v01/hosting-attempt-04/smoke-results.json`.
Both service workers receive no-store and their correct scope; manifest JSON
revalidates; all served manifest assets match the frozen compiled hashes.
The browser checks use fresh disposable profiles, external requests blocked,
actual compiled workers and phone-sized offline rendering. Real account sign-in,
restored offline identity and private-record workflows are not qualified by this.

The source fix replaces the six custom-header glob selectors with equivalent
RE2-compatible regex selectors. The emulator's Windows glob normalization had
changed URL separators to backslashes, defeating minimatch. Regex selectors
handle native URL slashes and that Windows normalization directly, using the
supported Firebase header configuration surface. No emulator dependency was
patched, loaded through a shim or replaced. Generic cache values and security
headers are preserved; worker exceptions still follow the generic JS rule.
Rewrites, Hosting ignore rules, production site and public directory are unchanged.
Firebase documents the [header source/regex configuration](https://firebase.google.com/docs/hosting/full-config#headers).

The actual installed matcher proves equivalent header values on1162 emitted and
representative URLs, for both POSIX and Windows paths (2324 assertions in one
configuration-contract group). This includes nonmatching extensions and exact
worker paths. The frozen compiled artifact manifest still matches1154 files and
922265128bytes. One cleanup group confirms all four owned emulator ports closed.
These three groups supplement the12-check smoke profile; prior failed attempts
remain retained. Remote CDN headers and whole-production acceptance remain open.

The new checkpoint and reviewed config overlay are under
`backups/web148_hosting_headers_20261114_v01`. The earlier combined build/output,
failed checkpoints and original32member Drive archive remain unchanged. This
follow-up is configuration-only, with no new app-code or native-package change;
148 is still an unpublished combined web candidate. No services, feature flags,
canonical dist, default launchers, original saves or private stores were changed.

Next: qualify backend/owner activation and fresh-device identity behavior, then
the final release gate and separately authorized preview/production deployment.
The remaining ten-goal/six-addition workstreams remain ACTIVE and incomplete.
The scoped follow-up archive preserves changed configuration and verification
evidence; it excludes the entire compiled site, media library and private data.
