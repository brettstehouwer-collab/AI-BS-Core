#include <aibs/gameplay_codec.hpp>
#include "fixtures/semantic_v1_fixture.hpp"
#include "fixtures/semantic_v1_golden.hpp"
#include <algorithm>
#include <bit>
#include <iostream>
#include <stdexcept>
using namespace aibs;
namespace gc=aibs::gameplay_codec;
void require(bool value,const char* message) { if(!value) throw std::runtime_error(message); }
template<class F> void rejects(F action,const char* message) {
 bool rejected=false;try {action();}catch(const std::invalid_argument&) {rejected=true;}require(rejected,message);
}
GameplayChangeBatch mechanism() {
 auto batch=semantic_v1_fixture();batch.schema_version=2;
 auto event=batch.events.front();event.payload_version=2;
 event.payload=MechanismOutcome{event.subject_ids.front(),"open",false,true};
 batch.events={event};return batch;
}
GameplayChangeBatch quest() {
 auto batch=mechanism();batch.events.front().payload=QuestOutcome{batch.events.front().subject_ids.front(),QuestState::offered,QuestState::active,"offer","repair_lamp"};return batch;
}
std::vector<ComponentSchema> registry() {
 return {{"fixture.State",1,{{"capacity",GameplayValueKind::number,true,0,100},{"count",GameplayValueKind::integer},
          {"open",GameplayValueKind::boolean},{"stage",GameplayValueKind::text},{"zero",GameplayValueKind::number}}}};
}
void rejected_by_both(const GameplayChangeBatch& batch,const char* message) {
 rejects([&]{(void)gc::encode_batch(batch);},message);
 GameplayAdmission ledger(batch.scope,registry());
 require(ledger.reserve(batch,[](const auto&){return true;}).status==AdmissionStatus::rejected,message);
 require(ledger.state().accepted_revision==0,"rejection cannot advance owner head");
}
void put_u32(gc::Bytes& bytes,std::size_t at,std::uint32_t value) {
 for(unsigned i=0;i<4;++i) bytes.at(at+i)=static_cast<std::uint8_t>(value>>(i*8));
}
int main() {
 try {
  const auto old=semantic_v1_fixture();const auto old_bytes=gc::encode_batch(old);
  require(std::equal(old_bytes.begin(),old_bytes.end(),semantic_v1_golden.begin(),semantic_v1_golden.end()),"SDK0.7 batch bytes must remain identical");
  require(gameplay_batch_exact(old,gc::decode_batch(semantic_v1_golden)),"old saved batch exact decode including signed zero and integer limits");
  for(const auto& batch:{mechanism(),quest()}) {
   const auto bytes=gc::encode_batch(batch);
   require(bytes.at(8)==2 && bytes.at(16)==2,"v2 batch has v2 envelope and inner schema");
   require(gameplay_batch_exact(batch,gc::decode_batch(bytes)),"new outcome roundtrip exact");
   require(gc::encode_batch(gc::decode_batch(bytes))==bytes,"v2 canonical bytes stable");
   GameplayAdmission ledger(batch.scope,registry());const auto targets=[](const auto&){return true;};
   require(ledger.reserve(batch,targets).status==AdmissionStatus::accepted,"new payload admitted");
   require(ledger.reserve(batch,targets).status==AdmissionStatus::retry,"new payload exact retry");
   auto conflict=batch;conflict.events.front().provenance.source_id+="changed";
   require(ledger.reserve(conflict,targets).status==AdmissionStatus::rejected,"v2 conflicting retry rejected");
   require(ledger.state().visible_revision==0 && ledger.state().durable_revision==0,"acceptance is not visibility/durability");
   for(std::size_t size=0;size<bytes.size();++size)
    rejects([&]{(void)gc::decode_batch(std::span(bytes).first(size));},"every truncated v2 prefix rejected");
   for(std::size_t size=16;size<bytes.size();++size) {
    gc::Bytes hostile(bytes.begin(),bytes.begin()+static_cast<std::ptrdiff_t>(size));put_u32(hostile,12,static_cast<std::uint32_t>(size-16));
    rejects([&]{(void)gc::decode_batch(hostile);},"v2 repaired outer length cannot hide truncation");
   }
   auto corrupt=bytes;put_u32(corrupt,8,1);rejects([&]{(void)gc::decode_batch(corrupt);},"v2 in v1 envelope rejected");
   corrupt=bytes;put_u32(corrupt,16,1);rejects([&]{(void)gc::decode_batch(corrupt);},"v1 in v2 envelope rejected");
   corrupt=bytes;put_u32(corrupt,8,3);rejects([&]{(void)gc::decode_batch(corrupt);},"unknown envelope rejected");
   corrupt=bytes;corrupt.push_back(0);rejects([&]{(void)gc::decode_batch(corrupt);},"trailing v2 bytes rejected");
  }
  auto mixed=old;mixed.schema_version=2;auto extra=quest().events.front();extra.event_id=new_uuid();extra.sequence=5;mixed.events.push_back(extra);
  require(gameplay_batch_exact(gc::decode_batch(gc::encode_batch(mixed)),mixed),"mixed legacy and v2 payloads retain family versions");
  GameplayAdmission mixed_owner(mixed.scope,registry());require(mixed_owner.reserve(mixed,[](const auto&){return true;}).status==AdmissionStatus::accepted,"mixed batch admitted");
  auto bad=old;bad.schema_version=2;rejected_by_both(bad,"old-only v2 noncanonical upgrade rejected");
  bad=mechanism();bad.schema_version=1;rejected_by_both(bad,"new payload cannot use old batch");
  bad=mechanism();bad.events.front().payload_version=1;rejected_by_both(bad,"new family requires payload v2");
  bad=old;bad.events.front().payload_version=2;rejected_by_both(bad,"legacy family retains payload v1");
  bad=mechanism();bad.schema_version=3;rejected_by_both(bad,"future batch rejected");
  bad=mechanism();bad.deltas.clear();rejected_by_both(bad,"mechanism requires same-batch primary delta");
  bad=quest();bad.deltas.clear();rejected_by_both(bad,"quest requires same-batch primary delta");
  bad=mechanism();std::get<MechanismOutcome>(bad.events.front().payload).before=true;rejected_by_both(bad,"unchanged mechanism rejected");
  for(const auto& attribute:{std::string{},std::string(257,'a'),std::string("a\0b",3)}) {
   bad=mechanism();std::get<MechanismOutcome>(bad.events.front().payload).attribute_id=attribute;rejected_by_both(bad,"invalid attribute rejected");
  }
  bad=quest();auto& same=std::get<QuestOutcome>(bad.events.front().payload);same.after=same.before;same.after_step=same.before_step;rejected_by_both(bad,"unchanged quest rejected");
  bad=quest();std::get<QuestOutcome>(bad.events.front().payload).after=static_cast<QuestState>(255);rejected_by_both(bad,"unknown quest enum rejected");
  bad=quest();std::get<QuestOutcome>(bad.events.front().payload).before=static_cast<QuestState>(-1);rejected_by_both(bad,"negative quest enum rejected");
  for(const auto& step:{std::string(257,'s'),std::string("s\0t",3)}) {
   bad=quest();std::get<QuestOutcome>(bad.events.front().payload).after_step=step;rejected_by_both(bad,"invalid quest step rejected");
  }
  auto loop=quest();auto& outcome=std::get<QuestOutcome>(loop.events.front().payload);outcome.before=outcome.after=QuestState::active;outcome.before_step="pencil";outcome.after_step="hub";
  require(gc::decode_batch(gc::encode_batch(loop))==loop,"quest loops allowed when actual step changes");
  outcome.before_step.clear();outcome.after_step.clear();outcome.after=QuestState::completed;
  require(gc::decode_batch(gc::encode_batch(loop))==loop,"empty optional steps allowed for state transition");
  auto corrupt=gc::encode_batch(mechanism());corrupt.back()=2;rejects([&]{(void)gc::decode_batch(corrupt);},"noncanonical mechanism bool rejected");
  corrupt=gc::encode_batch(mechanism());corrupt.at(corrupt.size()-2)=2;rejects([&]{(void)gc::decode_batch(corrupt);},"noncanonical mechanism before bool rejected");
  corrupt=gc::encode_batch(quest());
  const auto q=std::get<QuestOutcome>(quest().events.front().payload);
  const auto state_at=corrupt.size()-(2+4+q.before_step.size()+4+q.after_step.size());
  corrupt.at(state_at+1)=255;rejects([&]{(void)gc::decode_batch(corrupt);},"decoded unknown quest state rejected");
  corrupt=gc::encode_batch(quest());corrupt.at(state_at-41)=6;rejects([&]{(void)gc::decode_batch(corrupt);},"decoded future payload kind rejected");
  corrupt=old_bytes;put_u32(corrupt,8,2);put_u32(corrupt,16,2);
  rejects([&]{(void)gc::decode_batch(corrupt);},"rewriting both v1 version words cannot create canonical v2");
  require(std::string(semantic_event_type(mechanism().events.front()))=="mechanism.outcome" &&
          std::string(semantic_event_type(quest().events.front()))=="quest.outcome","new families have distinct semantic names");
  std::cout<<"PASS: old0.7 golden compatibility, semantic v2 roundtrip/admission/malformed/version bounds\n";return 0;
 }catch(const std::exception& error) {std::cerr<<"FAIL: "<<error.what()<<'\n';return 1;}
}
