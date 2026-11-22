#pragma once
#include <aibs/first_boot_content.hpp>
#include <string_view>
namespace aibs {
inline constexpr std::string_view first_boot_initial_view_key="view.initial_target";
struct FirstBootInitialView {std::string world_id,target_id;Vec3 center;};
// AIBD3 warm_beginning only. Target must be a current selectable inspection
// fixture. Absence retains legacy facing; empty serialized values are invalid.
std::optional<FirstBootInitialView> first_boot_initial_view(const FirstBootContentDefinition&);
// Full-geometry LOS and bounded facing are checked before view-only input is
// applied with elapsed0. No body teleport, physics tick or gameplay/store API.
bool frame_first_boot_initial_view(PlayerController&,const SceneSnapshot&,const FirstBootInitialView&);
// App explicitly supplies eligibility: a new player at the Jenison return,
// including a resumed timeline or successful reload. Revision is irrelevant;
// framing remains view-only and never adds a saved outcome.
// Genuine player movement/look/actions consume this optional initial policy.
// Ground settling may adjust the aim for at most32 idle frames; there is no
// movement restriction, narrative timer gate or persisted camera state.
class FirstBootInitialViewPolicy {
public:
 FirstBootInitialViewPolicy(const FirstBootContentDefinition&,bool jenison_return);
 bool apply(PlayerController&,const SceneSnapshot&,const WindowInput& actual);
 bool pending()const noexcept{return pending_;}
 bool applied()const noexcept{return applied_;}
private:
 std::optional<FirstBootInitialView> binding_;
 bool pending_=false,applied_=false;
 unsigned attempts_=0;
};
}
