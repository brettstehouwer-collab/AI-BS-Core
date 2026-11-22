#include <aibs/persistence.hpp>
#include <iostream>

int main(int argc, char** argv) {
 aibs::SchemaRegistry registry;
 if (!registry.add({"capacity", 0, 100})) return 1;
 aibs::CreatorSession session(registry, "first-boot", "main");
 const bool inspect = argc == 3 && std::string(argv[1]) == "--inspect";
 const bool checkpoint = argc == 3 && std::string(argv[1]) == "--checkpoint";
 if (argc != 1 && !inspect && !checkpoint) {
  std::cerr << "Usage: aibs_player [--checkpoint PATH | --inspect PATH]\n"; return 2;
 }
 std::filesystem::path path;
 if (inspect || checkpoint) {
  path = argv[2];
  if (inspect || std::filesystem::exists(path)) {
   const auto loaded = aibs::CheckpointStore::load(path, session);
   if (!loaded.ok) { std::cerr << loaded.message << '\n'; return 3; }
  }
 }
 std::cout << "AI-BS | Adam's Infinite-Brett Stehouwer Living Learning Memoir\n";
 std::cout << "Adam: I'm here. Start with what still responds.\n";
 if (!inspect) {
  if (!session.apply({"boot-node", 0, {aibs::Create{{"core-01", "Core Node 01", {{"capacity", 0}}}}}, "Built Core Node 01"}).ok) return 1;
  auto repair = session.apply({"repair-node", 1, {aibs::SetField{"core-01", "capacity", 75}}, "Restored Core Node 01 capacity"});
  if (!repair.ok) return 1;
 }
 if (!session.world().contains("core-01")) { std::cerr << "Checkpoint has no demo core node\n"; return 4; }
 std::cout << "Headless foundation demonstration: capacity=" << session.world().at("core-01").fields.at("capacity") << "\n";
 if (session.world().at("core-01").fields.at("capacity") > 0)
  std::cout << "Adam: That connection holds. We can build from here.\n";
 else std::cout << "Adam: This core still needs repair.\n";
 std::cout << "World UUID=" << session.world_id() << "\nEntity UUID=" << session.world().at("core-01").persistent_id << "\nAdam events=" << session.memory().events().size() << '\n';
 if (checkpoint) {
  const auto saved = aibs::CheckpointStore::save(path, session);
  if (!saved.ok) { std::cerr << saved.message << '\n'; return 5; }
  std::cout << "Checkpoint published: " << saved.checkpoint_id << '\n';
 } else std::cout << (inspect ? "Read-only checkpoint inspection; no changes published.\n" : "In-memory demonstration; use --checkpoint PATH to save.\n");
 return 0;
}
