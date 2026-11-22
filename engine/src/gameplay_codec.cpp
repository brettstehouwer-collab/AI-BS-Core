#include <aibs/gameplay_codec.hpp>
#include <algorithm>
#include <array>
#include <bit>
#include <cmath>
#include <set>
#include <stdexcept>
#include <string_view>
#include <type_traits>

namespace aibs::gameplay_codec {
namespace {
constexpr std::string_view batch_magic="AIBGBAT1",component_magic="AIBGCMP1",schemas_magic="AIBGSCH1",scope_magic="AIBGSCP1";
constexpr std::size_t identifier_bytes=256,text_bytes=4096;
void ensure(bool value,const char* message) { if(!value) throw std::invalid_argument(message); }
std::uint32_t family_version(std::size_t index) { return index==6?3u:index>=4?2u:1u; }
void valid_companion(const CompanionOutcome& value) {
 const auto anchor=[](const CompanionIntentValue& v){return std::isfinite(v.anchor_x)&&std::abs(v.anchor_x)<=1e6&&
  std::isfinite(v.anchor_y)&&std::abs(v.anchor_y)<=1e6&&std::isfinite(v.anchor_z)&&std::abs(v.anchor_z)<=1e6;};
 ensure(value.action>=CompanionAction::follow&&value.action<=CompanionAction::recall&&anchor(value.before)&&anchor(value.after),
        "Companion outcome requires a known action and finite bounded anchors");
 ensure((value.action!=CompanionAction::follow||value.after.follow)&&
        (value.action!=CompanionAction::wait||!value.after.follow)&&
        (value.action!=CompanionAction::recall||value.before.follow==value.after.follow),
        "Companion action does not match saved intent");
}
void identifier(const std::string& value,std::size_t maximum=identifier_bytes) {
 ensure(!value.empty() && value.size()<=maximum && value.find('\0')==std::string::npos,"Invalid gameplay identifier or source reference");
}
template<class E> void enumeration(E value,unsigned maximum) {
 const auto raw=static_cast<std::underlying_type_t<E>>(value);
 ensure(raw>=0 && static_cast<unsigned>(raw)<=maximum,"Unsupported gameplay enum");
}
void valid_scope(const GameplayScope& value) {
 identifier(value.project_id); identifier(value.branch_id);
 ensure(is_uuid(value.world_id) && is_uuid(value.timeline_id),"Invalid gameplay scope UUIDs"); enumeration(value.context,3);
}
struct Writer {
 Bytes bytes;
 explicit Writer(std::string_view magic,std::uint32_t version=1) {
  bytes.insert(bytes.end(),magic.begin(),magic.end()); number(version,4); number(0,4);
 }
 void number(std::uint64_t value,unsigned width=8) {
  ensure(width<=maximum_bytes-bytes.size(),"Gameplay envelope exceeds 4 MiB");
  for(unsigned i=0;i<width;++i) bytes.push_back(static_cast<std::uint8_t>(value>>(8*i)));
 }
 void string(const std::string& value,std::size_t maximum=text_bytes) {
  ensure(value.size()<=maximum && value.size()+4<=maximum_bytes-bytes.size(),"Gameplay string/envelope byte limit exceeded");
  number(value.size(),4); bytes.insert(bytes.end(),value.begin(),value.end());
 }
 void id(const std::string& value) { identifier(value); string(value,identifier_bytes); }
 void uuid(const std::string& value) { ensure(is_uuid(value),"Gameplay value requires a canonical UUID v4"); string(value,36); }
 void count(std::size_t value,std::size_t maximum,std::size_t minimum=0) {
  ensure(value>=minimum && value<=maximum,"Gameplay collection count outside supported bounds"); number(value,4);
 }
 void real(double value) { ensure(std::isfinite(value),"Nonfinite gameplay number"); number(std::bit_cast<std::uint64_t>(value)); }
 Bytes finish() {
  const auto payload=bytes.size()-16;
  for(unsigned i=0;i<4;++i) bytes[12+i]=static_cast<std::uint8_t>(payload>>(8*i));
  return std::move(bytes);
 }
};
struct Reader {
 std::span<const std::uint8_t> bytes;
 std::size_t position=0;
 std::uint32_t version=0;
 Reader(std::span<const std::uint8_t> value,std::string_view magic,std::uint32_t maximum_version=1):bytes(value) {
  ensure(bytes.size()>=16 && bytes.size()<=maximum_bytes,"Invalid gameplay envelope size");
  ensure(std::equal(magic.begin(),magic.end(),bytes.begin()),"Unexpected gameplay envelope type"); position=8;
  version=static_cast<std::uint32_t>(number(4));ensure(version>=1 && version<=maximum_version,"Unsupported gameplay envelope version");
  ensure(number(4)==bytes.size()-16,"Gameplay envelope length mismatch");
 }
 std::uint64_t number(unsigned width=8) {
  ensure(width<=bytes.size()-position,"Truncated gameplay envelope");
  std::uint64_t value=0;
  for(unsigned i=0;i<width;++i) value|=static_cast<std::uint64_t>(bytes[position++])<<(8*i);
  return value;
 }
 bool boolean() { const auto value=number(1); ensure(value<=1,"Noncanonical gameplay boolean"); return value!=0; }
 std::string string(std::size_t maximum=text_bytes) {
  const auto size=number(4);
  ensure(size<=maximum && size<=bytes.size()-position,"Gameplay string length exceeds bound or remaining envelope");
  const auto begin=bytes.begin()+static_cast<std::ptrdiff_t>(position);
  std::string value(begin,begin+static_cast<std::ptrdiff_t>(size)); position+=static_cast<std::size_t>(size); return value;
 }
 std::string id() { auto value=string(identifier_bytes); identifier(value); return value; }
 std::string uuid() { auto value=string(36); ensure(is_uuid(value),"Decoded gameplay UUID is invalid"); return value; }
 std::size_t count(std::size_t maximum,std::size_t minimum=0) {
  const auto value=number(4);
  ensure(value>=minimum && value<=maximum && value<=bytes.size()-position,"Decoded gameplay collection count exceeds bounds or remaining bytes");
  return static_cast<std::size_t>(value);
 }
 double real() { const auto value=std::bit_cast<double>(number()); ensure(std::isfinite(value),"Decoded nonfinite gameplay number"); return value; }
 void finish() const { ensure(position==bytes.size(),"Trailing gameplay payload bytes"); }
};
void scope(Writer& writer,const GameplayScope& value) {
 valid_scope(value);
 writer.id(value.project_id); writer.uuid(value.world_id); writer.id(value.branch_id); writer.uuid(value.timeline_id);
 writer.number(static_cast<unsigned>(value.context),1);
}
GameplayScope scope(Reader& reader) {
 GameplayScope value{reader.id(),reader.uuid(),reader.id(),reader.uuid()};
 value.context=static_cast<GameplayContext>(reader.number(1)); enumeration(value.context,3); return value;
}
void field_value(Writer& writer,const GameplayValue& value) {
 ensure(!value.valueless_by_exception(),"Gameplay value has no supported type"); writer.number(value.index(),1);
 std::visit([&](const auto& typed) {
  using T=std::decay_t<decltype(typed)>;
  if constexpr(std::is_same_v<T,bool>) writer.number(typed?1:0,1);
  else if constexpr(std::is_same_v<T,std::int64_t>) writer.number(std::bit_cast<std::uint64_t>(typed));
  else if constexpr(std::is_same_v<T,double>) writer.real(typed);
  else writer.string(typed);
 },value);
}
GameplayValue field_value(Reader& reader) {
 switch(reader.number(1)) {
 case 0:return reader.boolean();
 case 1:return std::bit_cast<std::int64_t>(reader.number());
 case 2:return reader.real();
 case 3:return reader.string();
 default:throw std::invalid_argument("Unsupported gameplay value type");
 }
}
void component(Writer& writer,const ComponentRecord& value) {
 writer.uuid(value.entity_id); writer.id(value.type_id); ensure(value.version!=0,"Component version cannot be zero"); writer.number(value.version,4);
 writer.count(value.fields.size(),64);
 for(const auto& [id,field]:value.fields) { writer.id(id); field_value(writer,field); }
}
ComponentRecord component(Reader& reader) {
 ComponentRecord value{reader.uuid(),reader.id()}; value.version=static_cast<std::uint32_t>(reader.number(4));
 ensure(value.version!=0,"Decoded component version cannot be zero"); const auto count=reader.count(64);
 std::string previous;
 for(std::size_t i=0;i<count;++i) {
  auto id=reader.id(); ensure(previous.empty() || previous<id,"Duplicate or noncanonical component field order"); previous=id;
  auto field=field_value(reader); ensure(value.fields.emplace(std::move(id),std::move(field)).second,"Duplicate component field");
 }
 return value;
}
const std::string& primary_subject(const SemanticPayload& payload) {
 return std::visit([](const auto& value)->const std::string& {
  using T=std::decay_t<decltype(value)>;
  if constexpr(std::is_same_v<T,RouteOutcome>) return value.route_id;
  else if constexpr(std::is_same_v<T,HazardOutcome>) return value.hazard_id;
  else if constexpr(std::is_same_v<T,QuestOutcome>) return value.quest_id;
  else return value.entity_id;
 },payload);
}
void payload(Writer& writer,const SemanticPayload& value) {
 ensure(!value.valueless_by_exception(),"Unsupported empty semantic payload"); writer.number(value.index(),1);
 writer.uuid(primary_subject(value));
 std::visit([&](const auto& typed) {
  using T=std::decay_t<decltype(typed)>;
  if constexpr(std::is_same_v<T,RepairOutcome>) {
   ensure(typed.before>=0 && typed.after>=typed.before && typed.after<=100,"Invalid repair outcome capacity");
   writer.real(typed.before); writer.real(typed.after);
  } else if constexpr(std::is_same_v<T,ConstructionOutcome>) writer.number(typed.built?1:0,1);
  else if constexpr(std::is_same_v<T,RouteOutcome>) writer.number(typed.traversed?1:0,1);
  else if constexpr(std::is_same_v<T,HazardOutcome>) writer.number(typed.survived?1:0,1);
  else if constexpr(std::is_same_v<T,MechanismOutcome>) {
   ensure(typed.before!=typed.after,"Unchanged mechanism outcome");writer.id(typed.attribute_id);
   writer.number(typed.before?1:0,1);writer.number(typed.after?1:0,1);
  } else if constexpr(std::is_same_v<T,QuestOutcome>) {
   enumeration(typed.before,4);enumeration(typed.after,4);
   ensure(typed.before!=typed.after || typed.before_step!=typed.after_step,"Unchanged quest outcome");
   ensure(typed.before_step.find('\0')==std::string::npos && typed.after_step.find('\0')==std::string::npos,"Invalid quest step");
   writer.number(static_cast<unsigned>(typed.before),1);writer.number(static_cast<unsigned>(typed.after),1);
   writer.string(typed.before_step,identifier_bytes);writer.string(typed.after_step,identifier_bytes);
  } else if constexpr(std::is_same_v<T,CompanionOutcome>) {
   valid_companion(typed);writer.number(static_cast<unsigned>(typed.action),1);
   for(const auto* intent:{&typed.before,&typed.after}) {
    writer.number(intent->follow?1:0,1);writer.real(intent->anchor_x);writer.real(intent->anchor_y);writer.real(intent->anchor_z);
   }
  }
 },value);
}
SemanticPayload payload(Reader& reader) {
 const auto kind=reader.number(1); ensure(kind<=6,"Unsupported semantic payload kind"); auto subject=reader.uuid();
 if(kind==0) { const auto before=reader.real(),after=reader.real(); ensure(before>=0 && after>=before && after<=100,"Invalid decoded repair capacity"); return RepairOutcome{std::move(subject),before,after}; }
 if(kind==4) {
  auto attribute=reader.id();const auto before=reader.boolean(),after=reader.boolean();ensure(before!=after,"Unchanged decoded mechanism outcome");
  return MechanismOutcome{std::move(subject),std::move(attribute),before,after};
 }
 if(kind==5) {
  const auto before=static_cast<QuestState>(reader.number(1)),after=static_cast<QuestState>(reader.number(1));enumeration(before,4);enumeration(after,4);
  auto before_step=reader.string(identifier_bytes),after_step=reader.string(identifier_bytes);
  ensure(before_step.find('\0')==std::string::npos && after_step.find('\0')==std::string::npos,"Invalid decoded quest step");
  ensure(before!=after || before_step!=after_step,"Unchanged decoded quest outcome");
  return QuestOutcome{std::move(subject),before,after,std::move(before_step),std::move(after_step)};
 }
 if(kind==6) {
  CompanionOutcome value;value.entity_id=std::move(subject);value.action=static_cast<CompanionAction>(reader.number(1));enumeration(value.action,2);
  for(auto* intent:{&value.before,&value.after}){intent->follow=reader.boolean();intent->anchor_x=reader.real();intent->anchor_y=reader.real();intent->anchor_z=reader.real();}
  valid_companion(value);return value;
 }
 const auto value=reader.boolean();
 if(kind==1) return ConstructionOutcome{std::move(subject),value};
 if(kind==2) return RouteOutcome{std::move(subject),value};
 return HazardOutcome{std::move(subject),value};
}
void event(Writer& writer,const SemanticEvent& value) {
 ensure(!value.payload.valueless_by_exception() && value.payload_version==family_version(value.payload.index()),"Unsupported semantic payload version");
 writer.uuid(value.event_id); writer.number(value.payload_version,4); scope(writer,value.scope);
 writer.number(value.sequence); writer.id(value.operation_id); writer.count(value.subject_ids.size(),64,1);
 std::set<std::string> subjects;
 for(const auto& subject:value.subject_ids) { writer.uuid(subject); ensure(subjects.insert(subject).second,"Duplicate semantic subject"); }
 writer.number(value.source_revision); writer.number(value.logical_tick.has_value()?1:0,1); if(value.logical_tick) writer.number(*value.logical_tick);
 enumeration(value.provenance.kind,2); writer.number(static_cast<unsigned>(value.provenance.kind),1);
 identifier(value.provenance.source_id,text_bytes); writer.string(value.provenance.source_id);
 ensure(value.result_phase==GameplayPhase::accepted,"Gameplay batch events must remain at accepted phase"); writer.number(0,1);
 ensure(!value.payload.valueless_by_exception() && subjects.contains(primary_subject(value.payload)),"Semantic payload target is not a subject");
 payload(writer,value.payload);
}
SemanticEvent event(Reader& reader) {
 SemanticEvent value; value.event_id=reader.uuid(); value.payload_version=static_cast<std::uint32_t>(reader.number(4));
 ensure(value.payload_version>=1 && value.payload_version<=3,"Unsupported decoded semantic payload version"); value.scope=scope(reader);
 value.sequence=reader.number(); value.operation_id=reader.id(); const auto subjects=reader.count(64,1);
 std::set<std::string> identities;
 for(std::size_t i=0;i<subjects;++i) { auto subject=reader.uuid(); ensure(identities.insert(subject).second,"Duplicate decoded semantic subject"); value.subject_ids.push_back(std::move(subject)); }
 value.source_revision=reader.number(); if(reader.boolean()) value.logical_tick=reader.number();
 value.provenance.kind=static_cast<GameplayProvenance>(reader.number(1)); enumeration(value.provenance.kind,2);
 value.provenance.source_id=reader.string(); identifier(value.provenance.source_id,text_bytes);
 ensure(reader.number(1)==0,"Decoded gameplay phase must be accepted"); value.payload=payload(reader);
 ensure(value.payload_version==family_version(value.payload.index()),"Decoded semantic family/version mismatch");
 ensure(identities.contains(primary_subject(value.payload)),"Decoded semantic payload target is not a subject"); return value;
}
void validate_batch(const GameplayChangeBatch& value) {
 std::uint32_t version=1;for(const auto& current:value.events)version=std::max(version,family_version(current.payload.index()));
 ensure(value.schema_version==version,"Unsupported or noncanonical gameplay batch schema"); valid_scope(value.scope); identifier(value.operation_id);
 ensure(value.expected_revision<std::numeric_limits<std::uint64_t>::max() && value.revision==value.expected_revision+1,"Invalid gameplay batch revision");
 ensure(value.deltas.size()<=256 && !value.events.empty() && value.events.size()<=64,"Invalid gameplay batch collection size");
 std::set<std::pair<std::string,std::string>> components; std::set<std::string> changed,events;
 for(const auto& delta:value.deltas) {
  enumeration(delta.action,1);
  ensure(is_uuid(delta.component.entity_id),"Invalid component delta UUID"); identifier(delta.component.type_id);
  ensure(components.emplace(delta.component.entity_id,delta.component.type_id).second,"Duplicate gameplay component delta"); changed.insert(delta.component.entity_id);
  ensure(delta.action!=ComponentAction::erase || delta.component.fields.empty(),"Component erasure cannot include replacement fields");
 }
 std::uint64_t previous=0;
 for(std::size_t i=0;i<value.events.size();++i) {
  const auto& current=value.events[i];
  ensure(is_uuid(current.event_id),"Invalid semantic event UUID");
  ensure(events.insert(current.event_id).second,"Duplicate gameplay event identity");
  ensure(current.scope==value.scope && current.operation_id==value.operation_id && current.source_revision==value.revision,"Gameplay event scope/operation/revision mismatch");
  ensure(current.sequence>0 && (i==0 || (previous<std::numeric_limits<std::uint64_t>::max() && current.sequence==previous+1)),"Gameplay semantic sequence is not contiguous"); previous=current.sequence;
  ensure(!current.payload.valueless_by_exception(),"Unsupported semantic payload");
  if(std::holds_alternative<RepairOutcome>(current.payload) || std::holds_alternative<ConstructionOutcome>(current.payload) || current.payload.index()>=4)
   ensure(changed.contains(primary_subject(current.payload)),"Repair/construction/mechanism/quest/companion outcome has no corresponding component delta");
 }
}
void schemas(Writer& writer,const std::vector<ComponentSchema>& values) {
 writer.count(values.size(),128,1);
 for(const auto& value:values) {
  identifier(value.type_id); ensure(value.version!=0 && !value.fields.empty() && value.fields.size()<=64,"Invalid schema version/field count");
  for(const auto& field:value.fields) identifier(field.id);
 }
 std::vector<const ComponentSchema*> ordered; ordered.reserve(values.size()); for(const auto& value:values) ordered.push_back(&value);
 std::sort(ordered.begin(),ordered.end(),[](const auto* a,const auto* b){return a->type_id<b->type_id || (a->type_id==b->type_id && a->version<b->version);});
 std::optional<std::pair<std::string,std::uint32_t>> previous;
 for(const auto* value:ordered) {
  const auto key=std::make_pair(value->type_id,value->version);
  ensure(!previous || *previous<key,"Duplicate component schema"); previous=key;
  writer.id(value->type_id); ensure(value->version!=0,"Component schema version cannot be zero"); writer.number(value->version,4); writer.count(value->fields.size(),64,1);
  std::vector<const GameplayFieldRule*> fields; fields.reserve(value->fields.size()); for(const auto& field:value->fields) fields.push_back(&field);
  std::sort(fields.begin(),fields.end(),[](const auto* a,const auto* b){return a->id<b->id;}); std::string previous_id;
  for(const auto* field:fields) {
   ensure(previous_id.empty() || previous_id<field->id,"Duplicate component schema field"); previous_id=field->id;
   writer.id(field->id); enumeration(field->kind,3); writer.number(static_cast<unsigned>(field->kind),1); writer.number(field->required?1:0,1);
   ensure(field->minimum<=field->maximum,"Inverted component numeric bounds"); writer.real(field->minimum); writer.real(field->maximum);
  }
 }
}
std::vector<ComponentSchema> schemas(Reader& reader) {
 const auto count=reader.count(128,1); std::vector<ComponentSchema> values;
 std::optional<std::pair<std::string,std::uint32_t>> previous;
 for(std::size_t i=0;i<count;++i) {
  ComponentSchema value; value.type_id=reader.id(); value.version=static_cast<std::uint32_t>(reader.number(4)); ensure(value.version!=0,"Decoded schema version cannot be zero");
  const auto key=std::make_pair(value.type_id,value.version); ensure(!previous || *previous<key,"Duplicate/noncanonical schema order"); previous=key;
  const auto count_fields=reader.count(64,1); std::string previous_id;
  for(std::size_t f=0;f<count_fields;++f) {
   GameplayFieldRule field; field.id=reader.id(); ensure(previous_id.empty() || previous_id<field.id,"Duplicate/noncanonical schema field order"); previous_id=field.id;
   field.kind=static_cast<GameplayValueKind>(reader.number(1)); enumeration(field.kind,3); field.required=reader.boolean();
   field.minimum=reader.real(); field.maximum=reader.real(); ensure(field.minimum<=field.maximum,"Inverted decoded numeric bounds"); value.fields.push_back(std::move(field));
  }
  values.push_back(std::move(value));
 }
 return values;
}
}
Bytes encode_scope(const GameplayScope& value) { Writer writer(scope_magic); scope(writer,value); return writer.finish(); }
GameplayScope decode_scope(std::span<const std::uint8_t> bytes) { Reader reader(bytes,scope_magic); auto value=scope(reader); reader.finish(); return value; }
Bytes encode_component(const ComponentRecord& value) { Writer writer(component_magic); component(writer,value); return writer.finish(); }
ComponentRecord decode_component(std::span<const std::uint8_t> bytes) { Reader reader(bytes,component_magic); auto value=component(reader); reader.finish(); return value; }
Bytes encode_schemas(const std::vector<ComponentSchema>& values) { Writer writer(schemas_magic); schemas(writer,values); return writer.finish(); }
std::vector<ComponentSchema> decode_schemas(std::span<const std::uint8_t> bytes) { Reader reader(bytes,schemas_magic); auto values=schemas(reader); reader.finish(); return values; }
Bytes encode_batch(const GameplayChangeBatch& value) {
 validate_batch(value); Writer writer(batch_magic,value.schema_version); writer.number(value.schema_version,4); scope(writer,value.scope);
 writer.id(value.operation_id); writer.number(value.expected_revision); writer.number(value.revision); writer.count(value.deltas.size(),256);
 for(const auto& delta:value.deltas) { writer.number(static_cast<unsigned>(delta.action),1); component(writer,delta.component); }
 writer.count(value.events.size(),64,1); for(const auto& current:value.events) event(writer,current); return writer.finish();
}
GameplayChangeBatch decode_batch(std::span<const std::uint8_t> bytes) {
 Reader reader(bytes,batch_magic,3); GameplayChangeBatch value; value.schema_version=static_cast<std::uint32_t>(reader.number(4));
 ensure(value.schema_version==reader.version,"Batch schema/envelope version mismatch"); value.scope=scope(reader); value.operation_id=reader.id();
 value.expected_revision=reader.number(); value.revision=reader.number(); const auto deltas=reader.count(256);
 for(std::size_t i=0;i<deltas;++i) {
  ComponentDelta delta; delta.action=static_cast<ComponentAction>(reader.number(1)); enumeration(delta.action,1);
  delta.component=component(reader); value.deltas.push_back(std::move(delta));
 }
 const auto events=reader.count(64,1); for(std::size_t i=0;i<events;++i) value.events.push_back(event(reader));
 reader.finish(); validate_batch(value); return value;
}
}
