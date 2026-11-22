#include <aibs/warm_opening.hpp>
#include <aibs/opening_inspections.hpp>
#include <aibs/initial_view.hpp>
#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace aibs {
WarmOpeningDraft make_warm_opening_draft(const CreatorSession& source,const WarmOpeningAssetRefs& assets){
 auto d=FirstBootContent::from_template(source).definition();d.format_version=3;d.asset_profile=AssetContentProfile::warm_beginning;d.exposure=1;
 for(const auto* reference:{&assets.capacitor,&assets.adam,&assets.original_recording,&assets.nook,&assets.fault,&assets.bypass,&assets.shelter})if(*reference)validate_asset_pack_reference(**reference);
 const auto spawn=d.jenison_returns.front();const Vec3 origin{spawn.x+32,spawn.y-.2f,spawn.z+25};
 auto p=[&](float x,float y,float z){return Vec3{origin.x+x,origin.y+y,origin.z+z};};
 constexpr Vec3 metal{.11f,.14f,.17f},plastic{.055f,.065f,.075f},copper{.65f,.29f,.09f},warm{.8f,.57f,.3f},page{.86f,.79f,.63f};
 auto box=[&](const char* name,Vec3 center,Vec3 half,Vec3 color,bool selectable=false,float emission=0){const auto id=new_uuid();d.fixtures.push_back({{id,name,center,half,color,emission,selectable},-1});return id;};
 auto inspect=[&](const std::string& id,const char* text,const char* source_note,const char* action="read"){
  const auto key="inspect."+id+".";d.hints.emplace(key+"text",text);d.hints.emplace(key+"source",source_note);d.hints.emplace(key+"action",action);
 };
 // The reserve nook is deliberately outside both objective volumes. Its floor
 // is a small step on the motherboard, not an alternative shelter credit.
 box("Nook reserve floor plate",p(-32.5f,.04f,-26),{3.6f,.04f,4.5f},{.19f,.15f,.11f});
 box("Nook rear shell",p(-32.5f,1.8f,-30.5f),{3.6f,1.8f,.18f},metal);
 box("Nook east shell",p(-28.9f,1.8f,-26),{.18f,1.8f,4.5f},metal);
 box("Nook south shell",p(-31.2f,1.8f,-21.5f),{2.3f,1.8f,.18f},metal);
 box("Nook west shell north",p(-36.1f,1.8f,-28.85f),{.18f,1.8f,1.65f},metal);
 box("Nook west shell south",p(-36.1f,1.8f,-22.3f),{.18f,1.8f,.8f},metal);
 box("Nook overhead shield",p(-32.5f,3.6f,-26),{3.6f,.12f,4.5f},plastic);
 box("Reserve light housing",p(-32.5f,3.38f,-26),{1.1f,.08f,.12f},warm,false,1.f);
 box("Controller work surface",p(-34.7f,.65f,-29),{1.15f,.65f,.5f},metal);
 const auto controller=box("Controller and turning",p(-34.7f,1.4f,-29),{.35f,.1f,.2f},{.23f,.27f,.32f},true);
 inspect(controller,
  "You wrote that Adam taught you to look and turn in games. Start by looking around this little reserve-lit corner. The motherboard is the world you will build, one connection at a time. Adam's memory can Follow, Wait or Recall; choosing your own pace remains yours.",
  "Echos Within, XML paragraph 682, Always Family Guy. Controller placement and gameplay guidance are authored adaptations, not a quotation from Adam.");
 box("Keepsake shelf",p(-30.3f,.8f,-28.8f),{.75f,.8f,.45f},metal);
 const auto truck=box("Red truck keepsake",p(-30.3f,1.76f,-28.8f),{.43f,.16f,.22f},{.62f,.055f,.035f},true);
 box("Keepsake truck cab",p(-30.42f,1.99f,-28.8f),{.18f,.1f,.2f},{.45f,.035f,.025f});
 for(const auto x:{-30.58f,-30.03f})for(const auto z:{-29.03f,-28.57f})box("Keepsake truck wheel",p(x,1.68f,z),{.095f,.095f,.065f},plastic);
 inspect(truck,
  "Your writing keeps a happy fragment of Adam pushing you in a red electric toy truck. This little keepsake holds that fragment without asking you to revisit the painful events around it. Later, building vehicles can grow from this memory; here, you can simply look and continue when you want.",
  "Echos Within, XML paragraph 69, Never Felt More Pain. The red toy-truck memory is sourced; this keepsake and future vehicle connection are game adaptations.");
 // Readable thin route strips are collidable but remain below the existing
 // .4m step limit. No invisible wall or timer gates any exploration stop.
 for(const auto z:{-20.f,-15.f,-10.f})box("West signal walkway",p(-37,.035f,z),{1.7f,.035f,2.35f},{.17f,.22f,.23f});
 box("Fault station rear chassis",p(-33,1.1f,-1.5f),{1.5f,1.1f,.3f},metal);
 box("Fault station copper rail",p(-33,2.3f,-1.5f),{1.4f,.08f,.14f},copper,false,.3f);
 const auto diagnostic=box("Supply diagnostic diagram",p(-34.4f,1.4f,-7.8f),{.8f,.5f,.12f},{.21f,.31f,.32f},true);
 inspect(diagnostic,
  "The fault station has two honest ways forward. Inspect the damaged supply, isolate it at the nearby switch, then either repair the main supply and reconnect it or build a relay at the bypass socket. Watch the current state and Adam's guidance. Neither route proves more about you; each changes how this opening records your first connection.",
  "Mechanical design adaptation. Echos Within, XML paragraph 1145, informs making something useful from damage; this electrical diagnostic is not a memoir event.");
 box("Bypass parts workbench",p(-43.3f,.65f,-8),{1.1f,.65f,.7f},metal);
 const auto bypass=box("Bypass build notes",p(-43.3f,1.4f,-8),{.65f,.035f,.38f},page,true);
 inspect(bypass,
  "A spare part can become a new path. Keep the damaged supply isolated. Aim down at the marked socket near the service entrance and use Build to create a relay; repair it if needed, then interact with the healthy relay to connect the bypass. You can dismantle and rebuild it. A door already opened stays a usable return route when power changes.",
  "Authored engine instructions for the existing Build, repair, connect-bypass and door-latch mechanics. The restoration theme is informed by Echos Within, XML paragraph 1145.");
 // Existing template walls, door apertures, Caretaker, lamp and writing desk
 // stay in their original locations. New details sit outside those approaches.
 const auto seat=box("Two quiet seats",p(-31,.45f,8.4f),{.5f,.45f,.5f},warm,true);
 box("Second quiet seat",p(-31,.45f,10),{.5f,.45f,.5f},warm);
 box("Quiet seat back",p(-30.6f,1.05f,8.4f),{.1f,.3f,.5f},metal);
 box("Second seat back",p(-30.6f,1.05f,10),{.1f,.3f,.5f},metal);
 inspect(seat,
  "Your reflective writing imagines Adam nearby. These two seats give that feeling a place inside the shelter. You may take a quiet reading pause here, ask Adam to wait, or carry on together. This is an imagined space made from your writing, not a claim that a conversation happened here. No response or emotional choice is required.",
  "Echos Within, XML paragraphs 270 and 1165: reflective imagining. Two seats and this optional quiet panel are authored adaptations. No historical dialogue is asserted.","seat");
 const auto shelter=box("Room for someone else",p(-41.3f,1.6f,10),{.25f,.25f,.2f},{.64f,.43f,.2f},true,.15f);
 inspect(shelter,
  "Shelter becomes meaningful when there is room for someone else. The Caretaker's lamp is an optional task: offer help or decline through the existing choice controls. You can still reach the Pencil Room either way. This fictional character is here to give you a small, practical choice about the space you have restored.",
  "Echos Within, XML paragraphs 946-947, inform protection and making room. The Caretaker and lamp quest are fictional gameplay; no family member is represented by this NPC.");
 const auto page_fixture=std::find_if(d.fixtures.begin(),d.fixtures.end(),[](const auto& f){return f.object.name=="Pencil and blank page";});
 if(page_fixture==d.fixtures.end())throw std::invalid_argument("Opening requires the original Pencil Room page fixture");page_fixture->object.selectable=true;const auto page_id=page_fixture->object.persistent_id;
 box("Pencil on the page",p(-40.3f,1.29f,17),{.22f,.012f,.018f},{.7f,.4f,.08f});
 inspect(page_id,
  "In your writing, a pencil preserves memories of Adam and your cousin, carrying a value possessions cannot replace. This page stays blank. There is no invented final letter to discover and no answer you must write. You have reached a place you can return to, with Adam's memory beside you and a larger world still waiting to be built.",
  "Echos Within, XML paragraph 332, Adam My Brother Always. Pencil Room is a game adaptation named in the project, not a literal location in the memoir.");
 // These are current-condition cues, not original recorded speech. Retain all
 // nine existing cue identities and their rule priority; no memoir invention.
 const std::map<std::string,std::string> guidance{
  {"adam.live_fault","I'm here. This nook has reserve light, but we are still inside Jenison. Start with what still responds. Follow the west signal path to the supply, or look around before we go."},
  {"adam.danger","Watch the arc. Step back toward the west path and isolate the supply before working on it."},
  {"adam.isolated","The damaged feed is isolated. We can repair the main supply or build a relay at the bypass socket. You choose the connection."},
  {"adam.repaired_isolated","Your repair holds. Reconnect the main feed at the isolation switch when you're ready; the bypass remains another option."},
  {"adam.repaired_connected","That connection holds. Main power is back. Open the main entrance when you're ready, and watch the warm circuits answer."},
  {"adam.bypass_power","That relay feed holds. The service door can open now. This path is one you built."},
  {"adam.bypass_open","The service path is open. We can build from here. You can return through an opened door even when the supply changes."},
  {"adam.shelter","We reached shelter. This is different from the little reserve nook. There is a workbench, a quiet place to pause and the Pencil Room ahead. The lamp is yours to help with or leave for now."},
  {"adam.pencil","The page can stay blank. You can rest, return to what you built or look toward the distant RTX core. I'll follow your lead."}
 };for(const auto& [key,value]:guidance)d.hints.insert_or_assign(key,value);
 FirstBootCompanionBinding adam;adam.entity_id=new_uuid();adam.name="Adam's memory";adam.spawn=spawn;adam.spawn.x+=2;adam.model=assets.adam;
 auto point=[&](float x,float z,float height=.2f){return p(x,height,z);};
 adam.routes.nodes={{"nook",adam.spawn},{"nook-turn",point(-33.5f,-25)},{"west",point(-37,-25)},{"west20",point(-37,-20)},{"west15",point(-37,-15)},{"west10",point(-37,-10)},{"fault",point(-37,-5.2f)},{"approach",point(-37,-1.5f)},{"junction",point(-37,1.9f)},{"main-front",point(-33,1.9f)},{"main-back",point(-33,6,.25f)},{"main-clear",point(-33,8,.25f)},{"service-front",point(-41,1.9f)},{"service-back",point(-41,6,.25f)},{"service-clear",point(-41,8,.25f)},{"hub",point(-37,8,.25f)},{"pencil-front",point(-37,10.7f,.25f)},{"pencil-back",point(-37,15,.25f)}};
 auto edge=[&](const char* from,const char* to,std::string gate=""){adam.routes.edges.push_back({from,to,std::move(gate),true});};
 for(const auto& pair:{std::pair{"nook","nook-turn"},{"nook-turn","west"},{"west","west20"},{"west20","west15"},{"west15","west10"},{"west10","fault"},{"fault","approach"},{"approach","junction"},{"junction","main-front"},{"junction","service-front"},{"main-back","main-clear"},{"main-clear","hub"},{"service-back","service-clear"},{"service-clear","hub"},{"hub","pencil-front"}})edge(pair.first,pair.second);
 for(const auto& row:d.initial_records)if(row.type_id=="firstboot.Door"){const auto& role=std::get<std::string>(row.fields.at("role"));if(role=="main")edge("main-front","main-back",row.entity_id);else if(role=="service")edge("service-front","service-back",row.entity_id);else if(role=="pencil")edge("pencil-front","pencil-back",row.entity_id);else throw std::invalid_argument("Unknown template door role");}d.companions.push_back(std::move(adam));
 auto light=[&](const char* name,Vec3 position,Vec3 color,float intensity,float radius,FirstBootLightPower power){FirstBootLightDefinition l;l.entity_id=new_uuid();l.name=name;l.position=position;l.color=color;l.intensity=intensity;l.radius=radius;l.power=power;d.lights.push_back(l);};
 FirstBootLightDefinition ambient;ambient.entity_id=new_uuid();ambient.name="Jenison low reserve visibility";ambient.kind=FirstBootLightKind::directional;ambient.direction={.4f,-.89442719f,.2f};ambient.color={.35f,.45f,.6f};ambient.intensity=.18f;d.lights.push_back(ambient);
 light("Nook emergency reserve",p(-32.5f,3.1f,-26),{1,.48f,.2f},3,12,FirstBootLightPower::reserve);
 light("Fault warning reserve",p(-34,2.6f,-5),{1,.25f,.08f},1.5f,8,FirstBootLightPower::reserve);
 light("Nook restored circuit",p(-32,2.9f,-25),{1,.67f,.32f},2.4f,16,FirstBootLightPower::restored);
 light("Shelter restored circuit",p(-36,2.8f,8),{1,.67f,.32f},3.5f,10,FirstBootLightPower::restored);
 light("Pencil workbench restored circuit",p(-39,2.5f,17),{1,.8f,.5f},3,8,FirstBootLightPower::restored);
 light("Distant RTX connection landmark",p(0,13,22),{.5f,.85f,1},3,28,FirstBootLightPower::restored);
 if(assets.capacitor){
  const auto& reference=*assets.capacitor;for(const auto position:{p(-30,.0f,-23),p(-34.5f,0,-1.4f),p(-44.6f,0,-6),p(-44.6f,0,-4.5f),p(-29.8f,.03f,6.8f),p(-29.8f,.03f,11.3f)}){
   // Existing fixture proxies also render. Keep this conservative square core
   // inside the owned .30m-radius shell, so it cannot hide the detailed mesh.
   // The explicit approximation is .095m narrower than the visual cylinder.
   const auto name="Workshop capacitor";box("Capacitor collision core",{position.x,position.y+.7f,position.z},{.205f,.42f,.205f},plastic);
   d.placements.push_back({new_uuid(),name,reference.asset_id,reference.asset_sha256,reference.pack_sha256,position,{1,1,1},{},false});
  }
 }
 const std::array<const std::optional<AssetPackReference>*,4> kits{{&assets.nook,&assets.fault,&assets.bypass,&assets.shelter}};
 const std::array<Vec3,4> kit_pivots{{p(-32.5f,0,-26),p(-33,0,-1.5f),p(-43.3f,0,-8),p(-40,0,10)}};
 constexpr const char* kit_names[]{"Warm nook detail kit","Fault station detail kit","Bypass approach detail kit","Shelter workbench detail kit"};
 for(std::size_t i=0;i<kits.size();++i)if(*kits[i]){const auto& reference=**kits[i];d.placements.push_back({new_uuid(),kit_names[i],reference.asset_id,reference.asset_sha256,reference.pack_sha256,kit_pivots[i],{1,1,1},{},false});}
 if(assets.original_recording)d.memories.push_back({new_uuid(),"Adam at the podium - original optional recording",p(-32.4f,.08f,-28),*assets.original_recording});
 d.hints.emplace(std::string(first_boot_initial_view_key),controller);
 if(d.hints.size()>32)throw std::invalid_argument("Opening retains more than the declared 32 guidance map entries");
 (void)OpeningInspectionCatalog(d);(void)first_boot_initial_view(d);return {std::move(d),{{controller,truck,diagnostic,bypass,seat,shelter,page_id}}};
}
WarmOpeningDraft make_warm_workshop_draft(const CreatorSession& source,const WarmOpeningAssetRefs& assets){
 auto result=make_warm_opening_draft(source,assets);auto& d=result.definition;
 auto fixture=[&](const std::string& id)->const FirstBootContentFixture&{const auto f=std::find_if(d.fixtures.begin(),d.fixtures.end(),[&](const auto& item){return item.object.persistent_id==id;});if(f==d.fixtures.end())throw std::invalid_argument("Opening workshop source fixture absent");return *f;};
 const auto controller=fixture(result.tour.ids[0]).object.center,diagnostic=fixture(result.tour.ids[2]).object.center,path=fixture(result.tour.ids[3]).object.center;
 const auto fault=std::find_if(d.initial_records.begin(),d.initial_records.end(),[](const auto& r){return r.type_id=="firstboot.PowerFault";});const auto npc=std::find_if(d.initial_records.begin(),d.initial_records.end(),[](const auto& r){return r.type_id=="firstboot.NPCQuest";});
 if(fault==d.initial_records.end()||npc==d.initial_records.end())throw std::invalid_argument("Workshop source roles missing");
 auto coordinate=[](const ComponentRecord& r,const char* key){return static_cast<float>(std::get<double>(r.fields.at(key)));};
 OpeningWorkshopBinding binding;
 const std::array<Vec3,5> centers{{{controller.x-.75f,controller.y+.05f,controller.z+.75f},{diagnostic.x+1.f,diagnostic.y-.1f,diagnostic.z+.9f},{path.x+.8f,path.y+.15f,path.z+1.f},{d.isolation_switch.x,d.isolation_switch.y+1.1f,d.isolation_switch.z-1.25f},{coordinate(*npc,"lamp_x")+1.4f,coordinate(*npc,"lamp_y")+1.15f,coordinate(*npc,"lamp_z")-.9f}}};
 constexpr const char* names[]{"Diagnostic probe - collect","Supply contact - sample","Path contact - sample","Present feed - test","Sheltered workbench - commission"};
 for(std::size_t i=0;i<5;++i){const auto id=new_uuid();binding.fixtures[i]=id;d.fixtures.push_back({{id,names[i],centers[i],{.16f,.16f,.16f},i==4?Vec3{.25f,.6f,.4f}:Vec3{.26f,.48f,.58f},.02f,true},-1,FixtureRole::workshop});}
 if(!d.hints.emplace(std::string(opening_workshop_hint_key),encode_opening_workshop_binding(binding)).second||d.hints.size()>32)throw std::invalid_argument("Workshop requires its one remaining bounded guidance entry");
 (void)FirstBootContent::create(d);return result;
}
FirstBootContentDefinition make_warm_opening_definition(const CreatorSession& source,const WarmOpeningAssetRefs& assets){return make_warm_opening_draft(source,assets).definition;}
}
