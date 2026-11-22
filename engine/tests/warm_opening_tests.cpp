#include <aibs/warm_opening.hpp>
#include <aibs/opening_inspections.hpp>
#include <algorithm>
#include <cmath>
#include <iostream>
#include <stdexcept>
using namespace aibs;
namespace {int checks=0;void check(bool value,const char* why){++checks;if(!value)throw std::runtime_error(why);}const SceneObject& named(const FirstBootContentDefinition& d,const std::string& name){const auto i=std::find_if(d.fixtures.begin(),d.fixtures.end(),[&](const auto& f){return f.object.name==name;});if(i==d.fixtures.end())throw std::runtime_error("Missing fixture: "+name);return i->object;}}
int main(){try{
 CreatorSession source(first_boot_schema(),"warm-opening-unit","new-opening");check(seed_first_boot(source).ok,"Seed failed");const auto original_world=source.world();const auto original_revision=source.revision();const auto original_memory=source.memory().events();const auto template_content=FirstBootContent::from_template(source);const auto d=make_warm_opening_definition(source,{});
 check(source.world()==original_world&&source.revision()==original_revision&&source.memory().events()==original_memory,"Factory mutated source authoring/history");
 check(d.hardware==original_world,"Factory changed imported hardware topology");
 check(d.format_version==3&&d.asset_profile==AssetContentProfile::warm_beginning,"Opening is not modern content");
 check(d.definition_id!=template_content.definition().definition_id,"Factory reused content identity");check(d.world_id==source.world_id(),"Factory changed source world identity");
 check(d.initial_records.size()==6,"Factory changed fixed chapter roles");
 for(const auto& row:d.initial_records){const auto expected=std::find_if(template_content.definition().initial_records.begin(),template_content.definition().initial_records.end(),[&](const auto& base){return row.type_id==base.type_id&&(row.type_id!="firstboot.Door"||row.fields.at("role")==base.fields.at("role"));});check(expected!=template_content.definition().initial_records.end()&&row.fields==expected->fields,"Factory silently rewrote an original role/default/outcome");}
 check(d.hub.center==template_content.definition().hub.center&&d.pencil.center==template_content.definition().pencil.center,"Opening silently changed objective zones");
 check(d.hints.size()==31,"Expected nine authored cues, seven inspection triples and one explicit framing target");
 const OpeningInspectionCatalog catalog(d);check(catalog.entries().size()==7,"Seven meaningful stops missing");
 check(named(d,"Controller and turning").center.z<-20,"Controller is not in boot nook");
 check(named(d,"Red truck keepsake").center.z<-20,"Personal keepsake not in boot nook");
 check(named(d,"Two quiet seats").center.z>4,"Quiet seats must be inside shelter");
 check(d.companions.size()==1&&d.companions.front().initial_follow,"Adam must begin beside BS");
 check(d.memories.empty(),"Unprovided family recording should never be invented/copied");
 check(d.placements.empty(),"Unprovided art dependency should never be invented");
 unsigned doors=0;for(const auto& r:d.initial_records){if(r.type_id=="firstboot.Door"){++doors;check(!std::get<bool>(r.fields.at("open")),"Door begins open");const auto gated=std::count_if(d.companions.front().routes.edges.begin(),d.companions.front().routes.edges.end(),[&](const auto& e){return e.door==r.entity_id;});check(gated==1,"Adam graph must have exactly one matching door edge");}if(r.type_id=="firstboot.ChapterProgress"){check(!std::get<bool>(r.fields.at("shelter_secured")),"Reserve nook awarded shelter");check(!std::get<bool>(r.fields.at("pencil_visited")),"Factory awarded Pencil Room");check(std::get<std::string>(r.fields.at("first_route"))=="none","Factory fabricated a route");}}
 check(doors==3,"Original main/service/Pencil roles missing");
 check(std::count_if(d.lights.begin(),d.lights.end(),[](const auto& light){return light.power==FirstBootLightPower::reserve;})>=2,"Warm reserve lights missing");
 check(std::count_if(d.lights.begin(),d.lights.end(),[](const auto& light){return light.power==FirstBootLightPower::restored;})>=3,"Restored circuit lighting missing");
 for(const auto& inspection:catalog.entries())check(!inspection.source.empty(),"Panel lost provenance");
 const AssetPackReference cap{"12345678-1234-4234-8234-123456789abc",std::string(64,'a'),std::string(64,'b')};const AssetPackReference model{"12345678-1234-4234-8234-123456789abd",std::string(64,'c'),std::string(64,'d')};const AssetPackReference audio{"12345678-1234-4234-8234-123456789abe",std::string(64,'e'),std::string(64,'f')};
 const auto with_assets=make_warm_opening_definition(source,{cap,model,audio});check(with_assets.placements.size()==6,"Capacitor kit placements missing");for(const auto& placed:with_assets.placements)check(AssetPackReference{placed.asset_id,placed.asset_sha256,placed.pack_sha256}==cap,"Placement lost exact immutable reference");check(with_assets.companions.front().model==model,"Adam lost exact model reference");check(with_assets.memories.size()==1&&with_assets.memories.front().audio==audio,"Optional recording lost exact audio reference");
 // Full content validation must succeed after the inspection namespace is wired.
 // This executes real Jolt support, doorway traversal and companion route checks.
 const auto content=FirstBootContent::create(d);check(first_boot_content_decode(first_boot_content_encode(content)).fingerprint()==content.fingerprint(),"AIBD3 restart changed opening");
 const auto baseline=first_boot_content_baseline(content);GameplayStoreRecovery recovery{{"warm-opening-unit",d.world_id,"new-opening",new_uuid(),GameplayContext::temporary_play},0,0,baseline.components};
 check(first_boot_content_region(recovery,d.jenison_returns.front(),content)=="jenison","Nook is not inside Jenison");check(first_boot_content_region(recovery,d.hub_returns.front(),content)=="hub","Destination is not shelter");
 check(first_boot_content_hint(recovery,FirstBootChapterActor{},content).find("reserve")!=std::string::npos,"Opening does not explain reserve supply");
 const auto supplied=FirstBootContent::create(with_assets);const auto supplied_roundtrip=first_boot_content_decode(first_boot_content_encode(supplied));check(supplied_roundtrip.fingerprint()==supplied.fingerprint(),"Modern placements/model/audio lost restart identity");check(supplied_roundtrip.definition().companions.front().model==model&&supplied_roundtrip.definition().memories.front().audio==audio,"Exact model/media binding lost from AIBD3");
 CreatorSession translated(first_boot_schema(),"warm-opening-translated","fresh-branch");check(seed_first_boot(translated).ok,"Translated seed failed");Transaction move{"opening.translate",translated.revision(),{},"Move the whole authored hardware world"};
 for(const auto& [alias,entity]:translated.world())for(const auto& [field,offset]:{std::pair{"x",80.0},std::pair{"y",-32.0},std::pair{"z",60.0}})move.edits.push_back(SetField{alias,field,entity.fields.at(field)+offset,entity.persistent_id});check(translated.apply(move).ok,"Translation authoring transaction failed");
 const auto shifted=make_warm_opening_definition(translated,{});const auto shifted_content=FirstBootContent::create(shifted);check(shifted.world_id!=d.world_id&&shifted.definition_id!=d.definition_id&&shifted.binding_id!=d.binding_id,"New branch reused world/content/binding identity");
 for(const auto& fixture:catalog.entries()){const auto& moved=named(shifted,fixture.title);check(std::abs(moved.center.x-fixture.center.x-80)<.0001f&&std::abs(moved.center.y-fixture.center.y+32)<.0001f&&std::abs(moved.center.z-fixture.center.z-60)<.0001f,"Personal-memory fixture failed translated-world placement");}
 check(shifted_content.definition().companions.front().spawn.y<0,"Adam did not retain translated negative-height ground");
 std::cout<<checks<<" warm opening assembly checks passed\n";return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
