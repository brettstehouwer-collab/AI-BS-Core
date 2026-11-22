#pragma once
#include <aibs/first_boot_content.hpp>
#include <aibs/lighting.hpp>

namespace aibs {
// Read-only presentation projection. Recompute after accepted runtime/content
// changes, not for every frame. Reserve circuits survive main/bypass loss;
// restored circuits use the exact same supply predicates as chapter rules.
// No component, semantic event, objective or save is changed by this function.
SceneLighting first_boot_content_lighting(const GameplayStoreRecovery&,
                                         const FirstBootContent&);
}
