#pragma once
#include <aibs/first_boot_content.hpp>
#include <aibs/opening_tour.hpp>
namespace aibs {
// References must already be adopted into the new project's immutable store.
// Capacitor units/pivot match the owned workshop kit: one metre per unit,
// Y-up, board-mount pivot, .30m-radius shell from Y=.275..1.125m; owned pins
// extend to Y=-.03m into the board (admission allows no lower than -.04m).
// Its explicit
// .205/.42/.205m collision core stays inside the rendered shell; this is a
// documented .095m horizontal approximation, not imported mesh collision.
struct WarmOpeningAssetRefs {
 std::optional<AssetPackReference> capacitor,adam,original_recording;
 // Optional nonselectable visual-only kits; metre units, Y-up and an
 // owned local board-mount pivot. Existing collision proxies remain.
 std::optional<AssetPackReference> nook,fault,bypass,shelter;
};
struct WarmOpeningDraft {FirstBootContentDefinition definition;OpeningTourTargets tour;};
// Named role identities are returned as typed data for optional diagnostics;
// normal game content does not depend on a sidecar or fixture-name parser.
WarmOpeningDraft make_warm_opening_draft(const CreatorSession&,const WarmOpeningAssetRefs&);
// Builds a new definition from this source's template. Caller creates a NEW
// CreatorSession/branch, validates with FirstBootContent::create, and saves via
// ContentAuthoringHost. No existing project/save or family source is modified.
// Explicit opt-in; legacy factory bytes/roles remain unchanged.
WarmOpeningDraft make_warm_workshop_draft(const CreatorSession&,const WarmOpeningAssetRefs&);
FirstBootContentDefinition make_warm_opening_definition(const CreatorSession&,
                                                       const WarmOpeningAssetRefs&);
}
