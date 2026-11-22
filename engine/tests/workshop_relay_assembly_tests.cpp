#include <aibs/warm_opening.hpp>
#include <aibs/opening_inspections.hpp>
#include <aibs/gameplay_codec.hpp>
#include <aibs/durable_first_boot.hpp>
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
 const auto root=(argc>1?std::filesystem::path(argv[1]):std::filesystem::current_path())/std::filesystem::path("assembly-"+new_uuid());std::filesystem::create_directories(root);
 CreatorSession source(first_boot_schema(),"assembly-integration","finite-relay");check(seed_first_boot(source).ok,"Seed source hardware");
 const auto draft=make_warm_workshop_draft(source,{});const auto content=FirstBootContent::create(draft.definition);const auto binding=*first_boot_content_workshop_binding(content.definition());
 const GameplayScope scope{"assembly-integration",content.definition().world_id,"finite-relay",new_uuid(),GameplayContext::player_world};
 Run run(content,scope,root/"finite.sqlite");
 const auto fault=record(run.state,role_id(content,"firstboot.PowerFault"));
 const Vec3 socket{static_cast<float>(std::get<double>(fault.fields.at("socket_x"))),static_cast<float>(std::get<double>(fault.fields.at("socket_y"))),static_cast<float>(std::get<double>(fault.fields.at("socket_z")))};
 const auto actor=at({socket.x,socket.y,socket.z-2});
 auto status=[&]{return first_boot_content_relay_assembly(run.state,content);};
 check(!status().initialized&&!status().pickup_available&&!status().part_available&&status().alive_relays==0,"Fresh state grants no free carried assembly");
 const auto initial=run.state;
 rejects([&]{(void)first_boot_content_build(run.state,{socket.x,socket.y+1.2f,socket.z},actor,content,"unfunded."+new_uuid());},"Free build without collected assembly accepted");
 check(same(run.state,initial),"Denied uncollected build changed durable state");
 rejects([&]{(void)run.collect();},"Assembly pickup before path observation accepted");
 (void)run.station(0);(void)run.station(1);(void)run.station(2);
 check(status().pickup_available&&!status().part_available,"Path observation exposes finite owned supply");
 check(run.collect().has_value(),"Explicit physical tray pickup did not publish");
 check(status().initialized&&status().part_available&&!status().legacy&&!status().pickup_available,"One assembly carried after pickup");
 auto duplicate_pickup=[&]{const auto before=run.state;try{check(!run.collect(),"Repeated collection created another batch");}catch(const std::invalid_argument&){}check(same(run.state,before),"Repeated collection changed finite state");};
 duplicate_pickup();
 const auto funded=run.state;
 rejects([&]{(void)first_boot_content_build(run.state,{socket.x+4,socket.y+1.2f,socket.z},actor,content,"wrong-socket."+new_uuid());},"Carried assembly spent away from socket");
 check(same(run.state,funded)&&status().part_available,"Wrong socket consumed assembly");
 auto batch=first_boot_content_build(run.state,{socket.x+.1f,socket.y+1.2f,socket.z+.1f},actor,content,"atomic-build."+new_uuid());
 check(batch.deltas.size()>=2&&std::any_of(batch.deltas.begin(),batch.deltas.end(),[](const auto& d){return d.component.type_id==opening_workshop_assembly_component_type;}),"Build omits same-batch assembly consumption");
 std::string first_relay;for(const auto& delta:batch.deltas)if(delta.component.type_id=="firstboot.Node")first_relay=delta.component.entity_id;check(!first_relay.empty(),"No relay UUID in construction batch");
 auto free_batch=batch;std::erase_if(free_batch.deltas,[](const auto& d){return d.component.type_id==opening_workshop_assembly_component_type;});rejects([&]{first_boot_content_rules(funded,applied(funded,free_batch),free_batch,actor,content);},"Direct node-only batch bypassed assembly consumption");
 auto spent_only=batch;std::erase_if(spent_only.deltas,[](const auto& d){return d.component.type_id=="firstboot.Node";});rejects([&]{first_boot_content_rules(funded,applied(funded,spent_only),spent_only,actor,content);},"Assembly-only batch spent part without atomic relay");
 {GameplayStore failing(run.db,run.state.scope,run.schemas,[](GameplayStoreStage stage){if(stage==GameplayStoreStage::before_commit)throw std::runtime_error("assembly rollback fixture");});check(failing.commit(batch).status==GameplayStoreStatus::failed,"Interrupted transaction incorrectly committed");check(same(failing.recover(),funded),"Failed build consumed part or published half relay");}
 run.node(batch,actor);check(!status().part_available&&status().alive_relays==1,"Built relay did not consume sole assembly");
 {GameplayStore store(run.db,run.state.scope,run.schemas);const auto before=store.recover();check(store.commit(batch).status==GameplayStoreStatus::retry&&same(store.recover(),before),"Exact construction retry duplicated resource or relay");}
 rejects([&]{(void)first_boot_content_build(run.state,{socket.x,socket.y+1.2f,socket.z},actor,content,"duplicate-build."+new_uuid());},"Duplicate/free second relay accepted");duplicate_pickup();
 run.isolation(true);FirstBootChapterCommand feed;feed.action=FirstBootChapterAction::connect_bypass;feed.relay_id=first_relay;(void)run.action(feed,actor);check(first_boot_content_supply(run.state,content).bypass,"Assembly-built relay cannot power normal bypass");
 const auto removed=first_boot_content_dismantle(run.state,first_relay,actor,content,"remove."+new_uuid());check(removed.has_value(),"Built relay cannot be dismantled");run.node(*removed,actor);
 check(status().part_available&&status().alive_relays==0&&!std::get<bool>(record(run.state,first_relay).fields.at("alive")),"Last dismantle did not atomically reclaim assembly with tombstone");
 const auto reclaimed=run.state;check(!first_boot_content_dismantle(run.state,first_relay,actor,content,"repeat-remove."+new_uuid()),"Repeated dismantle duplicated reclaimed assembly");check(same(run.state,reclaimed),"Repeated dismantle changed recovered state");
 feed.action=FirstBootChapterAction::disconnect_bypass;(void)run.action(feed,actor);
 auto rebuilt=first_boot_content_build(run.state,{socket.x,socket.y+1.2f,socket.z},actor,content,"rebuild."+new_uuid());std::string replacement;for(const auto& d:rebuilt.deltas)if(d.component.type_id=="firstboot.Node")replacement=d.component.entity_id;
 check(!replacement.empty()&&replacement!=first_relay,"Rebuild reused tombstoned relay identity");run.node(rebuilt,actor);check(!status().part_available&&status().alive_relays==1&&!std::get<bool>(record(run.state,first_relay).fields.at("alive")),"Rebuild duplicated assembly or resurrected old relay");
 feed.action=FirstBootChapterAction::connect_bypass;feed.relay_id=replacement;(void)run.action(feed,actor);check(first_boot_content_supply(run.state,content).bypass,"Recovered assembly relay fails normal connection");
 Run repair(content,{scope.project_id,scope.world_id,"repair-independent",new_uuid(),scope.context},root/"repair.sqlite");repair.repair_main();check(first_boot_content_supply(repair.state,content).main&&!first_boot_content_relay_assembly(repair.state,content).initialized,"Independent repair route now requires or grants relay assembly");
 // A historical low-level encoded construction is fixture preparation ONLY.
 // Normal new-build admission above always uses first_boot_content_build.
 Run legacy(content,{scope.project_id,scope.world_id,"legacy-existing",new_uuid(),scope.context},root/"legacy.sqlite");
 auto nodes=legacy.state;std::erase_if(nodes.components,[](const auto& r){return r.type_id!="firstboot.Node";});
 const auto old_build=durable_first_boot_build(nodes,{socket.x,socket.y+1.2f,socket.z},"legacy-recorded-build."+new_uuid(),scope.context);
 {GameplayStore old_store(legacy.db,legacy.state.scope,legacy.schemas);check(old_store.commit(old_build).status==GameplayStoreStatus::committed,"Prepare recorded old free-build fixture");legacy.state=old_store.recover();}
 std::string old_id;for(const auto& d:old_build.deltas)if(d.component.type_id=="firstboot.Node")old_id=d.component.entity_id;
 const auto old_unconnected=first_boot_content_relay_assembly(legacy.state,content);check(!old_unconnected.initialized&&!old_unconnected.part_available&&!old_unconnected.pickup_available&&old_unconnected.alive_relays==1,"Old built-unconnected save received a duplicate supply");
 rejects([&]{(void)first_boot_content_build(legacy.state,{socket.x,socket.y+1.2f,socket.z},actor,content,"legacy-free-second."+new_uuid());},"Old built save admitted free second relay");
 legacy.isolation(true);feed.action=FirstBootChapterAction::connect_bypass;feed.relay_id=old_id;(void)legacy.action(feed,actor);
 const auto old_connected=legacy.state;const auto old_registry=GameplayStore::inspect_registry(legacy.db,legacy.state.scope);
 const auto old_query=first_boot_content_relay_assembly(legacy.state,content);
 check(!old_query.initialized&&!old_query.part_available&&!old_query.pickup_available&&old_query.legacy&&old_query.alive_relays==1,"Old living relay was reset or granted an extra assembly");
 first_boot_content_validate(legacy.state,content);check(first_boot_content_supply(legacy.state,content).bypass,"Old connected bypass invalidated on current read");
 check(same(legacy.state,old_connected)&&gameplay_codec::encode_schemas(GameplayStore::inspect_registry(legacy.db,legacy.state.scope))==gameplay_codec::encode_schemas(old_registry),"Passive old read migrated records or registry");
 const auto legacy_remove=first_boot_content_dismantle(legacy.state,old_id,actor,content,"legacy-reclaim."+new_uuid());check(legacy_remove.has_value(),"Old connected relay cannot be reclaimed");legacy.node(*legacy_remove,actor);
 const auto migrated=first_boot_content_relay_assembly(legacy.state,content);check(migrated.initialized&&migrated.part_available&&migrated.legacy&&migrated.alive_relays==0,"Explicit old dismantle did not reclaim exactly one finite assembly");
 {GameplayStore store(legacy.db,legacy.state.scope,legacy.schemas);check(store.lookup_batch(old_build.operation_id).has_value(),"Registry admission lost original legacy construction receipt");}
 Run multiple(content,{scope.project_id,scope.world_id,"multiple-legacy",new_uuid(),scope.context},root/"multiple.sqlite");
 std::vector<std::string> historical_relays;
 for(const float offset:{0.f,4.f}){
  auto old_nodes=multiple.state;std::erase_if(old_nodes.components,[](const auto& r){return r.type_id!="firstboot.Node";});
  const auto old=durable_first_boot_build(old_nodes,{socket.x+offset,socket.y+1.2f,socket.z},"legacy-multiple."+new_uuid(),scope.context);
  {GameplayStore store(multiple.db,multiple.state.scope,multiple.schemas);check(store.commit(old).status==GameplayStoreStatus::committed,"Prepare distinct historical legacy relay");multiple.state=store.recover();}
  for(const auto& d:old.deltas)if(d.component.type_id=="firstboot.Node")historical_relays.push_back(d.component.entity_id);
 }
 check(historical_relays.size()==2&&first_boot_content_relay_assembly(multiple.state,content).alive_relays==2,"Legacy relay count excludes off-socket living relay");
 const auto first_remove=first_boot_content_dismantle(multiple.state,historical_relays[0],actor,content,"legacy-first-remove."+new_uuid());check(first_remove.has_value(),"First historical relay not removable");multiple.node(*first_remove,actor);
 const auto one_left=first_boot_content_relay_assembly(multiple.state,content);check(one_left.initialized&&one_left.legacy&&!one_left.part_available&&one_left.alive_relays==1,"Removing one of multiple legacy relays minted spare supply");
 const auto second_actor=at({socket.x+4,socket.y,socket.z-2});const auto last_remove=first_boot_content_dismantle(multiple.state,historical_relays[1],second_actor,content,"legacy-last-remove."+new_uuid());check(last_remove.has_value(),"Final historical relay not removable");multiple.node(*last_remove,second_actor);
 const auto none_left=first_boot_content_relay_assembly(multiple.state,content);check(none_left.part_available&&none_left.alive_relays==0&&none_left.legacy,"Final historical relay failed finite single reclaim");
 Run tombstone(content,{scope.project_id,scope.world_id,"legacy-tombstone",new_uuid(),scope.context},root/"tombstone.sqlite");
 auto old_nodes=tombstone.state;std::erase_if(old_nodes.components,[](const auto& r){return r.type_id!="firstboot.Node";});const auto historical=durable_first_boot_build(old_nodes,{socket.x,socket.y+1.2f,socket.z},"historical-tray-build."+new_uuid(),scope.context);std::string historical_id;for(const auto& d:historical.deltas)if(d.component.type_id=="firstboot.Node")historical_id=d.component.entity_id;
 {GameplayStore store(tombstone.db,tombstone.state.scope,tombstone.schemas);check(store.commit(historical).status==GameplayStoreStatus::committed,"Prepare historical pre-assembly relay");tombstone.state=store.recover();}
 old_nodes=tombstone.state;std::erase_if(old_nodes.components,[](const auto& r){return r.type_id!="firstboot.Node";});const auto historical_remove=durable_first_boot_dismantle(old_nodes,historical_id,"historical-tray-remove."+new_uuid(),scope.context);check(historical_remove.has_value(),"Prepare historical tombstone operation");
 {GameplayStore store(tombstone.db,tombstone.state.scope,tombstone.schemas);check(store.commit(*historical_remove).status==GameplayStoreStatus::committed,"Prepare old tombstone-only save");tombstone.state=store.recover();}
 (void)tombstone.station(0);(void)tombstone.station(1);(void)tombstone.station(2);
 const auto pending_tray=first_boot_content_relay_assembly(tombstone.state,content);check(!pending_tray.initialized&&pending_tray.pickup_available&&!pending_tray.part_available&&pending_tray.legacy,"Historical tombstone passively received or lost recoverable tray supply");
 check(tombstone.collect().has_value(),"Explicit tray pickup failed for earlier tombstone-only save");const auto recovered_tray=first_boot_content_relay_assembly(tombstone.state,content);check(recovered_tray.initialized&&recovered_tray.part_available&&recovered_tray.legacy&&!recovered_tray.pickup_available,"Historical tray pickup did not preserve finite legacy provenance");
 std::cout<<checks<<" assembly checks; "<<restarts<<" saved-owner restarts; evidence "<<root.string()<<'\n';return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
