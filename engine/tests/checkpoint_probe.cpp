#include <aibs/persistence.hpp>
#include <cstdlib>
#include <filesystem>
#include <iostream>
#include <string>
using namespace aibs;
int main(int argc, char** argv) {
 if (argc < 3) return 2;
 SchemaRegistry schema; schema.add({"capacity", 0, 100});
 CreatorSession session(schema, "first-boot", "main");
 const std::filesystem::path path(argv[2]);
 const std::string mode(argv[1]);
 if (mode == "seed") {
  if (!session.apply({"build", 0, {Create{{"core", "Core", {{"capacity", 10}}}}}, "Built Core Node 01"}).ok) return 3;
  if (!CheckpointStore::save(path, session).ok) return 4;
 } else {
  const auto loaded = CheckpointStore::load(path, session);
  if (!loaded.ok) { std::cerr << loaded.message; return 5; }
  if (mode == "repair" || mode == "crash-before" || mode == "crash-after" || mode == "transient") {
   const Transaction operation = mode == "transient"
    ? Transaction{"transient", session.revision(), {Create{{"temporary", "Temporary", {{"capacity", 11}}}}, Erase{"temporary"}}, "Placed then removed a temporary node"}
    : Transaction{"repair", session.revision(), {SetField{"core", "capacity", 75}}, "Restored Core Node 01"};
   if (!session.apply(operation).ok) return 6;
   SaveObserver observer = nullptr;
   if (mode == "crash-before") observer = [](SaveStage stage) noexcept { if (stage == SaveStage::before_publish) std::_Exit(91); };
   if (mode == "crash-after") observer = [](SaveStage stage) noexcept { if (stage == SaveStage::after_publish) std::_Exit(92); };
   const auto saved = CheckpointStore::save(path, session, observer);
   if (!saved.ok) { std::cerr << saved.message; return 7; }
  } else if (mode == "verify") {
   if (argc != 5) return 8;
   if (session.world().at("core").fields.at("capacity") != std::stod(argv[3])) return 9;
   if (session.memory().events().size() != static_cast<std::size_t>(std::stoul(argv[4]))) return 10;
  } else return 11;
 }
 std::cout << session.world_id() << ' ' << session.world().at("core").persistent_id << ' ' << session.revision() << '\n';
 return 0;
}
