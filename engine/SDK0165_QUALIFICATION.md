# SDK0.16.5 qualification

SDK0.16.5 is a development candidate for gameplay measurement. Studio103 and the existing launchers continue to use SDK0.16.4. A separately installed prefix under `D:/AI-BS-Game-Resources/SDK/0.16.5/` does not deploy a new Studio release.

The gameplay measurement API adds fields to `FrameMeasurementConfig` and `FrameMeasurementSummary` and adds `finish_gameplay()`. Existing source aggregate initialization retains the stationary default. Rebuild consumers using matching headers and libraries from one SDK prefix; binary mixing between SDK versions is not supported. No AIBD document, gameplay save schema, personal history or family-reference format is changed.

The existing SDK consumer example includes a gameplay ABI/compatibility executable when `find_package` reports SDK0.16.5 or newer. Its synthetic clock fixture verifies linking and data layout, not real hardware FPS. Independent qualification also exercises the prior consumer and hidden guide/renderer validation paths using only the installed SDK.

P46 evidence lives under `D:/AI-BS-Game-Resources/P46/SDK0165Qualification`. Compilation, algorithm/process/HWND contracts, native graphics regressions, installed-consumer checks, user-started gameplay sampling and final Studio acceptance are distinct scopes. Read the verification receipts for actual completed sets; a configured target or installed prefix alone is not acceptance. Automated Play/Creator tests use their own transient windows and isolated saves; they do not start the user's manual review.

The public consumer now requests SDK0.16.4 or a compatible newer0.16 patch. Its former0.14 request was rejected by the SDK's same-minor version policy. The initial failed0.16.4 configure is retained; the corrected example must be verified against both retained0.16.4 and new0.16.5 prefixes. No installed old SDK file is changed to make this pass.

The prepared manual-review launcher remains on the stable Studio103 resources. Do not substitute a new sampler result for first-time8–12minute pacing or the creator's assessment of Adam's likeness and guidance.
