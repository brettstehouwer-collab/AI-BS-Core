# Temporary articulated guide presentation

`make_guide_placeholder()` provides a small indexed character resource for the
native companion renderer: a1.8m standing human figure, feet at localY=0,
18parent-before-child joints, inverse binds and four uniformly baked clips.
Separate shirt, trousers, skin and shoe color regions help make motion readable.
It is explicitly a temporary figure. It uses no family photographs, recording or
likeness data and does not represent the completed Adam character.

The four clip indices are stable for this presenter:

| Index | Name | Motion |
| --- | --- | --- |
|0|`idle`|Small breathing, chest/head motion and resting arms|
|1|`walk`|Opposing arm/leg swings and flexing knees|
|2|`catchup`|Faster, larger articulated swings|
|3|`guidance`|A restrained one-hand invitation, without touching machinery|

All clips keep root translation exactly at bind translation. Navigation owns
world movement. They are authored poses sampled through the existing
`CharacterScene` skeleton contract, not rebuilt static geometry. This blockout
has rigid limb regions; it is not a finished deformation/foot-placement rig.

`GuidePresentation` borrows an immutable mesh which must outlive it. Construction
validates the complete resource and exact four-clip contract. An rvalue mesh is
rejected at compile time to avoid immediately dangling resource ownership. The
presenter contains fixed-size pose state and does not copy geometry or clips.

```cpp
const auto figure = aibs::make_guide_placeholder();
aibs::GuidePresentation presentation(figure);
const auto state = companion.state();
const auto instance = presentation.sample(
    state.guide, elapsed, paused, state.recall_required, guidance_requested);
// If instance has a value, pass it to the dedicated indexed character draw.
// A missing instance is not a character at the origin.
```

The instance follows actual guide feet. The guide controller has no yaw field;
visual yaw derives from actual horizontal velocity and is retained on stopping.
Only initial adoption can use the destination to face a stationary figure.
Following above0.12m/s selects locomotion, with catch-up above9m/s for the current
native7m/s walk and13m/s catch-up controller. Waiting, near-player and blocked
states idle unless an explicit guidance presentation is requested. These clip
thresholds do not alter movement speed or controller state.

Missing, Recall-required, ungrounded, nonfinite, out-of-bounds or unknown-enum
guide states hide the figure. Pausing freezes the previous visible instance;
invalid/missing states still hide while paused. Negative/nonfinite elapsed time
throws before modifying presenter state. Each active call advances at most
four60Hz ticks of animation time, discarding excess display-time backlog. Loops
wrap within their duration and the nonlooped guidance gesture clamps at its end.

The steady cyan tint, positive emission and0.78opacity identify the temporary
luminous silhouette. They do not create a point light, cast shadows or imply any
completed hologram/GPU behavior; those are renderer responsibilities. The
presenter cannot repair, open doors, publish progression or write gameplay
history. Clocks, facing and sampled bones remain ephemeral and reset on restart.

## Verification

The isolated MSVC fixture is in
`D:/AI-BS-Game-Resources/workshop/guide-presentation-test`. Its initial build
failed for the missing presenter header before implementation. Release and Debug
each pass2,956 checks covering rest-height/origin, inverse-bind identity, real
skinned displacement in all four clips, asymmetric walking, in-place roots,
actual-feet/yaw transforms, clip selection, pause, hide/Recall, malformed input
and bounded clocks. A1,000frame loop intercepts ordinary and aligned global
allocation and verifies zero allocations plus unchanged geometry/sample pointers.
Source and diagnostics are retained; no family originals were changed.

These CPU checks prove the presenter and authored blockout. Visible native
skinning, hologram depth/blending, Adam's likeness, family audio and the full
packaged opening require their separate GPU/content acceptance evidence.

## External installed SDK GPU example

`examples/sdk_consumer/guide_gpu.cpp` is a separate consumer of the installed
public SDK. It accepts the installed shader directory and an evidence output
directory, and reads no canonical source assets or family references. Its only
static scene geometry is a small floor/background; the guide goes through
`set_character` and the indexed `CharacterInstance` draw overload.

The executable captures the background, idle figure, walk at0/0.25seconds and
cleared background through actual GPU readback. It checks that authored bone
samples change pixels, thirty ordinary pose frames reuse persistent character
buffers without replacing scenery or draining the GPU, clearing restores the
exact original background, and the DX12 debug layer reports no errors/warnings.
Its `verification.json` reports actual measured pixel differences, frame counts
and charged GPU bytes only after those assertions pass. Registration, installed
Release/Debug execution and their reports belong to the checkpoint verifier;
source presence alone does not establish a passing installed-SDK GPU test.
