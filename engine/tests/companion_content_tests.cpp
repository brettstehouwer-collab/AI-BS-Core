#include <aibs/first_boot_content.hpp>
#include <aibs/gameplay_codec.hpp>
#include <algorithm>
#include <cmath>
#include <filesystem>
#include <iostream>
#include <limits>
#include <stdexcept>
using namespace aibs;
namespace fs=std::filesystem;
namespace {
unsigned checks=0;
void need(bool value,const char* message){if(!value)throw std::runtime_error(message);++checks;}
template<class F>void reject(F f,const char* message){bool failed=false;try{f();}catch(const std::invalid_argument&){failed=true;}need(failed,message);}
GameplayStoreRecovery state(const FirstBootContent& content){const auto b=first_boot_content_baseline(content);return {{"companion-content",content.definition().world_id,"main",new_uuid(),GameplayContext::temporary_play},b.revision,b.sequence,b.components};}
ComponentRecord& companion(GameplayStoreRecovery& s){for(auto& r:s.components)if(r.type_id=="firstboot.CompanionIntent")return r;throw std::runtime_error("Companion component missing");}
const ComponentRecord& find(const GameplayStoreRecovery& s,const char* type){for(const auto& r:s.components)if(r.type_id==type)return r;throw std::runtime_error("Fixture component missing");}
bool exact(const ComponentRecord& a,const ComponentRecord& b){return gameplay_codec::encode_component(a)==gameplay_codec::encode_component(b);}
bool same_components(const GameplayStoreRecovery& a,const GameplayStoreRecovery& b){std::map<std::string,gameplay_codec::Bytes> left,right;for(const auto& r:a.components)left.emplace(r.entity_id,gameplay_codec::encode_component(r));for(const auto& r:b.components)right.emplace(r.entity_id,gameplay_codec::encode_component(r));return left==right;}
GameplayStoreRecovery apply(GameplayStoreRecovery s,const GameplayChangeBatch& batch){for(const auto& delta:batch.deltas){auto p=std::find_if(s.components.begin(),s.components.end(),[&](const auto& r){return r.entity_id==delta.component.entity_id;});if(delta.action==ComponentAction::erase){if(p!=s.components.end())s.components.erase(p);}else if(p==s.components.end())s.components.push_back(delta.component);else *p=delta.component;}s.revision=batch.revision;s.sequence=batch.events.back().sequence;return s;}
FirstBootContent original(){CreatorSession source(first_boot_schema(),"companion-content","main");need(seed_first_boot(source).ok,"Seed original chapter");return FirstBootContent::from_template(source);}
FirstBootContentDefinition modern(const FirstBootContent& c){auto d=c.definition();d.format_version=3;d.asset_profile=AssetContentProfile::warm_beginning;const auto s=state(c);GroundedCharacter settled(first_boot_content_scene(s,c),d.jenison_returns.front());for(unsigned i=0;i<32;++i)settled.advance({},1.0/60);need(settled.state().grounded,"Authored companion has actual supported spawn");FirstBootCompanionBinding a;a.entity_id=new_uuid();a.name="Adam";a.spawn=settled.state().feet;d.companions.push_back(a);return d;}
}
int main(){try{
 const auto legacy=original();const auto legacy_registry=gameplay_codec::encode_schemas(first_boot_content_schemas());
 need(gameplay_codec::encode_schemas(first_boot_content_schemas(legacy))==legacy_registry,"AIBD1 keeps exact legacy registry bytes");
 auto legacy2=legacy.definition();legacy2.format_version=2;const auto v2=FirstBootContent::create(legacy2);
 need(gameplay_codec::encode_schemas(first_boot_content_schemas(v2))==legacy_registry,"AIBD2 keeps exact legacy registry bytes");
 auto unbound=legacy.definition();unbound.format_version=3;unbound.asset_profile=AssetContentProfile::warm_beginning;const auto lighting_only=FirstBootContent::create(unbound);
 need(gameplay_codec::encode_schemas(first_boot_content_schemas(lighting_only))==legacy_registry,"Companion-free AIBD3 keeps legacy registry identity");
 need(!first_boot_content_companion_intent(state(legacy),legacy)&&!first_boot_content_companion_intent(state(lighting_only),lighting_only),"Legacy and undeclared companion have no runtime intent");
 auto d=modern(legacy);const auto content=FirstBootContent::create(d);auto s=state(content);const auto baseline=s;
 const auto schemas=first_boot_content_schemas(content);need(schemas.size()==first_boot_content_schemas().size()+1,"Only one optional component schema is selected");
 const auto selected=std::find_if(schemas.begin(),schemas.end(),[](const auto& x){return x.type_id=="firstboot.CompanionIntent";});
 need(selected!=schemas.end()&&selected->version==1&&selected->fields.size()==4,"Exact optional companion schema exists");
 auto prefix=schemas;prefix.erase(std::find_if(prefix.begin(),prefix.end(),[](const auto& x){return x.type_id=="firstboot.CompanionIntent";}));
 need(gameplay_codec::encode_schemas(prefix)==legacy_registry&&gameplay_codec::encode_schemas(first_boot_content_schemas())==legacy_registry,"Optional schema preserves every original definition and no-arg registry");
 need(d.initial_records.size()==6&&content.definition().initial_records.size()==6,"Companion never changes six immutable chapter records");
 need(s.components.size()==state(legacy).components.size()+1,"Runtime baseline adds only optional companion intent");
 const auto original_record=companion(s);const auto initial=first_boot_content_companion_intent(s,content);
 need(initial&&initial->intent==GuideIntent::follow&&initial->waiting_anchor==d.companions[0].spawn,"Initial Follow/anchor comes from the immutable binding");
 need(original_record.entity_id==d.companions[0].entity_id&&original_record.version==1&&original_record.fields.size()==4,"Runtime identity and field shape are exact");
 need(exact(original_record,first_boot_content_companion_component(d.companions[0],*initial)),"Public component constructor agrees with actual baseline");
 first_boot_content_validate(s,content);need(true,"New baseline is a valid full chapter");
 auto waiting=d;waiting.companions[0].initial_follow=false;const auto wait_content=FirstBootContent::create(waiting);const auto wait_intent=first_boot_content_companion_intent(state(wait_content),wait_content);
 need(wait_intent&&wait_intent->intent==GuideIntent::wait&&wait_intent->waiting_anchor==waiting.companions[0].spawn,"Authored Wait intent is retained without invented movement history");
 const auto decoded=first_boot_content_decode(first_boot_content_encode(content));
 need(first_boot_content_encode(decoded)==first_boot_content_encode(content)&&gameplay_codec::encode_schemas(first_boot_content_schemas(decoded))==gameplay_codec::encode_schemas(schemas),"Content restart selects identical optional registry and bytes");
 auto bad=s;bad.components.erase(std::remove_if(bad.components.begin(),bad.components.end(),[](const auto& r){return r.type_id=="firstboot.CompanionIntent";}),bad.components.end());reject([&]{first_boot_content_validate(bad,content);},"Declared companion record cannot disappear");
 bad=s;bad.components.push_back(original_record);reject([&]{first_boot_content_validate(bad,content);},"Duplicate companion record rejects");
 bad=s;companion(bad).entity_id=new_uuid();reject([&]{first_boot_content_validate(bad,content);},"Wrong companion identity rejects");
 bad=s;companion(bad).version=2;reject([&]{first_boot_content_validate(bad,content);},"Unknown companion component version rejects");
 bad=s;companion(bad).fields.erase("follow");reject([&]{first_boot_content_validate(bad,content);},"Missing durable intent rejects");
 bad=s;companion(bad).fields["step"]=std::string("walk-frame-7");reject([&]{first_boot_content_validate(bad,content);},"Transient movement field cannot silently enter durable component");
 bad=s;companion(bad).fields["follow"]=1.0;reject([&]{first_boot_content_validate(bad,content);},"Follow must remain a boolean");
 for(const auto value:{std::numeric_limits<double>::infinity(),std::numeric_limits<double>::quiet_NaN(),1000001.0,1.1}){bad=s;companion(bad).fields["anchor_x"]=value;reject([&]{first_boot_content_validate(bad,content);},"Anchor requires finite bounded canonical-float coordinates");}
 bad=state(legacy);bad.components.push_back(original_record);reject([&]{first_boot_content_validate(bad,legacy);},"Legacy chapters never admit undeclared companion family");
 bad=state(lighting_only);bad.components.push_back(original_record);reject([&]{first_boot_content_validate(bad,lighting_only);},"Companion-free AIBD3 never admits extra family");
 bad=s;companion(bad).type_id="firstboot.Foreign";reject([&]{first_boot_content_validate(bad,content);},"Unknown component remains rejected");
 auto invalid_intent=*initial;invalid_intent.intent=static_cast<GuideIntent>(99);reject([&]{first_boot_content_companion_component(d.companions[0],invalid_intent);},"Constructor rejects unknown intent");
 invalid_intent=*initial;invalid_intent.waiting_anchor.x=std::numeric_limits<float>::infinity();reject([&]{first_boot_content_companion_component(d.companions[0],invalid_intent);},"Constructor rejects infinite anchor");
 invalid_intent=*initial;invalid_intent.waiting_anchor.x=1000001;reject([&]{first_boot_content_companion_component(d.companions[0],invalid_intent);},"Constructor enforces coordinate bounds");
 invalid_intent=*initial;invalid_intent.waiting_anchor={1000000,-1000000,0};need(first_boot_content_companion_component(d.companions[0],invalid_intent).fields.at("anchor_y")==GameplayValue{-1000000.0},"Structural coordinate endpoints remain representable");
 auto outside=s;companion(outside).fields["anchor_y"]=-1000.0;
 first_boot_content_validate(outside,content);need(!first_boot_content_scene(outside,content).objects.empty(),"A later-invalid waiting anchor does not invalidate the world or its scene");
 const auto outside_intent=first_boot_content_companion_intent(outside,content);need(outside_intent&&outside_intent->waiting_anchor.y==-1000,"Recovery preserves invalidated anchor for explicit Recall rather than teleporting");
 const auto& fault=find(s,"firstboot.PowerFault");FirstBootChapterActor actor;actor.feet=actor.previous_feet={static_cast<float>(std::get<double>(fault.fields.at("x"))-3),static_cast<float>(std::get<double>(fault.fields.at("y"))+.2),static_cast<float>(std::get<double>(fault.fields.at("z")))};
 FirstBootChapterCommand inspect;inspect.action=FirstBootChapterAction::inspect_fault;inspect.operation_id=new_uuid();const auto batch=first_boot_content_action(s,inspect,actor,content);need(batch.has_value(),"Real BS fault inspection remains available");
 auto after=apply(s,*batch);first_boot_content_rules(s,after,*batch,actor,content);need(exact(companion(after),original_record),"Ordinary BS chapter action preserves companion intent exactly");
 auto forged=after;companion(forged).fields["follow"]=false;reject([&]{first_boot_content_rules(s,forged,*batch,actor,content);},"BS inspection cannot covertly change companion intent");
 const auto anchor=initial->waiting_anchor;GuideController original_guide(first_boot_content_scene(s,content),anchor,d.companions[0].routes);
 FirstBootChapterActor builder;builder.feet=builder.previous_feet={anchor.x+2.3f,anchor.y,anchor.z};const auto construction=first_boot_content_build(s,{anchor.x,anchor.y+1.2f,anchor.z},builder,content,new_uuid());
 const auto built_state=apply(s,construction);first_boot_content_validate(built_state,content);
 need(exact(find(built_state,"firstboot.CompanionIntent"),original_record),"BS may build over the old guide anchor without rewriting it or vetoing construction");
 reject([&]{GuideController now_blocked(first_boot_content_scene(built_state,content),anchor,d.companions[0].routes);},"Actual construction invalidates guide placement and requires explicit Recall");
 auto forged_build=built_state;companion(forged_build).fields["follow"]=false;reject([&]{first_boot_content_rules(s,forged_build,construction,builder,content);},"Node construction cannot covertly rewrite companion intent");
 const auto relay=std::get<ConstructionOutcome>(construction.events.front().payload).entity_id;const auto dismantle=first_boot_content_dismantle(built_state,relay,builder,content,new_uuid());need(dismantle.has_value(),"BS can dismantle the obstructing build while the guide is blocked");
 const auto dismantled=apply(built_state,*dismantle);need(exact(find(dismantled,"firstboot.CompanionIntent"),original_record),"Dismantling preserves companion intent exactly");
 GuideController clear_again(first_boot_content_scene(dismantled,content),anchor,d.companions[0].routes);need(clear_again.state().character.grounded,"Dismantling restores support/clearance without an implicit guide action");
 const auto db=fs::temp_directory_path()/("aibs-companion-content-"+new_uuid()+".sqlite");
 {GameplayStore store(db,built_state.scope,schemas);need(store.seed({built_state.revision,built_state.sequence,built_state.components,{}}).status==GameplayStoreStatus::committed,"New compatible branch seeds optional companion without migration");need(store.verify().ok,"Seeded optional companion stream verifies");}
 {GameplayStore store(db,built_state.scope,schemas);const auto recovered=store.recover();first_boot_content_validate(recovered,content);need(first_boot_content_companion_intent(recovered,content)->waiting_anchor==anchor&&same_components(recovered,built_state),"SQLite restart preserves exact build and invalidated anchor without losing world");}
 reject([&]{GameplayStore mismatch(db,built_state.scope,first_boot_content_schemas());},"Existing bound save cannot silently drop its optional registry");
 fs::remove(db);auto wal=db;wal+=L"-wal";fs::remove(wal);auto shm=db;shm+=L"-shm";fs::remove(shm);
 need(baseline.revision==s.revision&&baseline.sequence==s.sequence&&baseline.components==s.components,"Read-only helpers preserve all authoritative state");
 std::cout<<"PASS "<<checks<<" companion registry, baseline, canonical intent, isolation and restart contracts\n";return 0;
 }catch(const std::exception& e){std::cerr<<"FAIL: "<<e.what()<<'\n';return 1;}}
