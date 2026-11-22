#include <aibs/gameplay_codec.hpp>
#include <algorithm>
#include <array>
#include <bit>
#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>
using namespace aibs;
namespace gc=aibs::gameplay_codec;
namespace {
void require(bool ok,const char* message) { if(!ok) throw std::runtime_error(message); }
template<class F> void rejects(F action,const char* message) {
 bool rejected=false; try {action();} catch(const std::invalid_argument&) {rejected=true;}
 require(rejected,message);
}
GameplayScope scope() { return {"first-boot",new_uuid(),"main",new_uuid(),GameplayContext::player_world}; }
ComponentRecord component(const std::string& entity) {
 return {entity,"fixture.Component",1,{{"aa",std::numeric_limits<std::int64_t>::min()},
                                    {"bb",std::numeric_limits<std::int64_t>::max()},
                                    {"enabled",true},{"text",std::string("A\0B",3)},{"zero",-0.0}}};
}
GameplayChangeBatch batch() {
 GameplayChangeBatch value; value.scope=scope(); value.operation_id="repair-1"; value.revision=1;
 const auto entity=new_uuid();
 value.deltas.push_back({ComponentAction::upsert,component(entity)});
 SemanticEvent event; event.event_id=new_uuid(); event.scope=value.scope; event.sequence=42;
 event.operation_id=value.operation_id; event.subject_ids={entity}; event.source_revision=1; event.logical_tick=123;
 event.provenance={GameplayProvenance::gameplay_rule,"fixture.rule.v1"}; event.payload=RepairOutcome{entity,0,100};
 value.events.push_back(event);
 event.event_id=new_uuid(); event.sequence=43; event.payload=ConstructionOutcome{entity,true}; value.events.push_back(event);
 event.event_id=new_uuid(); event.sequence=44; event.payload=RouteOutcome{entity,true}; value.events.push_back(event);
 event.event_id=new_uuid(); event.sequence=45; event.logical_tick.reset(); event.payload=HazardOutcome{entity,false}; value.events.push_back(event);
 return value;
}
void put_u32(gc::Bytes& bytes,std::size_t position,std::uint32_t value) {
 for(unsigned i=0;i<4;++i) bytes.at(position+i)=static_cast<std::uint8_t>(value>>(8*i));
}
}
int main() {
 try {
  const auto original=batch(); const auto encoded=gc::encode_batch(original);
  require(encoded.size()<gc::maximum_bytes && gc::decode_batch(encoded)==original,"all typed batch values round-trip exactly");
  require(gc::encode_batch(gc::decode_batch(encoded))==encoded,"canonical batch bytes stable on round trip");
  const auto record=gc::decode_component(gc::encode_component(original.deltas[0].component));
  require(std::get<std::int64_t>(record.fields.at("aa"))==std::numeric_limits<std::int64_t>::min() &&
          std::get<std::int64_t>(record.fields.at("bb"))==std::numeric_limits<std::int64_t>::max(),"int64 limits retain exact bits");
  require(std::signbit(std::get<double>(record.fields.at("zero"))),"negative zero retains its IEEE bits");
  require(std::get<std::string>(record.fields.at("text")).size()==3,"typed text preserves embedded NUL bytes");
  require(gc::decode_scope(gc::encode_scope(original.scope))==original.scope,"scope round trip");
  std::vector<ComponentSchema> schemas={{"z.Type",2,{{"b",GameplayValueKind::boolean,false},{"a",GameplayValueKind::number,true,-0.0,100}}},
                                        {"a.Type",1,{{"integer",GameplayValueKind::integer}}}};
  const auto schema_bytes=gc::encode_schemas(schemas);
  std::reverse(schemas.begin(),schemas.end()); std::reverse(schemas.back().fields.begin(),schemas.back().fields.end());
  require(gc::encode_schemas(schemas)==schema_bytes,"schema registries canonicalize semantic ordering");
  require(gc::encode_schemas(gc::decode_schemas(schema_bytes))==schema_bytes,"canonical schema bytes round trip");
  for(std::size_t size=0;size<encoded.size();++size)
   rejects([&]{(void)gc::decode_batch(std::span(encoded).first(size));},"every truncated batch prefix rejected");
  for(std::size_t size=16;size<encoded.size();++size) {
   gc::Bytes hostile(encoded.begin(),encoded.begin()+static_cast<std::ptrdiff_t>(size)); put_u32(hostile,12,static_cast<std::uint32_t>(size-16));
   rejects([&]{(void)gc::decode_batch(hostile);},"internal truncation rejected even after attacker repairs envelope length");
  }
  auto bad=encoded; bad.push_back(0); rejects([&]{(void)gc::decode_batch(bad);},"extra envelope bytes rejected");
  bad=encoded; bad[0]^=1; rejects([&]{(void)gc::decode_batch(bad);},"wrong magic rejected");
  bad=encoded; put_u32(bad,8,2); rejects([&]{(void)gc::decode_batch(bad);},"future envelope version rejected");
  rejects([&]{(void)gc::decode_component(encoded);},"typed envelope cannot be reinterpreted as another record kind");
  auto invalid=original; invalid.schema_version=2; rejects([&]{(void)gc::encode_batch(invalid);},"future batch schema rejected");
  invalid=original; invalid.events[0].payload_version=2; rejects([&]{(void)gc::encode_batch(invalid);},"future semantic payload rejected");
  invalid=original; invalid.events[0].result_phase=GameplayPhase::durably_committed; rejects([&]{(void)gc::encode_batch(invalid);},"encoded acceptance cannot forge durable completion");
  invalid=original; invalid.events[1].sequence=99; rejects([&]{(void)gc::encode_batch(invalid);},"semantic sequence gaps rejected");
  invalid=original; invalid.events[0].scope.branch_id="other"; rejects([&]{(void)gc::encode_batch(invalid);},"cross-scope events rejected");
  invalid=original; invalid.events[0].source_revision=2; rejects([&]{(void)gc::encode_batch(invalid);},"foreign revision rejected");
  invalid=original; invalid.events[0].operation_id="other"; rejects([&]{(void)gc::encode_batch(invalid);},"foreign operation rejected");
  invalid=original; invalid.events[0].subject_ids.clear(); rejects([&]{(void)gc::encode_batch(invalid);},"zero subject count rejected");
  invalid=original; invalid.events[0].subject_ids.push_back(invalid.events[0].subject_ids[0]); rejects([&]{(void)gc::encode_batch(invalid);},"duplicate subjects rejected");
  invalid=original; invalid.events[1].event_id=invalid.events[0].event_id; rejects([&]{(void)gc::encode_batch(invalid);},"duplicate event UUID rejected");
  invalid=original; invalid.deltas.push_back(invalid.deltas.front()); rejects([&]{(void)gc::encode_batch(invalid);},"duplicate component delta rejected");
  invalid=original; invalid.events.clear(); rejects([&]{(void)gc::encode_batch(invalid);},"zero required event count rejected");
  auto field=record; field.fields["zero"]=std::numeric_limits<double>::infinity(); rejects([&]{(void)gc::encode_component(field);},"nonfinite double rejected");
  field=record; field.fields["text"]=std::string(4097,'x'); rejects([&]{(void)gc::encode_component(field);},"text over byte bound rejected");
  field=record; field.entity_id="bad"; rejects([&]{(void)gc::encode_component(field);},"malformed UUID rejected");
  auto corrupt_scope=gc::encode_scope(original.scope); corrupt_scope.back()=255;
  rejects([&]{(void)gc::decode_scope(corrupt_scope);},"unknown decoded enum rejected");
  auto corrupt_schemas=schema_bytes; put_u32(corrupt_schemas,16,0xffffffffu);
  rejects([&]{(void)gc::decode_schemas(corrupt_schemas);},"huge collection count rejected before allocation");
  put_u32(corrupt_schemas,16,0); rejects([&]{(void)gc::decode_schemas(corrupt_schemas);},"zero schema count rejected");
  auto component_bytes=gc::encode_component(record);
  const std::array<std::uint8_t,6> field_key{2,0,0,0,'b','b'};
  auto duplicate=std::search(component_bytes.begin(),component_bytes.end(),field_key.begin(),field_key.end());
  require(duplicate!=component_bytes.end(),"duplicate-field corruption fixture located");
  duplicate[4]='a'; duplicate[5]='a';
  rejects([&]{(void)gc::decode_component(component_bytes);},"duplicate decoded keys rejected without map overwrite");
  component_bytes=gc::encode_component(record);
  const auto fields_offset=16+4+record.entity_id.size()+4+record.type_id.size()+4;
  put_u32(component_bytes,fields_offset,0xffffffffu);
  rejects([&]{(void)gc::decode_component(component_bytes);},"huge decoded field count rejected");
  component_bytes=gc::encode_component(record);
  const std::string bool_key="enabled";
  auto boolean=std::search(component_bytes.begin(),component_bytes.end(),bool_key.begin(),bool_key.end());
  require(boolean!=component_bytes.end(),"boolean corruption fixture located"); boolean[bool_key.size()+1]=2;
  rejects([&]{(void)gc::decode_component(component_bytes);},"noncanonical boolean rejected instead of coerced to true");
  component_bytes=gc::encode_component(record);
  const auto nan_bits=std::bit_cast<std::uint64_t>(std::numeric_limits<double>::quiet_NaN());
  for(unsigned i=0;i<8;++i) component_bytes[component_bytes.size()-8+i]=static_cast<std::uint8_t>(nan_bits>>(8*i));
  rejects([&]{(void)gc::decode_component(component_bytes);},"nonfinite decoded floating-point bits rejected");
  auto wire_gap=encoded;
  const auto& event_id=original.events[1].event_id;
  const auto occurrence=std::search(wire_gap.begin(),wire_gap.end(),event_id.begin(),event_id.end());
  require(occurrence!=wire_gap.end(),"semantic sequence corruption fixture located");
  const auto sequence_offset=static_cast<std::size_t>(occurrence-wire_gap.begin())+36+4+(gc::encode_scope(original.scope).size()-16);
  for(unsigned i=0;i<8;++i) wire_gap[sequence_offset+i]=static_cast<std::uint8_t>(std::uint64_t{44}>>(8*i));
  rejects([&]{(void)gc::decode_batch(wire_gap);},"semantic sequence validation also applies to malicious wire input");
  auto many=encoded;
  const auto delta_offset=16+4+(gc::encode_scope(original.scope).size()-16)+4+original.operation_id.size()+16;
  put_u32(many,delta_offset,257);
  rejects([&]{(void)gc::decode_batch(many);},"decoded delta count limit enforced before allocation");
  auto bad_rule=schemas; bad_rule[0].fields[0].kind=static_cast<GameplayValueKind>(99);
  rejects([&]{(void)gc::encode_schemas(bad_rule);},"unknown schema field type rejected");
  auto wrong_enum=original; wrong_enum.scope.context=static_cast<GameplayContext>(99);
  rejects([&]{(void)gc::encode_batch(wrong_enum);},"unknown input enum rejected");
  auto exact_tick=original; exact_tick.events[0].logical_tick=std::numeric_limits<std::uint64_t>::max();
  require(gc::decode_batch(gc::encode_batch(exact_tick)).events[0].logical_tick==exact_tick.events[0].logical_tick,
          "unsigned logical tick preserves all 64 bits");
  auto oversized=original; oversized.deltas.clear();
  for(unsigned index=0;index<17;++index) {
   ComponentRecord large{new_uuid(),"large.Component",1,{}};
   for(unsigned f=0;f<64;++f) large.fields.emplace("field-"+std::to_string(f),std::string(4096,'x'));
   oversized.deltas.push_back({ComponentAction::upsert,std::move(large)});
  }
  const auto target=oversized.deltas.front().component.entity_id;
  for(auto& value:oversized.events) { value.subject_ids={target}; value.payload=RouteOutcome{target,true}; }
  rejects([&]{(void)gc::encode_batch(oversized);},"encoder hard byte limit applies across many individually valid records");
  gc::Bytes huge(gc::maximum_bytes+1,0); rejects([&]{(void)gc::decode_batch(huge);},"oversized envelope rejected");
  std::cout<<"PASS: canonical bounded typed gameplay binary envelopes, exact values and hostile-input rejection\n";
  return 0;
 }catch(const std::exception& error){std::cerr<<"FAIL: "<<error.what()<<'\n';return 1;}
}
