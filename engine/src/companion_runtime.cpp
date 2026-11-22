#include <aibs/companion_runtime.hpp>
#include <aibs/gameplay_codec.hpp>
#include <algorithm>
#include <bit>
#include <cmath>
#include <limits>
#include <stdexcept>
#include <type_traits>

namespace aibs {
namespace {
void need(bool value,const char* message){if(!value)throw std::invalid_argument(message);}
bool finite(Vec3 p){return std::isfinite(p.x)&&std::isfinite(p.y)&&std::isfinite(p.z)&&std::max({std::abs(p.x),std::abs(p.y),std::abs(p.z)})<=1000000;}
bool exact(Vec3 a,Vec3 b){return std::bit_cast<std::uint32_t>(a.x)==std::bit_cast<std::uint32_t>(b.x)&&std::bit_cast<std::uint32_t>(a.y)==std::bit_cast<std::uint32_t>(b.y)&&std::bit_cast<std::uint32_t>(a.z)==std::bit_cast<std::uint32_t>(b.z);}
bool exact(GuideIntentRecord a,GuideIntentRecord b){return a.intent==b.intent&&exact(a.waiting_anchor,b.waiting_anchor);}
bool exact(const CompanionActor& a,const CompanionActor& b){return exact(a.target.feet,b.target.feet)&&a.target.grounded==b.target.grounded&&a.target.scene_revision==b.target.scene_revision&&a.inspection_mode==b.inspection_mode&&a.paused==b.paused&&a.active_tick==b.active_tick;}
CompanionIntentValue value(GuideIntentRecord record){return {record.intent==GuideIntent::follow,record.waiting_anchor.x,record.waiting_anchor.y,record.waiting_anchor.z};}
const char* action_name(CompanionAction action){switch(action){case CompanionAction::follow:return "follow";case CompanionAction::wait:return "wait";case CompanionAction::recall:return "recall";}throw std::invalid_argument("Unknown companion action");}
std::map<std::string,bool> doors(const GameplayStoreRecovery& state){std::map<std::string,bool> result;for(const auto& r:state.components)if(r.type_id=="firstboot.Door"){const auto open=std::get<bool>(r.fields.at("open"));result.emplace(r.entity_id,open);result.emplace(std::get<std::string>(r.fields.at("role")),open);}return result;}
}
struct PreparedCompanionChoice::Data {
 std::string owner;
 std::uint64_t epoch=0;
 CompanionActor actor;
 GuideIntentRecord saved;
 GameplayChangeBatch batch;
 SceneSnapshot scene;
 std::unique_ptr<GuideController> guide;
};
PreparedCompanionChoice::PreparedCompanionChoice(std::unique_ptr<Data> data):data_(std::move(data)){}
PreparedCompanionChoice::~PreparedCompanionChoice()=default;
const GameplayChangeBatch& PreparedCompanionChoice::batch()const noexcept{return data_->batch;}

struct CompanionRuntime::Impl {
 FirstBootContent content;
 FirstBootCompanionBinding binding;
 GuideSettings settings;
 GameplayScope scope;
 std::uint64_t revision=0,sequence=0,epoch=0;
 std::string owner=new_uuid();
 SceneSnapshot scene;
 GuideIntentRecord saved;
 std::unique_ptr<GuideController> guide;
 bool recall_required=false;
 Impl(const GameplayStoreRecovery& state,const FirstBootContent& c):content(c),scope(state.scope){
  const CharacterSettings bs;settings.walk_speed=bs.walk_speed;settings.catchup_speed=std::min(15.f,bs.sprint_speed+1.f);
  first_boot_content_validate(state,c);need(c.definition().companions.size()==1,"Runtime requires exactly one declared companion");binding=c.definition().companions.front();saved=*first_boot_content_companion_intent(state,c);scene=first_boot_content_scene(state,c);revision=state.revision;sequence=state.sequence;
  try{guide=std::make_unique<GuideController>(scene,saved.waiting_anchor,binding.routes,settings);guide->restore_intent(saved);guide->set_doors(doors(state));}catch(const std::invalid_argument&){guide.reset();recall_required=true;}
 }
 void check_state(const GameplayStoreRecovery& state)const{
  need(state.scope==scope&&state.revision==revision&&state.sequence==sequence,"Companion choice requires the current exact world head");
  const auto intent=first_boot_content_companion_intent(state,content);need(intent&&exact(*intent,saved),"Companion durable intent changed before choice");
 }
 void check_actor(const CompanionActor& actor)const{
  need(!actor.paused&&!actor.inspection_mode&&actor.target.grounded,"Companion choices require active grounded BS control");
  need(finite(actor.target.feet)&&actor.target.scene_revision==scene.revision,"Companion choice requires current BS scene evidence");
 }
};
CompanionRuntime::CompanionRuntime(const GameplayStoreRecovery& state,const FirstBootContent& content):impl_(std::make_unique<Impl>(state,content)){}
CompanionRuntime::~CompanionRuntime()=default;
CompanionRuntimeState CompanionRuntime::state()const{
 const auto& p=*impl_;return {p.saved,p.guide&&!p.recall_required?std::optional<GuideState>(p.guide->state()):std::nullopt,p.recall_required,p.scene.revision};
}
GuideState CompanionRuntime::advance(GuideTarget target,double elapsed){
 need(finite(target.feet)&&std::isfinite(elapsed)&&elapsed>=0,"Invalid companion frame");auto& p=*impl_;++p.epoch;
 if(p.recall_required||!p.guide){GuideState blocked;blocked.intent=p.saved.intent;blocked.activity=GuideActivity::blocked;blocked.destination=p.saved.waiting_anchor;return blocked;}
 return p.guide->advance(target,elapsed);
}
void CompanionRuntime::suspend()noexcept{auto& p=*impl_;++p.epoch;if(p.guide)p.guide->suspend();}
void CompanionRuntime::synchronize(const GameplayStoreRecovery& state){
 auto& p=*impl_;need(state.scope==p.scope&&state.revision>=p.revision&&state.sequence>=p.sequence,"Companion cannot adopt a foreign or older world");first_boot_content_validate(state,p.content);
 const auto saved=*first_boot_content_companion_intent(state,p.content);auto scene=first_boot_content_scene(state,p.content);auto gates=doors(state);
 if(state.revision==p.revision&&state.sequence==p.sequence){need(exact(saved,p.saved),"Same world head cannot rewrite companion intent");return;}
 const bool changed=!exact(saved,p.saved);p.saved=saved;p.scene=std::move(scene);p.revision=state.revision;p.sequence=state.sequence;++p.epoch;
 if(p.recall_required&&!changed)return;
 try{
  if(changed||!p.guide){auto guide=std::make_unique<GuideController>(p.scene,saved.waiting_anchor,p.binding.routes,p.settings);guide->restore_intent(saved);guide->set_doors(std::move(gates));p.guide.swap(guide);p.recall_required=false;}
  else{p.guide->set_scene(p.scene);p.guide->set_doors(std::move(gates));}
 }catch(const std::invalid_argument&){if(p.guide)p.guide->suspend();p.recall_required=true;}
}
std::unique_ptr<PreparedCompanionChoice> CompanionRuntime::prepare_choice(const GameplayStoreRecovery& state,CompanionAction action,const CompanionActor& actor,std::span<const Vec3> candidates,std::string operation)const{
 const auto& p=*impl_;p.check_state(state);p.check_actor(actor);const auto name=action_name(action);
 need(state.revision<std::numeric_limits<std::uint64_t>::max()&&state.sequence<std::numeric_limits<std::uint64_t>::max(),"Companion history counter exhausted");
 need(candidates.size()<=16,"Companion Recall candidate limit");
 if(action!=CompanionAction::recall){need(!p.recall_required&&p.guide,"Adam needs explicit Recall to a clear supported point");if((action==CompanionAction::follow)==(p.saved.intent==GuideIntent::follow))return {};}
 auto staged=std::make_unique<PreparedCompanionChoice::Data>();staged->owner=p.owner;staged->epoch=p.epoch;staged->actor=actor;staged->scene=p.scene;staged->scene.revision=state.revision+1;
 if(action==CompanionAction::recall){
  for(const auto candidate:candidates){
   if(!finite(candidate))continue;
   try{auto guide=std::make_unique<GuideController>(staged->scene,candidate,p.binding.routes,p.settings);guide->set_intent(p.saved.intent);if(!guide->recall(actor.target.feet,std::span<const Vec3>(&candidate,1)))continue;staged->guide=std::move(guide);break;}catch(const std::invalid_argument&){}
  }
  need(static_cast<bool>(staged->guide),"No supported Recall point within personal-space bounds");
 }else{
  const auto pose=p.guide->state().character;need(pose.grounded,"Adam needs ground support for a saved choice");
  need(std::hypot(pose.feet.x-actor.target.feet.x,pose.feet.y-actor.target.feet.y,pose.feet.z-actor.target.feet.z)>=.9f,"Give Adam personal space before choosing Follow or Wait");
  staged->guide=std::make_unique<GuideController>(staged->scene,pose.feet,p.binding.routes,p.settings);staged->guide->set_intent(action==CompanionAction::follow?GuideIntent::follow:GuideIntent::wait);
 }
 staged->guide->set_doors(doors(state));staged->saved=staged->guide->saved_intent();auto& batch=staged->batch;batch.schema_version=3;batch.scope=state.scope;batch.operation_id=operation.empty()?"firstboot.companion."+std::string(name)+"."+new_uuid():std::move(operation);batch.expected_revision=state.revision;batch.revision=state.revision+1;
 batch.deltas.push_back({ComponentAction::upsert,first_boot_content_companion_component(p.binding,staged->saved)});
 SemanticEvent event;event.event_id=new_uuid();event.payload_version=3;event.scope=state.scope;event.sequence=state.sequence+1;event.operation_id=batch.operation_id;event.subject_ids={p.binding.entity_id};event.source_revision=batch.revision;event.logical_tick=actor.active_tick;event.provenance={GameplayProvenance::player_input,"firstboot.companion."+std::string(name)+".v1"};event.payload=CompanionOutcome{p.binding.entity_id,action,value(p.saved),value(staged->saved)};batch.events.push_back(std::move(event));
 (void)gameplay_codec::encode_batch(batch);return std::unique_ptr<PreparedCompanionChoice>(new PreparedCompanionChoice(std::move(staged)));
}
bool CompanionRuntime::ready(const PreparedCompanionChoice& choice)const noexcept{
 const auto& p=*impl_;const auto& d=*choice.data_;return d.owner==p.owner&&d.epoch==p.epoch&&d.batch.scope==p.scope&&d.batch.expected_revision==p.revision&&d.batch.events.front().sequence==p.sequence+1;
}
void CompanionRuntime::validate_choice(const PreparedCompanionChoice& choice,const GameplayStoreRecovery& before,const GameplayStoreRecovery& after,const GameplayChangeBatch& batch,const CompanionActor& actor)const{
 const auto& p=*impl_;const auto& d=*choice.data_;need(ready(choice),"Stale or foreign prepared companion choice");p.check_state(before);p.check_actor(actor);need(exact(d.actor,actor),"BS evidence changed before companion publication");need(gameplay_batch_exact(batch,d.batch),"Prepared companion request changed before admission");
 first_boot_content_validate(after,p.content);need(after.scope==before.scope&&after.revision==batch.revision&&after.sequence==before.sequence+1&&after.components.size()==before.components.size(),"Companion outcome changed the world shape or head");
 const auto expected=first_boot_content_companion_component(p.binding,d.saved);std::map<std::pair<std::string,std::string>,const ComponentRecord*> remaining;
 for(const auto& r:after.components)need(remaining.emplace(std::pair{r.entity_id,r.type_id},&r).second,"Duplicate component in companion result");
 for(const auto& r:before.components){const auto found=remaining.find({r.entity_id,r.type_id});need(found!=remaining.end(),"Companion choice erased BS state");const auto& wanted=r.entity_id==p.binding.entity_id&&r.type_id==expected.type_id?expected:r;need(gameplay_codec::encode_component(*found->second)==gameplay_codec::encode_component(wanted),"Companion choice rewrote unrelated state");remaining.erase(found);}
 need(remaining.empty(),"Companion choice added unrelated state");
}
bool CompanionRuntime::publish(std::unique_ptr<PreparedCompanionChoice> choice)noexcept{
 if(!choice||!ready(*choice))return false;auto& p=*impl_;auto& d=*choice->data_;static_assert(std::is_nothrow_swappable_v<SceneSnapshot>);p.guide.swap(d.guide);std::swap(p.scene,d.scene);p.saved=d.saved;p.revision=d.batch.revision;p.sequence=d.batch.events.front().sequence;p.recall_required=false;++p.epoch;return true;
}
std::string CompanionRuntime::hint()const{
 const auto& p=*impl_;if(p.recall_required)return "Adam's memory waits for a clear point. F8: Recall.";
 if(p.saved.intent==GuideIntent::wait)return "Adam is waiting here. F6: Follow | F8: Recall.";
 if(p.guide&&p.guide->state().activity==GuideActivity::blocked)return "Adam is waiting for a clear route. F7: Wait | F8: Recall.";
 return "Adam is following. F7: Wait | F8: Recall.";
}
}
