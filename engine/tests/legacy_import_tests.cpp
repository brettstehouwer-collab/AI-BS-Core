#include <aibs/legacy_import.hpp>
#include <aibs/gameplay_codec.hpp>
#include <fstream>
#include <iostream>
#include <stdexcept>
using namespace aibs;
namespace {
void require(bool ok,const char* why) { if(!ok) throw std::runtime_error(why); }
std::vector<std::uint8_t> bytes(const std::filesystem::path& p) {
 std::ifstream f(p,std::ios::binary);return {std::istreambuf_iterator<char>(f),{}};
}
std::vector<ComponentSchema> components() { return {{"legacy.Source",1,{{"alias",GameplayValueKind::text},{"name",GameplayValueKind::text},{"capacity",GameplayValueKind::number,true,0,100}}}}; }
std::vector<ComponentRecord> adapt(const Entity& e) { return {{e.persistent_id,"legacy.Source",1,{{"alias",e.id},{"name",e.name},{"capacity",e.fields.at("capacity")}}}}; }
unsigned validator_calls=0;
std::string expected_world,expected_checkpoint;
std::uint64_t expected_revision=0;
std::filesystem::path expected_unopened_database;
void validate_captured_original(const CreatorSession& original) {
 ++validator_calls;
 require(original.world_id()==expected_world && original.checkpoint_id()==expected_checkpoint && original.revision()==expected_revision &&
         original.world().at("core").fields.at("capacity")==50,"validator receives the fully replayed captured original snapshot");
 require(!std::filesystem::exists(expected_unopened_database),"game validator must run before opening the destination database");
}
void require_game_topology(const CreatorSession& original) {
 ++validator_calls;
 require(original.world().contains("board") && original.world().contains("gpu"),"Original game is missing the mandatory board/GPU topology");
}
void original_validator_regressions(const std::filesystem::path& directory,const std::filesystem::path& source,
 const SchemaRegistry& schema,const CreatorSession& original,const std::vector<std::uint8_t>& original_bytes) {
 expected_world=original.world_id();expected_checkpoint=original.checkpoint_id();expected_revision=original.revision();validator_calls=0;
 expected_unopened_database=directory/"validated-original.db";bool adapter_called=false;
 const auto accepted=import_format1_checkpoint(source,expected_unopened_database,schema,"legacy-case","main",components(),[&](const Entity& input) {
  require(validator_calls==1,"captured original validator must precede every adapter invocation");adapter_called=true;return adapt(input);
 },{},validate_captured_original);
 require(accepted.ok && adapter_called && validator_calls==1 && bytes(source)==original_bytes,"successful original validator preserves source bytes");
 GameplayStore store(expected_unopened_database,accepted.scope,components());const auto preserved=store.baseline();
 require(preserved && preserved->legacy_checkpoint==original_bytes,"validated original is exactly the immutable checkpoint retained in SQLite");
 validator_calls=0;adapter_called=false;const auto rejected_database=directory/"invalid-game-topology.db";
 const auto rejected=import_format1_checkpoint(source,rejected_database,schema,"legacy-case","main",components(),[&](const Entity& input) {
  adapter_called=true;return adapt(input);
 },{},require_game_topology);
 require(!rejected.ok && validator_calls==1 && !adapter_called && !std::filesystem::exists(rejected_database) && bytes(source)==original_bytes &&
         rejected.message.find("mandatory board/GPU")!=std::string::npos,"invalid original game topology rejects before projection or database creation without changing source");
}
void import_boundary_regressions(const std::filesystem::path& directory,const std::filesystem::path& source,
 const SchemaRegistry& schema,const std::vector<std::uint8_t>& original_bytes,const GameplayScope& scope,const GameplayStoreBaseline& baseline) {
 unsigned failures=0;
 auto check=[&](const char* name,auto operation) {
  try { operation(); }
  catch(const std::exception& error) { ++failures;std::cerr<<"REGRESSION "<<name<<": "<<error.what()<<'\n'; }
 };
 check("adapter input mutation",[&] {
  const auto database=directory/"mutating-adapter.db";
  const auto result=import_format1_checkpoint(source,database,schema,"legacy-case","main",components(),[](const Entity& input) {
   auto& changed=const_cast<Entity&>(input);changed.persistent_id=new_uuid();return adapt(changed);
  });
  require(!result.ok&&!std::filesystem::exists(database)&&bytes(source)==original_bytes,
          "callback UUID mutation must reject before database creation and preserve source bytes");
 });
 for(unsigned kind=0;kind<3;++kind) check("projection preflight before DB open",[&,kind] {
  const auto database=directory/("invalid-projection-"+std::to_string(kind)+".db");
  const auto result=import_format1_checkpoint(source,database,schema,"legacy-case","main",components(),[kind](const Entity& input) {
   auto value=adapt(input);
   if(kind==0) value[0].fields["capacity"]=101.0;
   else if(kind==1) value[0].fields.erase("name");
   else value[0].type_id="unregistered.Component";
   return value;
  });
  require(!result.ok&&!std::filesystem::exists(database)&&bytes(source)==original_bytes,
          "invalid registered projection must not create destination metadata");
 });
 for(unsigned kind=0;kind<2;++kind) check("restore store scope",[&,kind] {
  auto foreign=scope;
  if(kind==0) foreign.project_id="other-project";else foreign.branch_id="other-branch";
  GameplayStore mismatched(directory/("foreign-scope-"+std::to_string(kind)+".db"),foreign,components());
  require(mismatched.seed(baseline).status==GameplayStoreStatus::committed,"scope regression fixture seeded");
  CreatorSession destination(schema,"legacy-case","main");
  require(destination.apply({"unrelated",0,{Create{{"unrelated","Existing destination",{{"capacity",3}}}}}}).ok,"destination regression fixture");
  const auto before=destination;
  const auto restored=restore_imported_checkpoint(mismatched,destination);
  require(!restored.ok&&destination.world_id()==before.world_id()&&destination.checkpoint_id()==before.checkpoint_id()&&
          destination.revision()==before.revision()&&destination.world()==before.world()&&destination.memory().events()==before.memory().events(),
          "store project/branch mismatch must leave destination identity, world, memory and head unchanged");
 });
 require(failures==0,"legacy importer boundary regressions failed");
}
}
int main() {
 const auto directory=std::filesystem::temp_directory_path()/("aibs-legacy-import-"+new_uuid());
 try {
  std::filesystem::create_directories(directory);
  SchemaRegistry schema;require(schema.add({"capacity",0,100}),"register original schema");
  CreatorSession original(schema,"legacy-case","main");
  require(original.project_id()=="legacy-case"&&original.branch_id()=="main","read-only session scope accessors match original identity");
  const Transaction create{"original-create",0,{Create{{"core","Original core",{{"capacity",0}}}}}};
  require(original.apply(create).ok,"create original core");const auto core=original.world().at("core").persistent_id;
  require(original.apply({"repair",1,{SetField{"core","capacity",50,core}}}).ok,"old repair");
  require(original.apply({"relay",2,{Create{{"relay","Original relay",{{"capacity",10}}}}}}).ok,"old relay");const auto relay=original.world().at("relay").persistent_id;
  require(original.apply({"remove",3,{Erase{"relay",relay}}}).ok&&original.undo().ok,"original history with redo available");
  const auto file=directory/"original.aibs",db=directory/"gameplay.db";
  require(CheckpointStore::save(file,original).ok,"publish original format1");const auto original_bytes=bytes(file);
  original_validator_regressions(directory,file,schema,original,original_bytes);
  const auto imported=import_format1_checkpoint(file,db,schema,"legacy-case","main",components(),adapt);
  require(imported.ok&&!imported.retry&&imported.source_revision==original.revision()&&imported.entities==2,"import validated old world into typed baseline");
  require(imported.scope.world_id==original.world_id()&&imported.checkpoint_id==original.checkpoint_id(),"import preserves world/head identity");
  require(bytes(file)==original_bytes,"import never modifies original checkpoint bytes");
  GameplayStore store(db,imported.scope,components());const auto baseline=store.baseline();
  require(baseline&&baseline->legacy_checkpoint==original_bytes&&store.recover().components.size()==2&&store.recover().revision==original.revision(),"SQLite atomically retains typed baseline and original evidence");
  import_boundary_regressions(directory,file,schema,original_bytes,imported.scope,*baseline);
  CreatorSession restored(schema,"legacy-case","main");
  require(restore_imported_checkpoint(store,restored).ok&&restored.world()==original.world()&&restored.memory().events()==original.memory().events()&&restored.checkpoint_id()==original.checkpoint_id(),"full source/history restored from DB evidence");
  const auto count=restored.memory().events().size();require(restored.apply(create).ok&&restored.memory().events().size()==count,"original operation receipt survives import");
  require(restored.redo().ok&&!restored.world().contains("relay"),"original redo survives import");
  require(!restored.apply({"reuse-retired",restored.revision(),{Create{{"stolen","Wrong incarnation",{{"capacity",1}},relay}}}}).ok,"retired identity protection survives import");
  require(restored.undo().ok&&restored.world().at("relay").persistent_id==relay,"original undo restores same UUID");
  const auto retry=import_format1_checkpoint(file,db,schema,"legacy-case","main",components(),adapt);require(retry.ok&&retry.retry&&bytes(file)==original_bytes,"exact import retry is idempotent");
  const auto same=import_format1_checkpoint(file,file,schema,"legacy-case","main",components(),adapt);require(!same.ok&&bytes(file)==original_bytes,"source and database cannot be the same file");
  const auto linked=directory/"same-file-link.db";std::filesystem::create_hard_link(file,linked);
  require(!import_format1_checkpoint(file,linked,schema,"legacy-case","main",components(),adapt).ok&&bytes(file)==original_bytes,
          "hard-linked source cannot become its own database destination");
  const auto invalid=directory/"invalid.aibs",unused=directory/"unused.db";{std::ofstream out(invalid);out<<"bad checkpoint";}
  require(!import_format1_checkpoint(invalid,unused,schema,"legacy-case","main",components(),adapt).ok&&!std::filesystem::exists(unused),"invalid source rejects before creating DB");
  require(!import_format1_checkpoint(file,directory/"bad-adapter.db",schema,"legacy-case","main",components(),[](const Entity& e){auto value=adapt(e);value[0].entity_id=new_uuid();return value;}).ok,"component projection cannot rewrite entity UUIDs");
  CreatorSession foreign(schema,"another-project","main");const auto before=foreign.world_id();
  require(!restore_imported_checkpoint(store,foreign).ok&&foreign.world_id()==before&&foreign.world().empty(),"foreign restore leaves destination unchanged");
  require(store.verify().ok,"imported durable baseline verifies");
  std::cout<<"PASS: original format1 import, exact evidence, UUIDs, receipts, undo/redo and source protection\n";
  return 0;
 } catch(const std::exception& e) { std::cerr<<"FAIL: "<<e.what()<<'\n';return 1; }
}
