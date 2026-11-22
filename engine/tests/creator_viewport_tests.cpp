#include <aibs/creator_viewport.hpp>
#include <aibs/creator_payload.hpp>
#include <iostream>
#include <stdexcept>

namespace {
void require(bool value,const char* message) {if(!value)throw std::runtime_error(message);}
std::vector<unsigned char> fixture(bool missing=false) {
 aibs::creator_payload::detail::Writer w;
 w.number(0x56424941,4);w.number(1,2);w.number(0,1);
 w.text("11111111-1111-4111-8111-111111111111");w.text("BS workshop");w.text("main");
 w.text("22222222-2222-4222-8222-222222222222");w.text("");w.number(7,8);w.text("");w.number(1,4);
 w.text("relay");w.text("Relay");w.text("33333333-3333-4333-8333-333333333333");w.number(missing?5:6,4);
 for(const auto& [key,value]:std::vector<std::pair<std::string,double>>{{"half_x",1},{"half_y",1},{"half_z",1},{"x",0},{"y",0},{"z",0}}) {
  if(missing&&key=="z")continue;w.text(key);w.real(value);
 }
 return w.data;
}
}
int main() {
 try {
  const auto bytes=fixture();const auto snapshot=aibs::decode_viewport_snapshot(bytes);
  require(snapshot.scope.project=="BS workshop"&&snapshot.revision==7,"scope/revision decode");
  const auto scene=aibs::viewport_scene(snapshot);
  require(scene.world_id==snapshot.scope.world_id&&scene.objects.size()==1,"project actual authoritative geometry");
  const auto hit=aibs::pick_scene(scene,{0,0,-5},{0,0,1});
  require(hit&&hit->persistent_id==snapshot.world.at("relay").persistent_id,"pick actual persistent UUID");
  for(std::size_t i=0;i<bytes.size();++i) {
   bool rejected=false;try {(void)aibs::decode_viewport_snapshot(std::span(bytes).first(i));}catch(const std::exception&) {rejected=true;}
   require(rejected,"truncated snapshot accepted");
  }
  auto trailing=bytes;trailing.push_back(0);bool rejected=false;
  try {(void)aibs::decode_viewport_snapshot(trailing);}catch(const std::exception&) {rejected=true;}
  require(rejected,"trailing snapshot bytes accepted");
  require(aibs::viewport_scene(aibs::decode_viewport_snapshot(fixture(true))).objects.empty(),"incomplete transform is not invented");
  auto invalid=snapshot;invalid.world.at("relay").fields["half_x"]=-1;rejected=false;
  try {(void)aibs::viewport_scene(invalid);}catch(const std::exception&) {rejected=true;}
  require(rejected,"invalid render bounds accepted");
  aibs::CreatorSession seeded(aibs::first_boot_schema(),"BS","main");require(aibs::seed_first_boot(seeded).ok,"native hardware seed");
  aibs::CreatorViewportSnapshot hardware;hardware.scope={"BS","main",seeded.world_id()};hardware.first_boot=true;hardware.world=seeded.world();hardware.revision=seeded.revision();
  const auto motherboard=aibs::viewport_scene(hardware);
  require(motherboard.objects.size()>hardware.world.size(),"native composite hardware projection reused");
  require(std::all_of(motherboard.objects.begin(),motherboard.objects.end(),[](const auto& object){return object.selectable;}),"authoring can pick board and traces too");
  std::cout<<"Viewport projection, UUID picking, every truncation and invalid geometry passed\n";return 0;
 }catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}
}
