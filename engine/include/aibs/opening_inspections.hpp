#pragma once
#include <aibs/first_boot_content.hpp>
#include <string_view>
#include <cstddef>

namespace aibs {
enum class OpeningInspectionAction { read,seat };
struct OpeningInspection {
 std::string fixture_id,title,text,source;
 Vec3 center;
 OpeningInspectionAction action=OpeningInspectionAction::read;
};
// Pure owned content projection. FirstBootContent must additionally validate
// all other namespaces, collection limits, geometry and gameplay dependencies.
// inspect.<owned selectable fixture UUID>.{text,source,action} is one complete
// triple in AIBD3/warm_beginning. No changes to its binary map layout.
class OpeningInspectionCatalog {
public:
 explicit OpeningInspectionCatalog(const FirstBootContentDefinition&);
 const std::vector<OpeningInspection>& entries()const noexcept{return entries_;}
 const OpeningInspection* find(std::string_view fixture_id)const noexcept;
 // Actual owned vector/string capacities; native UI objects are charged separately.
 std::size_t resident_bytes()const noexcept;
private:
 std::vector<OpeningInspection> entries_;
};
// Ephemeral selection only: this module cannot move BS, pause a game, edit a
// chapter, open a door or award progress. The caller must prove its aimed hit
// and full-geometry line of sight; explicit reach is checked again here.
// A seat is a quiet reading/reflection panel, never a camera/body teleport or
// an assertion that a seated character animation already exists.
class OpeningInspectionSession {
public:
 explicit OpeningInspectionSession(OpeningInspectionCatalog catalog):catalog_(std::move(catalog)){}
 bool select(std::string_view fixture_id,Vec3 bs_feet,bool visible_line_of_sight);
 void close()noexcept{current_.reset();}
 std::optional<OpeningInspection> snapshot()const{return current_;}
 // Includes the owned catalog and optional selected entry/string capacities.
 std::size_t resident_bytes()const noexcept;
private:
 OpeningInspectionCatalog catalog_;
 std::optional<OpeningInspection> current_;
};
}
