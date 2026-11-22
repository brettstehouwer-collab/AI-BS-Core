# Chapter preview and isolated Play

Status: **VERIFIED source and installed native entry points**, revision0.20.
Actual evidence: `out/chapter_play_verification.json`. The full game/engine and
broader model tools/providers remain unfinished. Retained Studio94 is unchanged.

## Authoritative data

The C++ `ContentAuthoringHost` owns the currently visible chapter definition.
An export is a canonical immutable AIBD document, including its definition/world
identities, content revision and SHA-256 fingerprint. The creator can export
unsaved visible changes. Export neither applies a private prepared candidate nor
saves the authoring journal. Only Apply publishes an authoring preview.

The native typed owner advertises `chapter-content-export-v1`. Existing Describe
requests retain their metadata result. The optional Describe tail is a byte1,
uint32 offset, uint32 limit in1..256KiB, and expected fingerprint text. Full
project/branch/world/host-epoch and expected authoring head checks still apply.
The export response body carries uint16 version1, definition UUID text,
fingerprint text, uint64 content revision, uint32 total bytes, uint32 offset,
uint32 chunk bytes and raw data. Total is bounded by1MiB. The receiver checks
every chunk against the same loaded context and verifies the assembled hash.

## Read-only native preview

The independent viewport envelope uses AIBV version1, projection mode2, then
snapshot UUID/project/branch/world UUID/checkpoint text, uint64 authoring head,
selected UUID text, uint32 AIBD length and raw AIBD. It does not reconstruct
geometry from Python inspector rows. C++ decodes and validates the chapter,
constructs its gameplay baseline and uses the existing content-aware scene API.
Picking returns persistent UUIDs through the existing nonce-tagged READY/PICK
channel. Stale displays cannot select an object in a newer document snapshot.

## Native Play ownership

The Qt creator owns the native Play child and a per-launch scratch directory.
The selected immutable AIBD file and a separate temporary-play database live
there until the child exits. The Play process receives explicit paths and a
session UUID; it never guesses or opens a personal player database. No Save
operation is required before testing the visible authored state.

Play uses the same native collision, movement, interactions, hazards, rules,
Adam cues and asynchronous semantic saving as the chapter game. A content
binding prevents reopening scratch progress against a different definition.
Editor changes during Play stay in authoring; the child keeps its launch
snapshot. Its progress does not become editor history or change authored
defaults. There is no implicit apply-back operation.

Stop requests graceful child shutdown and waits for save completion and process
exit before releasing the scratch directory. Failed or forced shutdown must be
reported accurately. Parent close preserves Save/Discard/Cancel and joins all
owned children. An unexpected owner exit must not leave an untracked Play
process. Temporary Play is a testing session, not a durable personal campaign.

## Required evidence

- Real typed owner exports match canonical C++ bytes/fingerprint, reject wrong
  scope/head/fingerprint and respect chunk/read limits without changing saved
  authoring bytes.
- Native DX12 preview shows edited chapter geometry, returns the selected UUID
  from a real Win32 interaction, and has no DX12 validation errors.
- Native Play uses an authored change in actual render/collision/action logic;
  BS can walk, repair or build/connect the relay, open doors and receive Adam's
  contextual authored guidance. Scratch restart preserves genuine outcomes.
- Actual Qt tests cover launch from unsaved visible authoring, stale export,
  authoring edits during Play, explicit Stop and parent close, with joined child
  processes and unchanged authoring save bytes/head from runtime actions.
- Legacy numeric creator/preview and existing fixed-chapter routes retain their
  prior behavior. Installed Debug/Release entry points match tested sources.

Live local field generation is now connected through AI_AUTHORING.md. These native
tools consume validated authoring state and do not generate memoir facts or
claim that authored Adam lines are historical quotations.


Windows publication uses shared-delete native reads, ReplaceFileW for existing
snapshot targets, and a watcher that retains the prior valid scene through
transient read gaps and retries without advancing its stamp on failure.
