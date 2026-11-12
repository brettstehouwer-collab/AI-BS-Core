# Staged memory playback session

This reusable controller is staged separately and has not been integrated into
the canonical game, editor, SDK or release. It wraps the frozen AudioPlayback
module without editing it. It neither grants quest credit nor writes save
history, synthesizes speech, clones voices or starts playback on bind.

## Short API

```cpp
aibs::MemoryPlaybackSession memory; // same owner thread for its whole lifetime
memory.set_volume(0.7f);
memory.bind(station_uuid, shared_audio_asset, other_resident_bytes);
memory.play_or_resume(other_resident_bytes); // explicit user action
memory.set_game_paused(true, other_resident_bytes);
memory.set_game_paused(false, other_resident_bytes);
memory.pause(); // manual pause cancels remembered game-resume intent
memory.stop();  // manual Stop clears game-resume intent and the caption clock
const auto now = memory.snapshot();
if (now.caption_index) {
    const auto& caption = now.asset->captions[*now.caption_index];
    // The snapshot owns the AudioAsset keeping this caption alive.
}
memory.close();
```

The bound station must be a canonical lowercase version4 UUID. The asset must be
a fully validated immutable `shared_ptr<const AudioAsset>`; callers must not
mutate an aliased original after binding. The session retains the shared owner,
not a borrowed PCM or caption view. A returned snapshot retains that owner and
an optional numeric caption index, so it stays usable after rebind or close.
The station UUID is copied into a fixed array in the snapshot. Copy/move of the
controller is disabled. Like AudioPlayback, construction can fail allocation;
subsequent methods return bounded enum/audio-error values and are `noexcept`.
Wrong-thread operations cannot change the owner state.

Bind validates the entire candidate and its residency first. It then stops the
old playback and replaces the binding; validation/budget rejection preserves
the previous binding and playback. Successful binding never plays and clears
game-resume intent. Game Pause automatically pauses only a playing recording.
Unpause resumes only that remembered recording; manual Pause/Stop, rebind or
close cancel the intent. An over-budget or failed resume retains paused intent
for a later explicit retry. Explicit Play while the game is paused is refused.
Completed recordings replay only through a new explicit Play action.

## Caption behavior

The separate pure `memory_caption_index` function performs start-inclusive,
end-exclusive lookup using source frames. Gaps and frames at/beyond the original
recording length return no caption. It requires the same validated immutable
asset that binding accepts. The snapshot selects captions only in playing or
paused state; stopped, completed, failed and closed states hide them. Paused
playback holds the same source frame/cue.

Draft captions are withheld by default and `review_pending` remains true.
Passing `allow_draft_preview=true` explicitly to bind permits their display for
authoring preview while still reporting pending review. This flag does not mark
captions checked, and a `checked` declaration is not proof of human listening or
linguistic accuracy. Actual original-recording caption review is separate work.

The earlier AudioPlayback proof established a source sample clock. This module's
tests additionally establish caption interval selection from that clock; these
are distinct acceptance claims.

##128MiB admission contract

The caller supplies up-to-date `other_chapter_residency_bytes` on bind and every
operation that might start/resume playback. During **bind**, that value excludes
both the current and candidate AudioAssets and this session's PCM copy. The
controller adds old/new decoded source costs and the old PCM copy itself,
deduplicating the same shared AudioAsset object. Distinct aliased AudioAsset
objects are not collapsed just because their control block is shared.

During **Play/Resume/game pause changes**, other residency excludes the selected
AudioAsset and session PCM only. The controller adds the full source decoded
cost (metadata, PCM capacity and caption capacities) plus current owned PCM.
Starting a new stream additionally reserves the frozen AudioPlayback module's
48MiB maximum new PCM capacity before any device creation or old-state change.
Resume has no new-copy reserve. This conservative reserve deliberately avoids
assuming a standard-library vector's capacity equals its requested size.

All sums use checked subtraction against128MiB. Overflow and over-budget inputs
reject before device operations. Bind never creates a candidate playback copy;
its transient charge is old/new sources plus existing PCM. Current
`resident_bytes` reports source + actual session PCM capacity + the accepted
other residency. `reserved_peak_bytes` reports the greatest admitted transient
or conservative Play reserve. It is not a process RSS measurement. Opaque
XAudio2 internal allocations and the controller's small fixed objects remain
outside this content-residency accounting and must be measured separately.
If callers retain old snapshots/assets elsewhere, they must include those
other resident objects in subsequent caller accounting as applicable.

## Files and verification

Public: `include/aibs/memory_playback.hpp`. Implementation:
`src/memory_playback.cpp`. The private deterministic test injection seam is
`src/memory_detail.hpp` and is not a public SDK header. Canonical integration
should add a MemoryPlayback target with a public AudioPlayback dependency.
The staging CMake imports frozen sibling Release libraries read-only instead of
rebuilding them or writing canonical files.

Actual missing-header RED is preserved in `missing-api-red.log`. Strict MSVC
Release `/W4 /WX /permissive-` passes the API, pure controller/lookup and actual
muted XAudio2 device tests. Pure cases cover exact cue boundaries and gaps,
draft policy, retained snapshot ownership, game/manual pause interaction,
Stop/rebind intent clearing, failed controls, foreign-thread rejection, exact
128MiB admission, overflow and distinct/same-owner replacement accounting.

The device test uses only all-zero synthetic44.1kHz stereo PCM at source volume0.
It verifies caption indices/text against actual source sample progression,
caption/clock hold during game Pause, resume, manual Pause/Stop, no replay after
Stop or rebind, draft withholding/explicit preview, completion and cleanup.
Test processes have finite external deadlines and CTest timeouts. No original
family speech was loaded or played. No audible intelligibility, original caption
accuracy, gameplay UI, save-system or packaged-release claim follows from this.

Only the existing small `out-release` directory was used; no Debug or new bulk
build directory was created after the parent's disk-space hold. Final exact
source/frozen-input hashes, test counts and device measurements are in
`verification.json`. Debug and canonical integration remain unverified for this
new controller. There are no active test/build processes at handoff.
