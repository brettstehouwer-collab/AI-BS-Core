#include <aibs/engine.hpp>
#include <iostream>

int main() {
 aibs::SchemaRegistry schemas;
 if (!schemas.add({"capacity", 0, 100})) return 1;
 aibs::CreatorSession creator(schemas, "creator-example", "draft");
 const auto result = creator.apply({"place-node", 0, {aibs::Create{{"node-01", "Editable node", {{"capacity", 25}}}}}});
 if (!result.ok) { std::cerr << result.message << '\n'; return 1; }
 auto play = creator.start_play();
 play.at("node-01").fields["capacity"] = 0;
 if (creator.world().at("node-01").fields.at("capacity") != 25) return 1;
 if (!creator.undo().ok || !creator.world().empty()) return 1;
 if (!creator.redo().ok || creator.world().empty()) return 1;
 std::cout << "Creator CLI: grouped edits, isolated Play copy, undo and redo verified.\n";
 return 0;
}
