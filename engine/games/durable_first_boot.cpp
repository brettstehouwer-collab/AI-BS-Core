#include <aibs/durable_first_boot.hpp>
#include <aibs/gameplay_codec.hpp>
#include <aibs/legacy_import.hpp>
#include <algorithm>
#include <bit>
#include <cmath>
#include <limits>
#include <stdexcept>
#include <string_view>

namespace aibs {
namespace {
constexpr const char* node_type="firstboot.Node";
void require(bool value,const char* message) { if(!value) throw std::invalid_argument(message); }
const std::vector<FieldSchema>& numeric_fields() {
 static const std::vector<FieldSchema> fields={{"firstboot.kind",1,9},{"x",-200,200},{"y",-50,100},{"z",-200,200},
  {"half_x",.01,100},{"half_y",.01,100},{"half_z",.01,100},{"capacity",0,100}};
 return fields;
}
template<class T> const T& field(const ComponentRecord& record,const std::string& id) {
 const auto found=record.fields.find(id);require(found!=record.fields.end(),"First Boot node is missing a required field");
 const auto* value=std::get_if<T>(&found->second);require(value!=nullptr,"First Boot node field has the wrong type");return *value;
}
bool valid_text(const std::string& value) { return !value.empty() && value.size()<=4096 && value.find('\0')==std::string::npos; }
struct Node { ComponentRecord record;Entity entity;bool alive; };
using Nodes=std::map<std::string,Node>;
unsigned kind(const Node& node) { return static_cast<unsigned>(node.entity.fields.at("firstboot.kind")); }
Node node(const ComponentRecord& record) {
 (void)gameplay_codec::encode_component(record);
 require(record.type_id==node_type && record.version==1 && record.fields.size()==numeric_fields().size()+3,"Foreign First Boot component type, version or fields");
 Entity entity{field<std::string>(record,"alias"),field<std::string>(record,"name"),{},record.entity_id};
 require(valid_text(entity.id)&&valid_text(entity.name),"First Boot alias/name must be bounded nonempty text");
 for(const auto& rule:numeric_fields()) {
  const auto number=field<double>(record,rule.id);
  require(std::isfinite(number)&&number>=rule.minimum&&number<=rule.maximum,"First Boot number is outside its supported bounds");entity.fields.emplace(rule.id,number);
 }
 const auto type=entity.fields.at("firstboot.kind");require(std::floor(type)==type,"First Boot kind must be an integer");
 const auto alive=field<bool>(record,"alive");require(alive || type==static_cast<double>(FirstBootKind::relay),"Only relay identities can be tombstoned");
 return {record,std::move(entity),alive};
}
Nodes nodes(const GameplayStoreRecovery& snapshot,GameplayContext expected=GameplayContext::player_world) {
 (void)gameplay_codec::encode_scope(snapshot.scope);require((expected==GameplayContext::player_world||expected==GameplayContext::temporary_play)&&snapshot.scope.context==expected,"First Boot runtime context mismatch");
 require(snapshot.components.size()<=10000,"First Boot exceeds its component budget");Nodes result;std::set<std::string> aliases;std::size_t bytes=0;
 for(const auto& record:snapshot.components) {
  const auto encoded=gameplay_codec::encode_component(record);require(encoded.size()<=64*1024*1024-bytes,"First Boot exceeds its byte budget");bytes+=encoded.size();
  auto value=node(record);require(aliases.insert(value.entity.id).second,"First Boot aliases cannot be duplicated or recycled across tombstones");
  require(result.emplace(record.entity_id,std::move(value)).second,"Duplicate First Boot entity UUID");
 }
 return result;
}
World alive_world(const Nodes& values) {
 World world;for(const auto& [unused,value]:values) { (void)unused;if(value.alive) require(world.emplace(value.entity.id,value.entity).second,"Duplicate alive First Boot alias"); }return world;
}
void validate_topology(const GameplayStoreRecovery& snapshot,const Nodes& values,bool spawn) {
 const auto world=alive_world(values);const auto scene=first_boot_scene(world,snapshot.scope.world_id,snapshot.revision);
 (void)mesh_from_snapshot(scene);if(spawn) (void)first_boot_player(world,snapshot.scope.world_id,snapshot.revision);
}
bool exact(const ComponentRecord& left,const ComponentRecord& right) { return gameplay_codec::encode_component(left)==gameplay_codec::encode_component(right); }
bool same_number(double left,double right) { return std::bit_cast<std::uint64_t>(left)==std::bit_cast<std::uint64_t>(right); }
const Node& target(const Nodes& values,const std::string& id) {
 require(is_uuid(id),"First Boot target must be a persistent UUID");const auto found=values.find(id);require(found!=values.end(),"First Boot target does not exist");return found->second;
}
GameplayChangeBatch action(const GameplayStoreRecovery& before,ComponentRecord changed,SemanticPayload payload,
                           const std::string& source,std::string operation) {
 require(before.revision<std::numeric_limits<std::uint64_t>::max() && before.sequence<std::numeric_limits<std::uint64_t>::max(),"First Boot history head is exhausted");
 GameplayChangeBatch batch;batch.scope=before.scope;batch.operation_id=operation.empty()?source+"."+new_uuid():std::move(operation);
 batch.expected_revision=before.revision;batch.revision=before.revision+1;
 const auto id=changed.entity_id;batch.deltas.push_back({ComponentAction::upsert,std::move(changed)});
 SemanticEvent event;event.event_id=new_uuid();event.scope=before.scope;event.sequence=before.sequence+1;event.operation_id=batch.operation_id;
 event.subject_ids={id};event.source_revision=batch.revision;event.provenance={GameplayProvenance::gameplay_rule,source};event.payload=std::move(payload);batch.events.push_back(std::move(event));
 (void)gameplay_codec::encode_batch(batch);return batch;
}
GameplayStoreRecovery projected(const GameplayStoreRecovery& before,const GameplayChangeBatch& batch) {
 auto after=before;after.revision=batch.revision;after.sequence=batch.events.back().sequence;
 for(const auto& delta:batch.deltas) {
  auto found=std::find_if(after.components.begin(),after.components.end(),[&](const auto& value){return value.entity_id==delta.component.entity_id;});
  if(found==after.components.end()) after.components.push_back(delta.component);else *found=delta.component;
 }
 return after;
}
}
std::vector<ComponentSchema> durable_first_boot_schemas() {
 ComponentSchema schema{node_type,1,{{"alias",GameplayValueKind::text},{"name",GameplayValueKind::text},{"alive",GameplayValueKind::boolean}}};
 for(const auto& rule:numeric_fields()) schema.fields.push_back({rule.id,GameplayValueKind::number,true,rule.minimum,rule.maximum});return {std::move(schema)};
}
std::vector<ComponentRecord> durable_first_boot_components(const Entity& source) {
 require(source.fields.size()==numeric_fields().size(),"Original First Boot fields require an explicit compatible projection");
 ComponentRecord record{source.persistent_id,node_type,1,{{"alias",source.id},{"name",source.name},{"alive",true}}};
 for(const auto& [id,value]:source.fields) record.fields.emplace(id,value);(void)node(record);return {std::move(record)};
}
void durable_first_boot_validate_source(const CreatorSession& source) {
 for(const auto& [alias,entity]:source.world()) { require(alias==entity.id,"Original First Boot alias mismatch");(void)durable_first_boot_components(entity); }
 (void)mesh_from_snapshot(first_boot_scene(source));(void)first_boot_player(source);
}
GameplayStoreBaseline durable_first_boot_baseline(const CreatorSession& source) {
 durable_first_boot_validate_source(source);GameplayStoreBaseline baseline;
 for(const auto& [unused,entity]:source.world()) { (void)unused;auto records=durable_first_boot_components(entity);baseline.components.push_back(std::move(records.front())); }
 return baseline;
}
World durable_first_boot_world(const GameplayStoreRecovery& snapshot) {
 return durable_first_boot_world(snapshot,GameplayContext::player_world);
}
World durable_first_boot_world(const GameplayStoreRecovery& snapshot,GameplayContext expected) {const auto values=nodes(snapshot,expected);validate_topology(snapshot,values,false);return alive_world(values);}
SceneSnapshot durable_first_boot_scene(const GameplayStoreRecovery& snapshot) {
 const auto world=durable_first_boot_world(snapshot);return first_boot_scene(world,snapshot.scope.world_id,snapshot.revision);
}
SceneSnapshot durable_first_boot_scene(const GameplayStoreRecovery& snapshot,GameplayContext expected){const auto world=durable_first_boot_world(snapshot,expected);return first_boot_scene(world,snapshot.scope.world_id,snapshot.revision);}
PlayerController durable_first_boot_player(const GameplayStoreRecovery& snapshot) {
 const auto world=durable_first_boot_world(snapshot);return first_boot_player(world,snapshot.scope.world_id,snapshot.revision);
}
void durable_first_boot_validate(const GameplayStoreRecovery& snapshot) { const auto values=nodes(snapshot);validate_topology(snapshot,values,true); }
void durable_first_boot_validate(const GameplayStoreRecovery& snapshot,GameplayContext expected){const auto values=nodes(snapshot,expected);validate_topology(snapshot,values,true);}
std::set<std::string> durable_first_boot_imported_ids(const GameplayStore& archive) {
 const auto baseline=archive.baseline();if(!baseline || baseline->legacy_checkpoint.empty()) return {};
 const auto scope=archive.recover().scope;CreatorSession source(first_boot_schema(),scope.project_id,scope.branch_id);
 const auto restored=restore_imported_checkpoint(archive,source);require(restored.ok,restored.message.c_str());
 return source.known_entity_ids();
}
void durable_first_boot_rules(const GameplayStoreRecovery& before,const GameplayStoreRecovery& after,
                             const GameplayChangeBatch& batch,const std::set<std::string>& historical_ids) {
 durable_first_boot_rules(before,after,batch,historical_ids,GameplayContext::player_world);
}
void durable_first_boot_rules(const GameplayStoreRecovery& before,const GameplayStoreRecovery& after,
                             const GameplayChangeBatch& batch,const std::set<std::string>& historical_ids,GameplayContext expected_context) {
 (void)gameplay_codec::encode_batch(batch);
 require(before.scope==after.scope && before.scope==batch.scope && batch.expected_revision==before.revision && after.revision==batch.revision,
         "First Boot action belongs to a foreign scope or head");
 require(historical_ids.size()<=10000,"Imported identity registry exceeds its source budget");
 const auto old=nodes(before,expected_context),next=nodes(after,expected_context);validate_topology(before,old,false);
 require(!batch.deltas.empty() && batch.deltas.size()==batch.events.size() &&
         before.sequence<=std::numeric_limits<std::uint64_t>::max()-batch.events.size() && after.sequence==before.sequence+batch.events.size() &&
         batch.events.front().sequence==before.sequence+1,"First Boot actions require one matching outcome per changed node");
 std::map<std::string,const ComponentRecord*> changes;
 for(const auto& delta:batch.deltas) {
  require(delta.action==ComponentAction::upsert && delta.component.type_id==node_type,"First Boot identities must be retained as node tombstones");
  require(changes.emplace(delta.component.entity_id,&delta.component).second,"Duplicate changed First Boot node");
  const auto found=next.find(delta.component.entity_id);require(found!=next.end() && exact(found->second.record,delta.component),"First Boot candidate differs from its declared delta");
 }
 for(const auto& [id,value]:old) {
  const auto found=next.find(id);require(found!=next.end(),"First Boot history cannot erase an entity identity");
  if(!changes.contains(id)) require(exact(value.record,found->second.record),"Unchanged First Boot architecture was modified");
 }
 for(const auto& [id,value]:next) { (void)value;require(old.contains(id)||changes.contains(id),"Undeclared First Boot entity was introduced"); }
 std::set<std::string> described;
 for(const auto& event:batch.events) {
  require(event.subject_ids.size()==1 && changes.contains(event.subject_ids.front()) && described.insert(event.subject_ids.front()).second &&
          event.provenance.kind==GameplayProvenance::gameplay_rule,"First Boot outcome does not match a single changed node");
  const auto& id=event.subject_ids.front();const auto& changed=next.at(id);const auto found=old.find(id);
  if(const auto* repair=std::get_if<RepairOutcome>(&event.payload)) {
   require(event.provenance.source_id=="firstboot.repair.v1" && repair->entity_id==id && found!=old.end(),"Invalid First Boot repair provenance or target");
   const auto& previous=found->second;const auto capacity=previous.entity.fields.at("capacity");
   require(previous.alive && changed.alive && (kind(previous)==2||kind(previous)==6) && capacity<100 &&
           same_number(repair->before,capacity) && same_number(repair->after,100) && same_number(changed.entity.fields.at("capacity"),100),"Repair outcome contradicts actual before/after capacity");
   auto expected=previous.record;expected.fields["capacity"]=100.0;require(exact(expected,changed.record),"Repair cannot move, rename or replace existing architecture");
  } else if(const auto* construction=std::get_if<ConstructionOutcome>(&event.payload)) {
   require(construction->entity_id==id && kind(changed)==6,"Only relay construction/dismantling is supported");
   if(construction->built) {
    require(event.provenance.source_id=="firstboot.build.v1" && found==old.end() && !historical_ids.contains(id) && changed.alive,
            "Construction cannot recycle an imported, existing or retired entity UUID");
    require(changed.entity.id=="relay-"+id && changed.entity.name=="Built power relay" &&
            same_number(changed.entity.fields.at("capacity"),100) && same_number(changed.entity.fields.at("half_x"),static_cast<double>(.9f)) &&
            same_number(changed.entity.fields.at("half_y"),static_cast<double>(1.2f)) && same_number(changed.entity.fields.at("half_z"),static_cast<double>(.9f)),"New relay architecture does not match its supported recipe");
   } else {
    require(event.provenance.source_id=="firstboot.dismantle.v1" && found!=old.end() && found->second.alive && !changed.alive && kind(found->second)==6,
            "Dismantling requires a living relay and cannot revive or remove base architecture");
    auto expected=found->second.record;expected.fields["alive"]=false;require(exact(expected,changed.record),"Dismantling must preserve the relay's complete identity record");
   }
  } else require(false,"Unsupported First Boot semantic action");
 }
 try { validate_topology(after,next,true); }
 catch(const std::runtime_error& error) {
  if(std::string_view(error.what()).starts_with("No safe BS spawn was found"))
   throw std::invalid_argument("Action would leave no supported safe BS spawn; choose another placement.");
  throw;
 }
}
std::optional<Vec3> durable_first_boot_placement(const GameplayStoreRecovery& snapshot,Vec3 origin,Vec3 direction) {
 const auto finite=[](Vec3 value){return std::isfinite(value.x)&&std::isfinite(value.y)&&std::isfinite(value.z);};
 if(!finite(origin)||!finite(direction)) return {};
 const auto length=std::hypot(static_cast<double>(direction.x),static_cast<double>(direction.y),static_cast<double>(direction.z));
 if(length<=0) return {};const auto dy=static_cast<double>(direction.y)/length;if(dy>=0) return {};
 const auto world=durable_first_boot_world(snapshot);const Entity* board=nullptr;
 for(const auto& [unused,entity]:world){(void)unused;if(entity.fields.at("firstboot.kind")==1){board=&entity;break;}}
 require(board!=nullptr,"First Boot placement requires its board");
 const auto top=board->fields.at("y")+board->fields.at("half_y");const auto center_y=top+1.2;
 if(center_y<-50||center_y>100) return {};
 const auto distance=(top+1-static_cast<double>(origin.y))/dy;
 if(!std::isfinite(distance)||distance<=0||distance>=200) return {};
 const auto x=static_cast<double>(origin.x)+(static_cast<double>(direction.x)/length)*distance;
 const auto z=static_cast<double>(origin.z)+(static_cast<double>(direction.z)/length)*distance;
 if(!std::isfinite(x)||!std::isfinite(z)||x<-200||x>200||z<-200||z>200) return {};
 return Vec3{static_cast<float>(x),static_cast<float>(center_y),static_cast<float>(z)};
}
std::optional<GameplayChangeBatch> durable_first_boot_repair(const GameplayStoreRecovery& before,const std::string& id,std::string operation) {
 return durable_first_boot_repair(before,id,std::move(operation),GameplayContext::player_world);
}
std::optional<GameplayChangeBatch> durable_first_boot_repair(const GameplayStoreRecovery& before,const std::string& id,std::string operation,GameplayContext expected_context) {
 const auto values=nodes(before,expected_context);validate_topology(before,values,false);const auto& previous=target(values,id);
 require(previous.alive && (kind(previous)==2||kind(previous)==6),"Selected First Boot node is not repairable");
 const auto capacity=previous.entity.fields.at("capacity");if(capacity==100) return {};
 auto changed=previous.record;changed.fields["capacity"]=100.0;
 auto batch=action(before,std::move(changed),RepairOutcome{id,capacity,100},"firstboot.repair.v1",std::move(operation));
 durable_first_boot_rules(before,projected(before,batch),batch,{},expected_context);return batch;
}
GameplayChangeBatch durable_first_boot_build(const GameplayStoreRecovery& before,Vec3 position,std::string operation) {
 return durable_first_boot_build(before,position,std::move(operation),GameplayContext::player_world);
}
GameplayChangeBatch durable_first_boot_build(const GameplayStoreRecovery& before,Vec3 position,std::string operation,GameplayContext expected_context) {
 const auto values=nodes(before,expected_context);validate_topology(before,values,false);const auto id=new_uuid();
 Entity entity{"relay-"+id,"Built power relay",{{"firstboot.kind",6},{"x",position.x},{"y",position.y},{"z",position.z},
  {"half_x",.9f},{"half_y",1.2f},{"half_z",.9f},{"capacity",100}},id};
 auto record=durable_first_boot_components(entity).front();
 auto batch=action(before,std::move(record),ConstructionOutcome{id,true},"firstboot.build.v1",std::move(operation));
 durable_first_boot_rules(before,projected(before,batch),batch,{},expected_context);return batch;
}
std::optional<GameplayChangeBatch> durable_first_boot_dismantle(const GameplayStoreRecovery& before,const std::string& id,std::string operation) {
 return durable_first_boot_dismantle(before,id,std::move(operation),GameplayContext::player_world);
}
std::optional<GameplayChangeBatch> durable_first_boot_dismantle(const GameplayStoreRecovery& before,const std::string& id,std::string operation,GameplayContext expected_context) {
 const auto values=nodes(before,expected_context);validate_topology(before,values,false);const auto& previous=target(values,id);require(kind(previous)==6,"Only relays can be dismantled");
 if(!previous.alive) return {};auto changed=previous.record;changed.fields["alive"]=false;
 auto batch=action(before,std::move(changed),ConstructionOutcome{id,false},"firstboot.dismantle.v1",std::move(operation));
 durable_first_boot_rules(before,projected(before,batch),batch,{},expected_context);return batch;
}
DurableFirstBootGuidance durable_first_boot_guidance(const GameplayWorld& world,const GameplayStore& archive,std::size_t maximum) {
 require(maximum>0 && maximum<=8,"First Boot recall is bounded to 1..8 committed facts");const auto snapshot=world.snapshot();
 const auto original_state=archive.recover();require(original_state.scope==snapshot->scope,"Original evidence belongs to another gameplay scope");
 const auto values=nodes(*snapshot);validate_topology(*snapshot,values,false);const Node* core=nullptr;
 for(const auto& [unused,value]:values) { (void)unused;if(value.alive&&kind(value)==2) core=&value; }
 require(core!=nullptr,"First Boot guidance requires its core");DurableFirstBootGuidance result;
 result.authored_hint=core->entity.fields.at("capacity")==100
  ?"Authored hint: Core Node 01 is restored. Follow its powered connections."
  :"Authored hint: Core Node 01 still needs repair. Start with what still responds.";
 const auto status=world.state();const auto from=status.durable_revision>maximum?status.durable_revision-maximum:0;
 for(const auto& batch:world.read_batches(from,maximum)) {
  if(batch.revision>status.durable_revision) continue;
  for(const auto& event:batch.events) {
   std::string fact;
   if(const auto* repair=std::get_if<RepairOutcome>(&event.payload)) fact="repair "+repair->entity_id+" capacity "+std::to_string(repair->before)+" -> "+std::to_string(repair->after);
   else if(const auto* built=std::get_if<ConstructionOutcome>(&event.payload)) fact=std::string(built->built?"built relay ":"dismantled relay ")+built->entity_id;
   else fact=std::string(semantic_event_type(event))+" recorded";
   result.committed_facts.push_back("Committed gameplay: "+fact+" [revision "+std::to_string(batch.revision)+", event "+event.event_id+"]");
  }
 }
 if(result.committed_facts.size()>maximum) result.committed_facts.erase(result.committed_facts.begin(),result.committed_facts.end()-static_cast<std::ptrdiff_t>(maximum));
 std::reverse(result.committed_facts.begin(),result.committed_facts.end());
 const auto baseline=archive.baseline();
 if(baseline&&!baseline->legacy_checkpoint.empty()) {
  CreatorSession original(first_boot_schema(),original_state.scope.project_id,original_state.scope.branch_id);
  const auto restored=restore_imported_checkpoint(archive,original);require(restored.ok,restored.message.c_str());
  if(original.memory().events().empty()) result.original_evidence="Original baseline evidence: format-1 checkpoint retained; no edit records were present.";
  else {
   const auto& event=original.memory().events().back();
   result.original_evidence="Original baseline evidence (format-1): Imported edit record: "+
    (event.description.empty()?std::string("[no description supplied]"):event.description)+
    " [revision "+std::to_string(event.revision)+", operation "+event.operation+"]";
  }
 } else result.original_evidence="Original baseline evidence: authored foundation; no imported original checkpoint.";
 return result;
}
}
