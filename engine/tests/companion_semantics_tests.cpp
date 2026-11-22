#include <aibs/gameplay_codec.hpp>
#include <aibs/gameplay_world.hpp>
#include "fixtures/semantic_v1_fixture.hpp"
#include "fixtures/semantic_v1_golden.hpp"
#include "fixtures/semantic_v2_golden.hpp"
#include <algorithm>
#include <bit>
#include <cmath>
#include <filesystem>
#include <iostream>
#include <limits>
#include <stdexcept>
using namespace aibs;
namespace gc=aibs::gameplay_codec;
namespace fs=std::filesystem;
namespace {
std::size_t checks=0;
void check(bool value,const char* message){if(!value)throw std::runtime_error(message);++checks;}
template<class F>void rejects(F action,const char* message){bool rejected=false;try{action();}catch(const std::invalid_argument&){rejected=true;}check(rejected,message);}
const std::string companion="33333333-3333-4333-8333-333333333333";
ComponentRecord record(const CompanionIntentValue& value){return {companion,"fixture.Companion",1,{{"follow",value.follow},{"anchor_x",value.anchor_x},{"anchor_y",value.anchor_y},{"anchor_z",value.anchor_z}}};}
std::vector<ComponentSchema> registry(){return {{"fixture.Companion",1,{{"follow",GameplayValueKind::boolean},{"anchor_x",GameplayValueKind::number,true,-1e6,1e6},{"anchor_y",GameplayValueKind::number,true,-1e6,1e6},{"anchor_z",GameplayValueKind::number,true,-1e6,1e6}}},{"fixture.State",1,{{"capacity",GameplayValueKind::number,true,0,100},{"count",GameplayValueKind::integer},{"open",GameplayValueKind::boolean},{"stage",GameplayValueKind::text},{"zero",GameplayValueKind::number}}}};}
GameplayChangeBatch sample(CompanionAction action,CompanionIntentValue before,CompanionIntentValue after){
 auto batch=semantic_v1_fixture();batch.schema_version=3;batch.deltas={{ComponentAction::upsert,record(after)}};
 auto event=batch.events.front();event.payload_version=3;event.provenance={GameplayProvenance::player_input,"fixture.adam.explicit-control"};event.payload=CompanionOutcome{companion,action,before,after};batch.events={event};return batch;
}
void rejected_by_both(const GameplayChangeBatch& batch,const char* message){
 rejects([&]{(void)gc::encode_batch(batch);},message);GameplayAdmission ledger(batch.scope,registry());
 check(ledger.reserve(batch,[](const auto&){return true;}).status==AdmissionStatus::rejected,message);
 check(ledger.state().accepted_revision==0&&ledger.state().accepted_sequence==0,"Rejected companion cannot advance semantic head");
}
void u32(gc::Bytes& bytes,std::size_t offset,std::uint32_t value){for(unsigned n=0;n<4;++n)bytes.at(offset+n)=static_cast<unsigned char>(value>>(n*8));}
void u64(gc::Bytes& bytes,std::size_t offset,std::uint64_t value){for(unsigned n=0;n<8;++n)bytes.at(offset+n)=static_cast<unsigned char>(value>>(n*8));}
GameplayChangeBatch step(GameplayChangeBatch batch,std::uint64_t revision){batch.operation_id="companion.step."+std::to_string(revision);batch.expected_revision=revision-1;batch.revision=revision;auto& e=batch.events.front();e.event_id=new_uuid();e.operation_id=batch.operation_id;e.sequence=revision;e.source_revision=revision;return batch;}
void durable(const fs::path& base){
 const auto folder=base/("companion-semantic-"+new_uuid());check(fs::create_directory(folder),"Create a unique owned companion proof directory");
 const auto path=folder/"world.sqlite";const auto scope=semantic_v1_fixture().scope;
 const CompanionIntentValue initial{true,1,2,3},waiting{false,4,2,5},recalled{false,-4,2,-5};
 const auto wait=step(sample(CompanionAction::wait,initial,waiting),1);
 const auto recall=step(sample(CompanionAction::recall,waiting,recalled),2);
 const auto follow=step(sample(CompanionAction::follow,recalled,{true,-4,2,-5}),3);
 {
  GameplayStore store(path,scope,registry());GameplayStoreBaseline baseline;baseline.components={record(initial)};
  check(store.seed(baseline).status==GameplayStoreStatus::committed,"Seed independent companion baseline");
  check(store.commit(wait).status==GameplayStoreStatus::committed,"Explicit Wait actually commits");
  check(store.commit(wait).status==GameplayStoreStatus::retry,"Durable exact Wait retry is idempotent");
  auto collision=wait;std::get<CompanionOutcome>(collision.events.front().payload).before.anchor_x=9;
  check(store.commit(collision).status==GameplayStoreStatus::rejected,"Companion retry with changed before anchor rejects");
  check(store.commit(recall).status==GameplayStoreStatus::committed,"Explicit Recall has its own semantic receipt");
  check(store.verify().ok,"Companion durable history validates");
 }
 {
  GameplayStore store(path,scope,registry());const auto restored=store.recover();
  check(restored.revision==2&&restored.sequence==2&&restored.components==std::vector<ComponentRecord>{record(recalled)},"Reopen reconstructs exact durable waiting intent/anchor");
  const auto saved=store.lookup_batch(recall.operation_id);check(saved&&gameplay_batch_exact(*saved,recall),"Reopen preserves exact Recall event, without repair/quest fabrication");
  check(store.commit(recall).status==GameplayStoreStatus::retry,"Fresh process can retry exact companion receipt");
 }
 {
  GameplayWorld world(path,scope,registry());const auto before=world.snapshot();auto prepared=world.prepare(follow);
  check(prepared.status==GameplayPrepareStatus::prepared&&world.snapshot()==before,"Follow preparation does not publish pose/intent");
  check(world.publish(prepared.change).ok,"Prepared Follow publishes through actual worker");
  check(world.close().ok&&world.state().durable_sequence==3,"Actual worker drains companion event to SQLite");
 }
 {
  GameplayStore store(path,scope,registry());const auto restored=store.recover();
  check(restored.revision==3&&restored.sequence==3&&restored.components==std::vector<ComponentRecord>{record({true,-4,2,-5})},"Follow state survives another independent owner");
  auto same=step(sample(CompanionAction::recall,{true,-4,2,-5},{true,-4,2,-5}),4);
  check(store.commit(same).status==GameplayStoreStatus::committed,"Explicit Recall may rematerialize without changing saved anchor");
  check(store.read_batches(0).size()==4&&store.verify().ok,"All explicit choices remain separate ordered semantic events");
 }
 const auto failed_path=folder/"failed-commit.sqlite";bool fail=false;
 {
  GameplayStore store(failed_path,scope,registry(),[&](GameplayStoreStage stage){if(fail&&stage==GameplayStoreStage::before_commit)throw std::runtime_error("Injected companion commit failure");});
  GameplayStoreBaseline baseline;baseline.components={record(initial)};
  check(store.seed(baseline).status==GameplayStoreStatus::committed,"Seed rollback test before enabling injected fault");
  fail=true;check(store.commit(wait).status==GameplayStoreStatus::failed,"Failed companion COMMIT never acknowledges durability");
  const auto unchanged=store.recover();check(unchanged.revision==0&&unchanged.sequence==0&&unchanged.components==baseline.components&&!store.lookup_batch(wait.operation_id),"Failed commit atomically preserves intent, semantic head and retry registry");
 }
 {
  GameplayStore store(failed_path,scope,registry());check(store.verify().ok&&store.commit(wait).status==GameplayStoreStatus::committed,"Restart after failed companion commit accepts the original exact choice");
 }
 // Retain proof databases for inspection; no real save or original media is opened.
 std::cout<<"Owned durable proof: "<<folder.string()<<'\n';
}
}
int main(int argc,char** argv){try{
 check(argc<=2,"Usage: companion_semantics_tests [EXISTING_OWNED_OUTPUT_DIRECTORY]");
 const auto base=argc==2?fs::absolute(argv[1]):fs::temp_directory_path();check(fs::is_directory(base),"Owned proof parent exists");
 const auto legacy=semantic_v1_fixture();const auto old=gc::encode_batch(legacy);
 check(std::equal(old.begin(),old.end(),semantic_v1_golden.begin(),semantic_v1_golden.end()),"All original v1 bytes remain identical");
 auto legacy_v2=legacy;legacy_v2.schema_version=2;auto v2_event=legacy_v2.events.front();v2_event.payload_version=2;
 v2_event.payload=MechanismOutcome{companion,"open",false,true};legacy_v2.events={v2_event};const auto v2_bytes=gc::encode_batch(legacy_v2);
 check(std::equal(v2_bytes.begin(),v2_bytes.end(),semantic_v2_golden.begin(),semantic_v2_golden.end()),"All prechange v2 bytes remain identical");
 check(gameplay_batch_exact(legacy_v2,gc::decode_batch(semantic_v2_golden)),"Old v2 receipt decodes without migration or byte rewriting");
 const CompanionIntentValue following{true,-0.0,2,3},waiting{false,4,2,5};
 const auto wait=sample(CompanionAction::wait,following,waiting);
 const auto follow=sample(CompanionAction::follow,waiting,following);
 const auto recall=sample(CompanionAction::recall,waiting,{false,-4,2,7});
 for(const auto& batch:{follow,wait,recall,sample(CompanionAction::recall,following,following)}){
  check(batch.events.front().payload.index()==6&&std::string(semantic_event_type(batch.events.front()))=="companion.outcome","Companion is appended with distinct honest family name");
  const auto bytes=gc::encode_batch(batch);check(bytes.at(8)==3&&bytes.at(16)==3,"Companion uses explicit envelope/schema3");
  const auto restored=gc::decode_batch(bytes);check(gameplay_batch_exact(batch,restored)&&gc::encode_batch(restored)==bytes,"Companion codec preserves canonical bytes and signed zero");
  GameplayAdmission owner(batch.scope,registry());check(owner.reserve(batch,[](const auto&){return true;}).status==AdmissionStatus::accepted,"Explicit companion action admitted");
  check(owner.reserve(batch,[](const auto&){return true;}).status==AdmissionStatus::retry,"Companion exact retry retains identity");
  check(owner.state().visible_revision==0&&owner.state().durable_revision==0,"Companion admission does not fabricate visibility/durability");
  for(std::size_t size=0;size<bytes.size();++size)rejects([&]{(void)gc::decode_batch(std::span(bytes).first(size));},"Every truncated companion prefix rejects");
  for(std::size_t size=16;size<bytes.size();++size){gc::Bytes truncated(bytes.begin(),bytes.begin()+static_cast<std::ptrdiff_t>(size));u32(truncated,12,static_cast<std::uint32_t>(size-16));rejects([&]{(void)gc::decode_batch(truncated);},"Repaired envelope length cannot hide companion truncation");}
 }
 for(unsigned version:{1u,2u,4u}){auto bad=wait;bad.schema_version=version;rejected_by_both(bad,"Companion rejects wrong batch version");bad=wait;bad.events.front().payload_version=version;rejected_by_both(bad,"Companion rejects wrong event version");}
 auto bad=legacy;bad.schema_version=3;rejected_by_both(bad,"Legacy-only batch cannot be silently promoted to3");
 bad=legacy;bad.schema_version=3;auto old_event=bad.events.front();old_event.payload_version=2;old_event.payload=MechanismOutcome{companion,"open",false,true};bad.events={old_event};rejected_by_both(bad,"V2-only batch cannot be silently promoted to3");
 bad=wait;bad.deltas.clear();rejected_by_both(bad,"Companion requires a same-batch world delta");
 bad=wait;bad.events.front().subject_ids={new_uuid()};rejected_by_both(bad,"Companion primary target must be a validated subject");
 for(auto action:{static_cast<CompanionAction>(-1),static_cast<CompanionAction>(3)}){bad=wait;std::get<CompanionOutcome>(bad.events.front().payload).action=action;rejected_by_both(bad,"Unknown companion action rejects");}
 bad=follow;std::get<CompanionOutcome>(bad.events.front().payload).after.follow=false;rejected_by_both(bad,"Follow cannot store Wait intent");
 bad=wait;std::get<CompanionOutcome>(bad.events.front().payload).after.follow=true;rejected_by_both(bad,"Wait cannot store Follow intent");
 bad=recall;std::get<CompanionOutcome>(bad.events.front().payload).after.follow=true;rejected_by_both(bad,"Recall cannot silently alter saved intent");
 for(const double value:{std::numeric_limits<double>::quiet_NaN(),std::numeric_limits<double>::infinity(),-std::numeric_limits<double>::infinity(),1000000.01,-1000000.01})for(unsigned index=0;index<6;++index){
  bad=wait;auto& out=std::get<CompanionOutcome>(bad.events.front().payload);auto& intent=index<3?out.before:out.after;switch(index%3){case 0:intent.anchor_x=value;break;case 1:intent.anchor_y=value;break;default:intent.anchor_z=value;break;}rejected_by_both(bad,"All six companion anchor fields have finite world bounds");
 }
 auto bounds=sample(CompanionAction::recall,{true,-1e6,1e6,-0.0},{true,1e6,-1e6,0});check(gameplay_batch_exact(bounds,gc::decode_batch(gc::encode_batch(bounds))),"Inclusive coordinate bounds and signed zero remain exact");
 auto zero=sample(CompanionAction::recall,{true,0,0,0},{true,0,0,0});auto negative=zero;std::get<CompanionOutcome>(negative.events.front().payload).before.anchor_x=-0.0;
 check(zero==negative&&!gameplay_batch_exact(zero,negative),"Retry identity compares companion anchor bits, not float value equality");
 GameplayAdmission identity(zero.scope,registry());check(identity.reserve(zero,[](const auto&){return true;}).status==AdmissionStatus::accepted&&identity.reserve(negative,[](const auto&){return true;}).status==AdmissionStatus::rejected,"Changed signed-zero anchor cannot reuse an operation ID");
 auto bytes=gc::encode_batch(wait);const auto payload_at=bytes.size()-92;
 for(unsigned version:{1u,2u,4u}){auto changed=bytes;u32(changed,8,version);rejects([&]{(void)gc::decode_batch(changed);},"Companion decoded envelope version must match its inner schema");u32(changed,16,version);rejects([&]{(void)gc::decode_batch(changed);},"Companion cannot be disguised as an old or unknown matching envelope/schema");}
 for(const auto offset:{41u,42u,67u}){auto corrupt=bytes;corrupt.at(payload_at+offset)=255;rejects([&]{(void)gc::decode_batch(corrupt);},"Decoded action/bools reject noncanonical bytes");}
 auto corrupt=bytes;corrupt.at(payload_at)=7;rejects([&]{(void)gc::decode_batch(corrupt);},"Unknown future family rejects");
 corrupt=bytes;u64(corrupt,payload_at+43,std::bit_cast<std::uint64_t>(std::numeric_limits<double>::quiet_NaN()));rejects([&]{(void)gc::decode_batch(corrupt);},"Decoded nonfinite companion anchor rejects");
 corrupt=bytes;u64(corrupt,payload_at+84,std::bit_cast<std::uint64_t>(1000001.));rejects([&]{(void)gc::decode_batch(corrupt);},"Decoded out-of-bounds companion anchor rejects");
 corrupt=bytes;corrupt.push_back(0);rejects([&]{(void)gc::decode_batch(corrupt);},"Trailing companion bytes reject");
 auto mixed=legacy;mixed.schema_version=3;mixed.deltas.push_back(wait.deltas.front());auto event=wait.events.front();event.event_id=new_uuid();event.sequence=5;mixed.events.push_back(event);
 event.event_id=new_uuid();event.sequence=6;event.payload_version=2;event.payload=MechanismOutcome{companion,"open",false,true};mixed.events.push_back(event);
 check(gameplay_batch_exact(mixed,gc::decode_batch(gc::encode_batch(mixed))),"One v3 envelope retains v1/v2/v3 payload versions together");GameplayAdmission mixed_owner(mixed.scope,registry());check(mixed_owner.reserve(mixed,[](const auto&){return true;}).status==AdmissionStatus::accepted,"Mixed old/new family batch admitted canonically");
 durable(base);
 std::cout<<"PASS "<<checks<<" companion semantic codec/admission/worker/recovery checks\n";return 0;
 }catch(const std::exception& error){std::cerr<<"FAIL after "<<checks<<" checks: "<<error.what()<<'\n';return 1;}}
