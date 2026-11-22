#include <aibs/creator_host.hpp>
#include <filesystem>
#include <iostream>
#include <stdexcept>

namespace {
using namespace aibs;
void require(bool condition,const char* message) { if(!condition) throw std::runtime_error(message); }
SchemaRegistry schemas() {
 SchemaRegistry registry;require(registry.add({"x",-100,100}),"register x");require(registry.add({"half_x",.1,10}),"register half_x");return registry;
}
CreatorSession authored() {
 CreatorSession session(schemas(),"generic-tools","main");
 require(session.apply({"seed",0,{Create{{"cube","Generic cube",{{"x",0},{"half_x",1}},new_uuid()}}},"Authored generic cube"}).ok,"seed generic document");return session;
}
void preview_is_private_and_grouped() {
 CreatorHost host(authored());const auto original=host.snapshot();const auto uuid=original->world.at("cube").persistent_id;bool assessed=false;
 const Transaction gesture{"move-and-resize",original->revision,{SetField{"cube","x",3,uuid},SetField{"cube","half_x",2,uuid}},"One inspector gesture"};
 const auto preview=host.preview(original->scope,gesture,[&](const auto& before,const auto& after,const auto&) {
  require(before.world.at("cube").fields.at("x")==0&&after.world.at("cube").fields.at("x")==3,"assessor sees actual immutable candidates");
  assessed=true;CreatorDependencyPreview result;result.render_rebuild=true;result.collision_rebuild=true;return result;
 });
 require(preview.status==CreatorHostStatus::prepared&&preview.change&&assessed,"private preview is assessed");
 require(host.snapshot()==original&&host.snapshot()->history.size()==1,"preview leaves live state/history unchanged");
 require(preview.change->snapshot()->world.at("cube").fields.at("half_x")==2,"immutable candidate groups edits");
 require(host.apply(preview.change).status==CreatorHostStatus::applied,"prepared candidate applies");
 require(host.snapshot()->revision==original->revision+1&&host.snapshot()->history.size()==2,"one gesture is one authored history item");
 require(host.snapshot()->world.at("cube").persistent_id==uuid,"editing retains UUID");
}
}
int main() {
 try { preview_is_private_and_grouped();std::cout<<"Creator host tests passed\n";return 0; }
 catch(const std::exception& error) { std::cerr<<error.what()<<'\n';return 1; }
}
