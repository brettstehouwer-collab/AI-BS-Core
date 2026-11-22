#pragma once
#include <aibs/creator_payload.hpp>
#include <aibs/first_boot.hpp>
#include <array>
#include <set>

namespace aibs {
// Independent read-only projection protocol. No authoring/save commands exist.
struct CreatorViewportSnapshot {
 std::string snapshot_id;
 CreatorScope scope;
 std::string checkpoint_id;
 std::string selected_id;
 std::uint64_t revision=0;
 bool first_boot=false;
 World world;
};
inline CreatorViewportSnapshot decode_viewport_snapshot(std::span<const unsigned char> bytes) {
 using namespace creator_payload;
 creator_payload::detail::ensure(bytes.size()<=maximum_bytes,"Viewport snapshot exceeds 1 MiB");creator_payload::detail::Reader r{bytes};
 creator_payload::detail::ensure(r.number(4)==0x56424941&&r.number(2)==1,"Unsupported viewport snapshot");
 const auto mode=r.number(1);creator_payload::detail::ensure(mode<=1,"Unknown viewport projection");
 CreatorViewportSnapshot result;result.first_boot=mode==1;
 result.snapshot_id=r.text(true);creator_payload::detail::uuid(result.snapshot_id);
 result.scope.project=r.text(true);result.scope.branch=r.text(true);result.scope.world_id=r.text(true);creator_payload::detail::uuid(result.scope.world_id);
 result.checkpoint_id=r.text();creator_payload::detail::uuid(result.checkpoint_id,true);result.revision=r.number(8);
 result.selected_id=r.text();creator_payload::detail::uuid(result.selected_id,true);
 const auto count=r.number(4);creator_payload::detail::ensure(count<=10000,"Viewport entity limit");std::set<std::string> ids;
 for(std::uint64_t i=0;i<count;++i) {
  Entity entity;entity.id=r.text(true);entity.name=r.text();entity.persistent_id=r.text(true);creator_payload::detail::uuid(entity.persistent_id);
  creator_payload::detail::ensure(ids.insert(entity.persistent_id).second,"Duplicate viewport UUID");const auto fields=r.number(4);
  creator_payload::detail::ensure(fields<=64,"Viewport field limit");
  for(std::uint64_t j=0;j<fields;++j){auto key=r.text(true);auto value=r.real();creator_payload::detail::ensure(entity.fields.emplace(std::move(key),value).second,"Duplicate viewport field");}
  creator_payload::detail::ensure(result.world.emplace(entity.id,entity).second,"Duplicate viewport alias");
 }
 creator_payload::detail::ensure(result.selected_id.empty()||ids.contains(result.selected_id),"Selected viewport UUID is absent");
 creator_payload::detail::ensure(r.offset==bytes.size(),"Trailing viewport snapshot bytes");return result;
}
inline SceneSnapshot viewport_scene(const CreatorViewportSnapshot& snapshot) {
 if(snapshot.first_boot){
  if(snapshot.world.size()>512)throw std::invalid_argument("First Boot preview exceeds the bounded projection limit");
  auto scene=first_boot_scene(snapshot.world,snapshot.scope.world_id,snapshot.revision);
  for(auto& object:scene.objects)object.selectable=true;
  return scene;
 }
 SceneSnapshot scene{snapshot.scope.world_id,snapshot.revision,{}};
 for(const auto& [alias,entity]:snapshot.world) {
  (void)alias;
  constexpr std::array<const char*,6> keys{"x","y","z","half_x","half_y","half_z"};
  if(!std::all_of(keys.begin(),keys.end(),[&](const auto* key){return entity.fields.contains(key);}))continue;
  std::array<float,6> values{};
  for(std::size_t i=0;i<keys.size();++i) {
   const double value=entity.fields.at(keys[i]);
   if(!std::isfinite(value)||std::abs(value)>1000000||(i>=3&&(value<.001||value>10000)))throw std::invalid_argument("Viewport geometry is outside supported bounds");
   values[i]=static_cast<float>(value);
  }
  scene.objects.push_back({entity.persistent_id,entity.name,{values[0],values[1],values[2]},
   {values[3],values[4],values[5]},{.16f,.48f,.58f},.1f,true});
 }
 return scene;
}
}
