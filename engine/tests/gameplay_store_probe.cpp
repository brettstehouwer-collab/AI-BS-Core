#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <aibs/gameplay_store.hpp>
#include <chrono>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <thread>

using namespace aibs;
namespace {
void require(bool ok,const char* why) { if(!ok) throw std::runtime_error(why); }
std::string ascii(const wchar_t* input) {
 std::string out;for(;*input;++input) { require(*input>0&&*input<128,"Probe value must be ASCII");out+=static_cast<char>(*input); }return out;
}
struct Options { std::string step,world,timeline,entity,seed_event,repair_event;std::filesystem::path database,report; };
std::vector<ComponentSchema> schemas() { return {{"probe.Power",1,{{"capacity",GameplayValueKind::number,true,0,100}}}}; }
GameplayChangeBatch batch(const Options& options,const GameplayScope& scope,bool repair) {
 GameplayChangeBatch b;b.scope=scope;b.operation_id=repair?"durable.repair":"durable.seed";b.expected_revision=repair?1:0;b.revision=b.expected_revision+1;
 b.deltas.push_back({ComponentAction::upsert,{options.entity,"probe.Power",1,{{"capacity",repair?100.0:0.0}}}});
 SemanticEvent event;event.event_id=repair?options.repair_event:options.seed_event;event.scope=scope;event.sequence=b.revision;event.operation_id=b.operation_id;
 event.subject_ids={options.entity};event.source_revision=b.revision;event.logical_tick=repair?120:0;event.provenance={GameplayProvenance::gameplay_rule,"sqlite.process.proof.v1"};
 if(repair) event.payload=RepairOutcome{options.entity,0,100};else event.payload=ConstructionOutcome{options.entity,true};
 b.events.push_back(event);return b;
}
const char* status(GameplayStoreStatus s) {
 switch(s) { case GameplayStoreStatus::committed:return "committed";case GameplayStoreStatus::retry:return "retry";case GameplayStoreStatus::rejected:return "rejected";default:return "failed"; }
}
void report(const Options& options,GameplayStore& store,const char* result="none") {
 const auto recovered=store.recover();require(store.verify().ok,"Recovered store failed integrity/replay validation");
 double capacity=0;for(const auto& c:recovered.components) if(c.entity_id==options.entity) capacity=std::get<double>(c.fields.at("capacity"));
 std::ofstream out(options.report);
 out<<"{\"revision\":"<<recovered.revision<<",\"sequence\":"<<recovered.sequence<<",\"capacity\":"<<capacity
    <<",\"components\":"<<recovered.components.size()<<",\"commit_status\":\""<<result<<"\",\"events\":[";
 bool first=true;for(const auto& b:store.read_batches(0)) for(const auto& e:b.events) { if(!first)out<<',';first=false;out<<'"'<<e.event_id<<'"'; }
 out<<"]}";require(out.good(),"Could not publish process proof result");
}
}
int wmain(int argc,wchar_t** argv) {
 try {
  Options o;
  for(int i=1;i<argc;++i) {
   const std::wstring flag(argv[i]);require(i+1<argc,"Probe option needs a value");const auto* value=argv[++i];
   if(flag==L"--step")o.step=ascii(value);else if(flag==L"--database")o.database=value;else if(flag==L"--report")o.report=value;
   else if(flag==L"--world")o.world=ascii(value);else if(flag==L"--timeline")o.timeline=ascii(value);else if(flag==L"--entity")o.entity=ascii(value);
   else if(flag==L"--seed-event")o.seed_event=ascii(value);else if(flag==L"--repair-event")o.repair_event=ascii(value);else throw std::invalid_argument("Unknown probe option");
  }
  require(!o.database.empty()&&!o.report.empty()&&is_uuid(o.world)&&is_uuid(o.timeline)&&is_uuid(o.entity)&&is_uuid(o.seed_event)&&is_uuid(o.repair_event),"Incomplete process proof scope/paths");
  GameplayScope scope{"store-process-proof",o.world,o.step=="foreign"?"other":"main",o.timeline};
  GameplayStoreObserver observer;
  if(o.step=="before"||o.step=="after") observer=[&](GameplayStoreStage stage) {
   if(o.step=="before"&&stage==GameplayStoreStage::before_commit) ExitProcess(73);
   if(o.step=="after"&&stage==GameplayStoreStage::after_commit) ExitProcess(74);
  };
  GameplayStore store(o.database,scope,schemas(),observer);
  if(o.step=="inspect"||o.step=="foreign") { report(o,store);return 0; }
  if(o.step=="stale") {
   require(store.recover().revision==1,"Concurrent writer did not open the expected old head");
   auto ready=o.report;ready+=L".ready";{std::ofstream signal(ready);signal<<"opened revision1";require(signal.good(),"Cannot signal stale writer readiness");}
   auto go=o.report;go+=L".go";const auto deadline=std::chrono::steady_clock::now()+std::chrono::seconds(10);
   while(!std::filesystem::exists(go)&&std::chrono::steady_clock::now()<deadline) std::this_thread::sleep_for(std::chrono::milliseconds(10));
   require(std::filesystem::exists(go),"Concurrent writer did not receive its bounded resume signal");
   auto stale=batch(o,scope,true);stale.operation_id="stale.repair";stale.events[0].operation_id=stale.operation_id;stale.events[0].event_id=new_uuid();
   const auto result=store.commit(stale);require(result.status==GameplayStoreStatus::rejected,"Stale connection overwrote the committed head");report(o,store,status(result.status));return 0;
  }
  require(o.step=="seed"||o.step=="before"||o.step=="after"||o.step=="retry"||o.step=="conflict","Unknown process proof step");
  auto request=batch(o,scope,o.step!="seed");
  if(o.step=="conflict") { request.deltas[0].component.fields["capacity"]=80.0;request.events[0].payload=RepairOutcome{o.entity,0,80}; }
  const auto result=store.commit(request);
  if(o.step=="before"||o.step=="after") throw std::runtime_error("Requested process interruption did not occur");
  if(o.step=="seed")require(result.status==GameplayStoreStatus::committed,"Initial durable seed failed");
  if(o.step=="retry")require(result.status==GameplayStoreStatus::retry,"Lost-completion retry was not idempotent");
  if(o.step=="conflict")require(result.status==GameplayStoreStatus::rejected,"Conflicting retry was accepted");
  report(o,store,status(result.status));return 0;
 } catch(const std::exception& e) { std::cerr<<"SQLite process probe failed: "<<e.what()<<'\n';return 1; }
}
