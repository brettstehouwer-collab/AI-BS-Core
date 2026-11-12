# SDK0.16.6 qualification

SDK0.16.6 packages the reader2 application presentation in a new immutable version. There is no public C++API, asset schema or AIBD/save-format change; the declared capability set matches0.16.5. Existing0.16.4/0.16.5prefixes and Studio103/104files were rehashed exactly.

Both Release and Debug independently passed all127registered engine tests, with exact JUnit names, no skips/failures/errors and fresh evidence roots. Each new installed prefix contains449files. Each configuration also passed8independent consumer tests using only the installed public headers/libraries, including actual native GPU/guide and render-validation checks. Consumer project files were checked for accidental source/build-tree include paths.

Evidence: D:/AI-BS-Game-Resources/P55/SDK0166Qualification/sdk-verification.json and verification.json. Source builds and tests use short temporary roots and new native-render output folders, preserving earlier diagnostics. All owned child Jobs joined.

Release: D:/AI-BS-Game-Resources/SDK/0.16.6/release
Debug: D:/AI-BS-Game-Resources/SDK/0.16.6/debug

This qualifies the SDK and reader2runtime, not the finished game. Studio104is still deployed. A separate25file v18curated bundle has been prepared and admitted by the0.16.6factory for the next preview; the old v10bundle remains unchanged. Studio packaging, final personal likeness/caption review, actual user gameplay performance and8–12minute first-time pacing remain incomplete. Original family media and user saves were not used by qualification.

The source checkpoint includes the engine code and current curated/reference assets. Jolt/SQLite remain external dependencies retrieved through their existing pinned CMake recipes; this is not a bundled compiler/Windows SDK or a claim of offline dependency availability.
