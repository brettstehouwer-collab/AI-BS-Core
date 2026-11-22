#include <aibs/companion_runtime.hpp>
#include <aibs/gameplay_world.hpp>
#include <cmath>
#include <filesystem>
#include <iostream>
#include <limits>
#include <stdexcept>
using namespace aibs;
namespace {
std::size_t checks=0;
void need(bool value,const char* message){++checks;if(!value)throw std::runtime_error(message);}
template<class F>void rejects(F f,const char* message){bool rejected=false;try{f();}catch(const std::invalid_argument&){rejected=true;}need(rejected,message);}
float distance(Vec3 a,Vec3 b){return std::hypot(a.x-b.x,a.y-b.y,a.z-b.z);}
FirstBootContent content(){CreatorSession source(first_boot_schema(),"companion-runtime","main");need(seed_first_boot(source).ok,"Seed chapter");auto d=FirstBootContent::from_template(source).definition();d.format_version=3;d.asset_profile=AssetContentProfile::warm_beginning;FirstBootCompanionBinding adam;adam.entity_id=new_uuid();adam.name="Adam's memory";adam.spawn=d.jenison_returns.front();adam.spawn.x+=2;d.companions.push_back(adam);return FirstBootContent::create(d);}
GameplayStoreRecovery baseline(const FirstBootContent& c){const auto b=first_boot_content_baseline(c);return {{"companion-runtime",c.definition().world_id,"main",new_uuid(),GameplayContext::temporary_play},b.revision,b.sequence,b.components};}
Vec3 settled_bs(const GameplayStoreRecovery& s,const FirstBootContent& c){GroundedCharacter bs(first_boot_content_scene(s,c),c.definition().jenison_returns.front());for(int i=0;i<32;++i)(void)bs.advance({},1.0/60);need(bs.state().grounded,"BS evidence comes from actual settled physics");return bs.state().feet;}
CompanionActor actor(const CompanionRuntime& runtime,Vec3 feet){return {{feet,true,runtime.state().scene_revision},false,false,42};}
GameplayStoreRecovery apply(const GameplayStoreRecovery& before,const GameplayChangeBatch& b){auto after=before;after.revision=b.revision;after.sequence=b.events.back().sequence;for(const auto& d:b.deltas){bool found=false;for(auto& r:after.components)if(r.entity_id==d.component.entity_id&&r.type_id==d.component.type_id){r=d.component;found=true;break;}if(!found)after.components.push_back(d.component);}return after;}
void accept(CompanionRuntime& runtime,GameplayStoreRecovery& state,std::unique_ptr<PreparedCompanionChoice> choice,const CompanionActor& bs){need(choice&&runtime.ready(*choice),"Choice staged and ready");const auto after=apply(state,choice->batch());runtime.validate_choice(*choice,state,after,choice->batch(),bs);need(runtime.publish(std::move(choice)),"Activate admitted choice without failure");state=after;}
void choices_and_isolation(){
 const auto c=content();auto s=baseline(c);const auto original=s.components;CompanionRuntime runtime(s,c);const auto bs=settled_bs(s,c);
 need(runtime.state().guide.has_value()&&!runtime.state().recall_required,"Valid initial anchor reconstructs guide");
 for(int i=0;i<100;++i)(void)runtime.advance({bs,true,runtime.state().scene_revision},1.0/60);
 need(s.components==original&&s.revision==0&&s.sequence==0,"Runtime footsteps never become durable history");
 auto wait=runtime.prepare_choice(s,CompanionAction::wait,actor(runtime,bs));need(wait&&runtime.state().saved.intent==GuideIntent::follow,"Preparing Wait preserves live intent");
 const auto batch=wait->batch();need(batch.schema_version==3&&batch.events.size()==1&&std::holds_alternative<CompanionOutcome>(batch.events.front().payload),"Wait has an honest companion outcome");
 auto forged=apply(s,batch);for(auto& r:forged.components)if(r.type_id=="firstboot.Node"){r.fields["capacity"]=99.0;break;}
 rejects([&]{runtime.validate_choice(*wait,s,forged,batch,actor(runtime,bs));},"Companion choice cannot rewrite BS hardware");
 auto wrong_actor=actor(runtime,bs);wrong_actor.target.feet.z+=1;rejects([&]{runtime.validate_choice(*wait,s,apply(s,batch),batch,wrong_actor);},"Changed BS evidence rejects staged choice");
 accept(runtime,s,std::move(wait),actor(runtime,bs));need(runtime.state().saved.intent==GuideIntent::wait,"Wait activates after admission");
 const auto waited=runtime.state().saved.waiting_anchor;CompanionRuntime restarted(s,c);need(restarted.state().saved.intent==GuideIntent::wait&&distance(restarted.state().guide->character.feet,waited)<.03f,"Restart restores exact durable Wait anchor");
 need(!runtime.prepare_choice(s,CompanionAction::wait,actor(runtime,bs)),"Repeated Wait invents no event");
 auto stale=runtime.prepare_choice(s,CompanionAction::follow,actor(runtime,bs));runtime.suspend();need(!runtime.ready(*stale)&&!runtime.publish(std::move(stale)),"Changed runtime invalidates stale prepared choice");need(runtime.state().saved.intent==GuideIntent::wait,"Stale choice does not change intent");
 auto paused=actor(runtime,bs);paused.paused=true;rejects([&]{(void)runtime.prepare_choice(s,CompanionAction::follow,paused);},"Paused controls cannot publish");
 paused=actor(runtime,bs);paused.inspection_mode=true;rejects([&]{(void)runtime.prepare_choice(s,CompanionAction::follow,paused);},"Inspection controls cannot publish");
 paused=actor(runtime,bs);paused.target.grounded=false;rejects([&]{(void)runtime.prepare_choice(s,CompanionAction::follow,paused);},"Airborne controls cannot publish");
 const auto pre=runtime.state().guide->character.feet;const std::vector<Vec3> bad{{bs.x,bs.y,bs.z},{bs.x,100,bs.z},{bs.x+20,bs.y,bs.z}};
 rejects([&]{(void)runtime.prepare_choice(s,CompanionAction::recall,actor(runtime,bs),bad);},"Unsupported, distant or overlapping Recall rejects");need(distance(runtime.state().guide->character.feet,pre)<.001f,"Failed Recall preserves live pose");
 const std::vector<Vec3> candidates{{bs.x,bs.y,bs.z+2}};auto recall=runtime.prepare_choice(s,CompanionAction::recall,actor(runtime,bs),candidates);accept(runtime,s,std::move(recall),actor(runtime,bs));need(runtime.state().saved.intent==GuideIntent::wait&&distance(runtime.state().saved.waiting_anchor,{bs.x,bs.y,bs.z+2})<.03f,"Explicit Recall preserves Wait and saves valid nearby anchor");
 const auto follow_actor=actor(runtime,bs);accept(runtime,s,runtime.prepare_choice(s,CompanionAction::follow,follow_actor),follow_actor);need(runtime.state().saved.intent==GuideIntent::follow,"Follow persists explicit intent");
 need(s.sequence==3&&s.revision==3,"Only three deliberate choices enter durable history");
}
void invalidated_anchor(){
 const auto c=content();auto s=baseline(c);CompanionRuntime runtime(s,c);const auto bs=settled_bs(s,c);const auto where=runtime.state().saved.waiting_anchor;
 FirstBootChapterActor builder;builder.feet=builder.previous_feet=bs;builder.grounded=true;
 const auto build=first_boot_content_build(s,{where.x,where.y+1.2f,where.z},builder,c);const auto built=apply(s,build);first_boot_content_rules(s,built,build,builder,c);s=built;runtime.synchronize(s);
 need(runtime.state().recall_required&&!runtime.state().guide,"Accepted BS construction can block Adam without veto");
 need(first_boot_content_companion_intent(s,c)->waiting_anchor==where,"Construction preserves durable companion anchor");
 CompanionRuntime restarted(s,c);need(restarted.state().recall_required&&!restarted.state().guide,"Invalid anchor on restart retains save and requires explicit Recall");
 rejects([&]{(void)restarted.prepare_choice(s,CompanionAction::follow,actor(restarted,bs));},"Follow never silently rematerializes a blocked guide");
 const std::vector<Vec3> candidates{{bs.x,bs.y,bs.z+2}};auto recall=restarted.prepare_choice(s,CompanionAction::recall,actor(restarted,bs),candidates);accept(restarted,s,std::move(recall),actor(restarted,bs));need(!restarted.state().recall_required&&restarted.state().guide.has_value(),"Explicit Recall repairs only the guide's own pose");
 need(s.components.size()==built.components.size(),"Recall does not erase BS's relay");
}
void durable_choices(const std::filesystem::path& directory){
 const auto c=content();auto s=baseline(c);const auto database=directory/(new_uuid()+".sqlite");
 {GameplayStore store(database,s.scope,first_boot_content_schemas(c));need(store.seed(first_boot_content_baseline(c)).status==GameplayStoreStatus::committed,"Seed selected companion schema");}
 GuideIntentRecord saved;
 {GameplayWorld world(database,s.scope,first_boot_content_schemas(c));CompanionRuntime runtime(*world.snapshot(),c);const auto bs=actor(runtime,settled_bs(*world.snapshot(),c));auto choice=runtime.prepare_choice(*world.snapshot(),CompanionAction::wait,bs);
  const auto prepared=world.prepare(choice->batch(),[&](const auto& before,const auto& after,const auto& batch){runtime.validate_choice(*choice,before,after,batch,bs);});need(prepared.status==GameplayPrepareStatus::prepared,"Actual GameplayWorld prepares companion choice");need(world.publish(prepared.change).ok,"Actual storage admission accepts");need(runtime.publish(std::move(choice)),"Accepted durable choice activates guide");saved=runtime.state().saved;need(world.close().ok,"Actual worker drains and joins");}
 {GameplayStore reopened(database,s.scope,first_boot_content_schemas(c));const auto recovered=reopened.recover();need(reopened.verify().ok&&recovered.revision==1&&recovered.sequence==1,"SQLite restart verifies complete companion receipt");CompanionRuntime runtime(recovered,c);need(runtime.state().saved.intent==saved.intent&&runtime.state().saved.waiting_anchor==saved.waiting_anchor,"SQLite restart reconstructs saved choice");need(!std::get<bool>([&]()->const ComponentRecord&{for(const auto& r:recovered.components)if(r.type_id=="firstboot.ChapterProgress")return r;throw std::runtime_error("Missing progress");}().fields.at("shelter_secured")),"Companion choices never secure shelter");}
}
void rejected_admission(const std::filesystem::path& directory){
 const auto c=content();const auto s=baseline(c);const auto database=directory/(new_uuid()+".sqlite");
 {GameplayStore store(database,s.scope,first_boot_content_schemas(c));need(store.seed(first_boot_content_baseline(c)).status==GameplayStoreStatus::committed,"Seed rejection proof");}
 GameplayWorld world(database,s.scope,first_boot_content_schemas(c));CompanionRuntime runtime(*world.snapshot(),c);const auto bs=actor(runtime,settled_bs(*world.snapshot(),c));const auto before=runtime.state();const auto head=world.snapshot();auto choice=runtime.prepare_choice(*head,CompanionAction::wait,bs);
 const auto prepared=world.prepare(choice->batch(),[&](const auto& b,const auto& a,const auto& batch){runtime.validate_choice(*choice,b,a,batch,bs);});need(prepared.status==GameplayPrepareStatus::prepared,"Prepare succeeds before actual admission failure");need(world.close().ok,"Close selected owner before publication");need(!world.publish(prepared.change).ok,"Actual GameplayWorld rejects publication after close");
 choice.reset();need(runtime.state().saved.intent==before.saved.intent&&runtime.state().saved.waiting_anchor==before.saved.waiting_anchor&&runtime.state().guide->character.feet==before.guide->character.feet,"Rejected admission and discarded candidate leave Adam unchanged");need(world.snapshot()==head&&world.state().visible_revision==0&&world.state().durable_revision==0,"Rejected admission leaves both world heads unchanged");
 GameplayStore reopened(database,s.scope,first_boot_content_schemas(c));need(reopened.recover().revision==0&&reopened.recover().sequence==0&&reopened.read_batches(0).empty(),"Rejected choice has no durable event or component mutation");
}
}
int main(int argc,char** argv){try{const auto output=argc==2?std::filesystem::path(argv[1]):std::filesystem::temp_directory_path()/new_uuid();std::filesystem::create_directories(output);choices_and_isolation();invalidated_anchor();durable_choices(output);rejected_admission(output);std::cout<<"PASS "<<checks<<" companion runtime, isolation, blocked-anchor, explicit Recall and SQLite restart contracts\n";return 0;}catch(const std::exception& e){std::cerr<<"FAIL "<<checks<<": "<<e.what()<<'\n';return 1;}}
