#include <aibs/warm_opening.hpp>
#include <aibs/opening_inspections.hpp>
#include <aibs/gameplay_codec.hpp>
#include <algorithm>
#include <filesystem>
#include <iostream>
#include <stdexcept>
using namespace aibs;
namespace {
unsigned checks=0,restarts=0;
void check(bool v,const char* why){++checks;if(!v)throw std::runtime_error(why);}
template<class F>void rejects(F f,const char* why){bool rejected=false;try{f();}catch(const std::exception&){rejected=true;}check(rejected,why);}
const ComponentRecord& record(const GameplayStoreRecovery& s,const std::string& id){const auto r=std::find_if(s.components.begin(),s.components.end(),[&](const auto& x){return x.entity_id==id;});if(r==s.components.end())throw std::runtime_error("Record absent");return *r;}
GameplayStoreRecovery applied(GameplayStoreRecovery state,const GameplayChangeBatch& b){state.revision=b.revision;state.sequence=b.events.back().sequence;for(const auto& d:b.deltas){auto r=std::find_if(state.components.begin(),state.components.end(),[&](const auto& x){return x.entity_id==d.component.entity_id&&x.type_id==d.component.type_id;});if(r==state.components.end())state.components.push_back(d.component);else *r=d.component;}return state;}
bool same(const GameplayStoreRecovery& a,const GameplayStoreRecovery& b){if(a.scope!=b.scope||a.revision!=b.revision||a.sequence!=b.sequence||a.components.size()!=b.components.size())return false;auto canonical=[](const auto& components){std::vector<std::vector<unsigned char>> rows;for(const auto& c:components)rows.push_back(gameplay_codec::encode_component(c));std::sort(rows.begin(),rows.end());return rows;};return canonical(a.components)==canonical(b.components);}
FirstBootChapterActor at(Vec3 feet){FirstBootChapterActor a;a.feet=feet;a.previous_feet=feet;a.grounded=true;return a;}
FirstBootChapterActor approach(const GameplayStoreRecovery& s,const FirstBootContent& content,const std::string& id){
 auto scene=first_boot_content_scene(s,content);auto visible=scene;for(auto& o:visible.objects)o.selectable=true;
 const auto& d=content.definition();const auto f=std::find_if(d.fixtures.begin(),d.fixtures.end(),[&](const auto& x){return x.object.persistent_id==id;});if(f==d.fixtures.end())throw std::runtime_error("Approach target absent");
 const auto binding=*first_boot_content_workshop_binding(d);const auto floor=(id==binding.fixtures[4]?d.hub_returns.front():d.jenison_returns.front()).y;
 for(const auto offset:{Vec3{1.2f,0,0},Vec3{-1.2f,0,0},Vec3{0,0,1.2f},Vec3{0,0,-1.2f},Vec3{2.5f,0,0},Vec3{-2.5f,0,0},Vec3{0,0,2.5f},Vec3{0,0,-2.5f}}){try{
  const auto p=f->object.center;GroundedCharacter body(scene,{p.x+offset.x,floor,p.z+offset.z});for(unsigned i=0;i<24;++i)body.advance({},1./60);const auto body_state=body.state();if(!body_state.grounded)continue;
  const Vec3 eye{body_state.feet.x,body_state.feet.y+.9f,body_state.feet.z};const auto hit=pick_scene(visible,eye,{p.x-eye.x,p.y-eye.y,p.z-eye.z},3.2f);if(hit&&hit->persistent_id==id)return at(body_state.feet);
 }catch(const std::invalid_argument&) {}}
 throw std::runtime_error("No actual physical local approach");
}
std::string role_id(const FirstBootContent& c,const std::string& type){for(const auto& r:c.definition().initial_records)if(r.type_id==type)return r.entity_id;throw std::runtime_error("Content role absent");}
struct Run {
 FirstBootContent content;GameplayStoreRecovery state;std::filesystem::path db;std::vector<ComponentSchema> schemas;
 Run(FirstBootContent c,GameplayScope scope,const std::filesystem::path& path):content(std::move(c)),state{std::move(scope),0,0,first_boot_content_baseline(content).components},db(path),schemas(first_boot_content_schemas(content)){GameplayStore store(db,state.scope,schemas);check(store.seed(first_boot_content_baseline(content)).status==GameplayStoreStatus::committed,"Seed actual authored store");state=store.recover();}
 std::optional<GameplayChangeBatch> action(FirstBootChapterCommand c,const FirstBootChapterActor& actor){
  c.operation_id="workshop-test."+new_uuid();const auto before=state;const auto batch=first_boot_content_action(before,c,actor,content);if(!batch)return {};
  const auto next=applied(before,*batch);first_boot_content_rules(before,next,*batch,actor,content);ensure_registry(*batch);
  {GameplayStore store(db,state.scope,schemas);check(store.commit(*batch).status==GameplayStoreStatus::committed,"Commit actual workflow action");const auto committed=store.recover();check(same(committed,next),"Committed state differs from authoritative plan");check(store.commit(*batch).status==GameplayStoreStatus::retry,"Exact operation retry duplicated outcome");check(same(store.recover(),committed),"Retry changed durable head");}
  {GameplayStore reopened(db,state.scope,schemas);state=reopened.recover();check(same(state,next),"Workflow state lost after owner restart");++restarts;}
  return batch;
 }
 std::optional<GameplayChangeBatch> station(unsigned n){const auto binding=*first_boot_content_workshop_binding(content.definition());FirstBootChapterCommand c;c.action=static_cast<FirstBootChapterAction>(static_cast<unsigned>(FirstBootChapterAction::collect_probe)+n);c.target_id=binding.fixtures[n];return action(c,approach(state,content,c.target_id));}
 void node(const GameplayChangeBatch& batch,const FirstBootChapterActor& actor){ensure_registry(batch);const auto next=applied(state,batch);first_boot_content_rules(state,next,batch,actor,content);{GameplayStore store(db,state.scope,schemas);check(store.commit(batch).status==GameplayStoreStatus::committed,"Commit actual relay change");}{GameplayStore reopened(db,state.scope,schemas);state=reopened.recover();check(same(state,next),"Relay/workshop state lost on restart");++restarts;}}
 void ensure_registry(const GameplayChangeBatch& batch){
  if(std::none_of(batch.deltas.begin(),batch.deltas.end(),[](const auto& d){return d.component.type_id==opening_workshop_assembly_component_type;}))return;
  const auto target=first_boot_content_relay_assembly_schemas(content);
  if(gameplay_codec::encode_schemas(schemas)==gameplay_codec::encode_schemas(target))return;
  const auto before=state;check(GameplayStore::extend_registry(db,state.scope,schemas,target,"assembly-test.registry.v1",state.revision,state.sequence).status==GameplayStoreStatus::committed,"Explicit additive registry admission");
  schemas=target;GameplayStore reopened(db,state.scope,schemas);check(same(reopened.recover(),before),"Registry extension changed gameplay records/heads");
 }
 std::optional<GameplayChangeBatch> collect(){const auto b=*first_boot_content_workshop_binding(content.definition());FirstBootChapterCommand c;c.action=FirstBootChapterAction::collect_relay_part;c.target_id=b.fixtures[2];return action(c,approach(state,content,c.target_id));}
 void isolation(bool enabled){const auto p=content.definition().isolation_switch;FirstBootChapterCommand c;c.action=FirstBootChapterAction::set_isolation;c.enabled=enabled;(void)action(c,at({p.x,p.y,p.z-1.5f}));}
 void repair_main(){const auto f=record(state,role_id(content,"firstboot.PowerFault"));isolation(true);FirstBootChapterCommand c;c.action=FirstBootChapterAction::repair_fault;(void)action(c,at({static_cast<float>(std::get<double>(f.fields.at("x"))),static_cast<float>(std::get<double>(f.fields.at("y"))),static_cast<float>(std::get<double>(f.fields.at("z")))-1.6f}));isolation(false);}
};
}
int main(int argc,char** argv){try{
 const auto root=(argc>1?std::filesystem::path(argv[1]):std::filesystem::current_path())/std::filesystem::path("workshop-"+new_uuid());std::filesystem::create_directories(root);
 CreatorSession source(first_boot_schema(),"workshop-integration","fresh-workshop");check(seed_first_boot(source).ok,"Seed source");const auto source_world=source.world();
 const auto legacy=make_warm_opening_draft(source,{});const auto legacy_content=FirstBootContent::create(legacy.definition);
 check(legacy.definition.hints.size()==31&&!first_boot_content_workshop_binding(legacy.definition),"Legacy default factory opted in");check(legacy.definition.initial_records.size()==6,"Legacy six records changed");
 const auto draft=make_warm_workshop_draft(source,{});const auto content=FirstBootContent::create(draft.definition);const auto binding=*first_boot_content_workshop_binding(content.definition());
 check(source.world()==source_world,"Factory mutated source hardware");check(content.definition().hints.size()==32&&content.definition().initial_records.size()==6,"Opt-in counts changed");check(OpeningInspectionCatalog(content.definition()).entries().size()==7,"Seven personal inspections changed");
 const auto bytes=first_boot_content_encode(content);check(first_boot_content_encode(first_boot_content_decode(bytes))==bytes,"Opt-in definition byte roundtrip");check(decode_opening_tour(encode_opening_tour(content,draft.tour),content).ids==draft.tour.ids,"Seven tour bindings changed");
 const auto old_schemas=first_boot_content_schemas(legacy_content),new_schemas=first_boot_content_schemas(content);check(new_schemas.size()==old_schemas.size()+1,"Schema was not conditional");for(std::size_t i=0;i<old_schemas.size();++i)check(gameplay_codec::encode_schemas({old_schemas[i]})==gameplay_codec::encode_schemas({new_schemas[i]}),"Existing registry entry changed");
 auto malformed=content.definition();malformed.hints.erase(std::string(opening_workshop_hint_key));rejects([&]{(void)FirstBootContent::create(malformed);},"Role2 accepted without binding");
 malformed=content.definition();for(auto& f:malformed.fixtures)if(f.object.persistent_id==binding.fixtures[0])f.object.selectable=false;rejects([&]{(void)FirstBootContent::create(malformed);},"Nonselectable workshop accepted");
 malformed=content.definition();auto foreign_binding=binding;foreign_binding.fixtures[0]=new_uuid();malformed.hints[std::string(opening_workshop_hint_key)]=encode_opening_workshop_binding(foreign_binding);rejects([&]{(void)FirstBootContent::create(malformed);},"Foreign owned fixture binding accepted");
 malformed=content.definition();malformed.format_version=2;rejects([&]{(void)FirstBootContent::create(malformed);},"Workshop downgraded into legacy format");
 GameplayScope scope{source.project_id(),source.world_id(),source.branch_id(),new_uuid(),GameplayContext::player_world};Run run(content,scope,root/"workflow.sqlite");
 rejects([&]{(void)run.station(1);},"Sample before probe accepted");check(!std::get<bool>(record(run.state,binding.fixtures[4]).fields.at("has_probe")),"Rejected sample changed state");
 check(run.station(0).has_value(),"Probe did not publish");const auto picked=run.state;check(!run.station(0),"Probe duplicated on repeat");check(same(run.state,picked),"No-op changed durable head");
 check(run.station(1).has_value()&&run.station(2).has_value(),"Samples did not persist");rejects([&]{(void)run.station(3);},"Damaged source passed test");
 run.repair_main();check(run.station(3).has_value(),"Repaired main test failed");const auto tested=run.state;
 run.isolation(true);rejects([&]{(void)run.station(4);},"Stale test commissioned with no power");check(!std::get<bool>(record(run.state,binding.fixtures[4]).fields.at("bench_claimed")),"Failed commissioning claimed bench");
 run.isolation(false);check(run.station(4).has_value(),"Valid current main could not commission");check(opening_workshop_online(record(run.state,binding.fixtures[4]),binding,first_boot_content_workshop_circuit(run.state,content)),"Commissioned bench offline");
 run.isolation(true);check(std::get<bool>(record(run.state,binding.fixtures[4]).fields.at("bench_claimed"))&&!opening_workshop_online(record(run.state,binding.fixtures[4]),binding,first_boot_content_workshop_circuit(run.state,content)),"Power loss erased claim or remained online");
 run.isolation(false);check(opening_workshop_online(record(run.state,binding.fixtures[4]),binding,first_boot_content_workshop_circuit(run.state,content)),"Restored feed did not restore claimed bench");
 const auto& npc=record(run.state,role_id(content,"firstboot.NPCQuest"));const auto npc_actor=at({static_cast<float>(std::get<double>(npc.fields.at("x"))),static_cast<float>(std::get<double>(npc.fields.at("y"))),static_cast<float>(std::get<double>(npc.fields.at("z")))-1.5f});const auto bench_before=record(run.state,binding.fixtures[4]);
 FirstBootChapterCommand optional;optional.action=FirstBootChapterAction::decline_caretaker;(void)run.action(optional,npc_actor);optional.action=FirstBootChapterAction::help_caretaker;(void)run.action(optional,npc_actor);check(record(run.state,binding.fixtures[4])==bench_before,"Help/decline rewrote workshop state");
 FirstBootChapterCommand wrong;wrong.action=FirstBootChapterAction::collect_probe;wrong.target_id=binding.fixtures[1];rejects([&]{(void)first_boot_content_action(tested,wrong,approach(tested,content,binding.fixtures[0]),content);},"Wrong fixture action accepted");
 auto airborne=approach(tested,content,binding.fixtures[0]);airborne.grounded=false;wrong.target_id=binding.fixtures[0];rejects([&]{(void)first_boot_content_action(tested,wrong,airborne,content);},"Airborne action accepted");
 auto unauthorized=tested;unauthorized.scope.context=GameplayContext::authoring;rejects([&]{first_boot_content_validate(unauthorized,content);},"Authoring admitted gameplay state");
 // A separate authored scope exercises live relay identity, dismantling and rebuilding.
 Run bypass(content,{scope.project_id,scope.world_id,new_uuid(),new_uuid(),GameplayContext::player_world},root/"bypass.sqlite");(void)bypass.station(0);(void)bypass.station(1);(void)bypass.station(2);check(bypass.collect().has_value(),"Bypass explicitly collects finite relay assembly after path observation");check(first_boot_content_relay_assembly(bypass.state,content).part_available,"Collected relay assembly unavailable before build");bypass.isolation(true);
 const auto fault=record(bypass.state,role_id(content,"firstboot.PowerFault"));const Vec3 socket{static_cast<float>(std::get<double>(fault.fields.at("socket_x"))),static_cast<float>(std::get<double>(fault.fields.at("socket_y"))),static_cast<float>(std::get<double>(fault.fields.at("socket_z")))};const auto socket_actor=at({socket.x,socket.y,socket.z-2});
 auto built=first_boot_content_build(bypass.state,{socket.x,socket.y+1.2f,socket.z},socket_actor,content,"build."+new_uuid());const auto first_relay=built.deltas.front().component.entity_id;bypass.node(built,socket_actor);
 FirstBootChapterCommand feed;feed.action=FirstBootChapterAction::connect_bypass;feed.relay_id=first_relay;(void)bypass.action(feed,socket_actor);(void)bypass.station(3);
 const auto dismantle=*first_boot_content_dismantle(bypass.state,first_relay,socket_actor,content,"remove."+new_uuid());bypass.node(dismantle,socket_actor);rejects([&]{(void)bypass.station(4);},"Dismantled tested relay commissioned bench");
 feed.action=FirstBootChapterAction::disconnect_bypass;(void)bypass.action(feed,socket_actor);built=first_boot_content_build(bypass.state,{socket.x,socket.y+1.2f,socket.z},socket_actor,content,"rebuild."+new_uuid());const auto replacement=built.deltas.front().component.entity_id;check(replacement!=first_relay,"Rebuild reused tombstoned identity");bypass.node(built,socket_actor);
 feed.action=FirstBootChapterAction::connect_bypass;feed.relay_id=replacement;(void)bypass.action(feed,socket_actor);rejects([&]{(void)bypass.station(4);},"Replacement relay inherited stale successful test");(void)bypass.station(3);(void)bypass.station(4);check(opening_workshop_online(record(bypass.state,binding.fixtures[4]),binding,first_boot_content_workshop_circuit(bypass.state,content)),"Retested replacement bypass did not power claimed bench");
 bypass.node(*first_boot_content_dismantle(bypass.state,replacement,socket_actor,content,"remove-again."+new_uuid()),socket_actor);check(std::get<bool>(record(bypass.state,binding.fixtures[4]).fields.at("bench_claimed"))&&!opening_workshop_online(record(bypass.state,binding.fixtures[4]),binding,first_boot_content_workshop_circuit(bypass.state,content)),"Dismantle erased permanent claim or retained power");
 // A nonselectable authored occluder must stop the rules, not just the UI picker.
 auto wall_definition=content.definition();++wall_definition.revision;const auto source_actor=approach(tested,content,binding.fixtures[1]);const auto target_fixture=std::find_if(wall_definition.fixtures.begin(),wall_definition.fixtures.end(),[&](const auto& f){return f.object.persistent_id==binding.fixtures[1];});const Vec3 eye{source_actor.feet.x,source_actor.feet.y+.9f,source_actor.feet.z};const auto target=target_fixture->object.center;
 wall_definition.fixtures.push_back({{new_uuid(),"Nonselectable diagnostic occluder",{(eye.x+target.x)*.5f,(eye.y+target.y)*.5f,(eye.z+target.z)*.5f},{.12f,.12f,.12f},{.2f,.2f,.2f},0,false},-1});const auto wall_content=FirstBootContent::create(wall_definition);const auto wall_baseline=first_boot_content_baseline(wall_content);GameplayStoreRecovery wall_state{{scope.project_id,scope.world_id,new_uuid(),new_uuid(),GameplayContext::temporary_play},wall_baseline.revision,wall_baseline.sequence,wall_baseline.components};
 FirstBootChapterCommand use;use.action=FirstBootChapterAction::collect_probe;use.target_id=binding.fixtures[0];const auto collected=*first_boot_content_action(wall_state,use,approach(wall_state,wall_content,use.target_id),wall_content);wall_state=applied(wall_state,collected);use.action=FirstBootChapterAction::sample_supply;use.target_id=binding.fixtures[1];bool occluded=false;try{(void)first_boot_content_action(wall_state,use,source_actor,wall_content);}catch(const std::invalid_argument& e){occluded=std::string(e.what()).find("visible grounded reach")!=std::string::npos;}check(occluded,"Nonselectable geometry did not block actual workshop rules");
 // Actual transaction rollback before COMMIT retains the old durable baseline.
 Run failing(content,{scope.project_id,scope.world_id,new_uuid(),new_uuid(),GameplayContext::player_world},root/"failed.sqlite");FirstBootChapterCommand collect;collect.action=FirstBootChapterAction::collect_probe;collect.target_id=binding.fixtures[0];collect.operation_id="rollback."+new_uuid();const auto actor=approach(failing.state,content,binding.fixtures[0]);const auto batch=*first_boot_content_action(failing.state,collect,actor,content);const auto before=failing.state;
 {GameplayStore store(failing.db,before.scope,new_schemas,[](GameplayStoreStage stage){if(stage==GameplayStoreStage::before_commit)throw std::runtime_error("controlled workshop save failure");});check(store.commit(batch).status==GameplayStoreStatus::failed,"Injected transaction failure passed");check(same(store.recover(),before),"Failed save published durable workshop progress");}
 {GameplayStore store(failing.db,before.scope,new_schemas);check(store.commit(batch).status==GameplayStoreStatus::committed,"Exact failed operation could not retry");check(std::get<bool>(record(store.recover(),binding.fixtures[4]).fields.at("has_probe")),"Retry lost probe");}
 check(first_boot_content_encode(legacy_content)==first_boot_content_encode(first_boot_content_decode(first_boot_content_encode(legacy_content))),"Legacy encoded bytes changed");
 std::cout<<checks<<" integration checks; "<<restarts<<" actual saved-owner restarts; evidence "<<root.string()<<'\n';return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
