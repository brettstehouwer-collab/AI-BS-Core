# Windows executable rebuild — v5.329.78 / Record201

Updated 2026-10-31T13:46:27.048380+00:00. The Windows client was rebuilt from the current v5.329.78 native source, installed at `C:\AI-BS\native_studio\releases\v5.329.78\AI_BS_Studio\AI_BS_Studio.exe`, and the existing **AI-BS Executive Studio** desktop shortcut now points to that executable.

## Verified outcome

- Windows FileVersion and ProductVersion: **5.329.78**; bundled version authority: **v5.329.78**.
- Frozen graph: **66 native modules / 85 inputs**, all matched to the actual current source, including existing uncommitted native chat updates. The canonical historical builder remains unchanged.
- Installed package: **2,256 files / 560,871,517 bytes**, with exact file membership and SHA-256 readback checked. Executable SHA-256: `fd2621dce9bc7ce2284a964d8261d5bcdd2e394b858b1215d0b0def7548f8f3b`.
- Existing older candidate and legacy dist_bin remain intact. The previous partial installation was left untouched at `C:\AI-BS\native_studio\dist\AI_BS_Studio`; the original desktop shortcut is preserved. One initial identity check on that old partial directory failed before copying or promotion; follow-up diagnosis found no ongoing change, so the completed install uses a fresh versioned directory and makes no old-tree hash certification claim.
- The desktop and both main Start Menu aliases now point to the same verified versioned executable; original shortcuts are backed up. Seven other utility/Trainer/Broadcast/Matrix aliases are unchanged.
- **48 focused native tests + 8 staging-wrapper tests pass**. Ten inventory/promotion and five binary-packaging regression tests also pass. Additional inventory-promotion regression results are recorded separately. Version synchronization remains v5.329.78; no patch bump was introduced for this rebuild.
- The actual frozen executable passes its existing bounded `--check-local-connection` mode. It resolves the owned local service identity using this application's exact Windows Credential Manager profile, emits credential-free diagnostics into a fresh restricted E: test location, sends no HTTP requests, writes no credential profile and creates no MainWindow.

## Build contents and service boundaries

PyInstaller built a Windows onedir client with the reviewed native module graph, Qt Windows platform plugin, pywin32 credentials/security modules, explicit win32timezone, and the existing DearPyGui2.3.1 dependency for the separate HUD. The HUD dependency and license/distribution metadata were frozen from the installed project environment; no package was downloaded or installed for this dependency. Backend modules, operational databases, private environment files and key material are excluded by the packaging guards.

This is a **native client build**, using the existing controlled local services. Backend fixes remain in C:/AI-BS and the existing loopback backend; they are not copied into the executable as a second service stack. Live trading remains **disabled**, crypto port8007 remains absent, and payments/outreach/background holds remain active. Four protected execution/monetary files retain their original hashes. No order, payment or outreach dispatch was invoked.

The native version is v5.329.78. Hosted Firebase remains v5.329.77; this task did not publish a website. The included web provenance records the actual v77 context:1,127 local artifact hashes and the143compiled-file plus public-sample/version remote proof. It does not assert a complete1,127-file remote readback or feature parity.

## Limits and preserved history

The executable is **unsigned**. No eligible certificate was available under the existing signing policy, and no trust-store/signing-policy changes were made. Optional PyInstaller warnings are retained in the build evidence; full GUI, every tab, optional OpenGL/TBB behavior, provider workflows and end-to-end feature parity were not certified by the bounded frozen support check. The known Chroma vector corruption remains an open recovery issue; this rebuild does not claim to repair its data.

The prior whole-system verification remains partial (Record200:1,604 accepted cases,11held integration files); it was not relabeled as a new full-suite execution. Nine ledger prefixes and the previous checkpoint text are preserved byte-for-byte before appending this record. Source snapshots, build plans, dependency provenance, tests, output hashes, shortcut preimages and recovery receipts are retained in the established [single Google Drive folder](https://drive.google.com/drive/folders/1yglgqXtK12MWL-6_9FaQ_I9OI44bhB2k). Cloud round-trip results are recorded separately after upload rather than presumed by this report.

ADR-125: rebuild and install an exact frozen native snapshot while preserving old artifacts; keep service ownership/dispatch holds unchanged; distinguish version/build/support validation from full GUI acceptance and publisher signing.
