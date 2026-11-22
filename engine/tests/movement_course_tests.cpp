#include <aibs/movement_course.hpp>
#include <aibs/persistence.hpp>
#include <cmath>
#include <filesystem>
#include <iostream>
#include <stdexcept>
using namespace aibs;
namespace { void require(bool ok, const char* why) { if (!ok) throw std::runtime_error(why); } }
int main() {
 const auto directory=std::filesystem::temp_directory_path()/("aibs-course-"+new_uuid());
 try {
  std::filesystem::create_directories(directory);
  CreatorSession session(movement_course_schema(),"movement-course","main");
  require(seed_movement_course(session).ok,"seed independent motherboard course");
  const auto original=session.world(); const auto events=session.memory().events();
  require(seed_movement_course(session).ok && session.world()==original && session.memory().events()==events,"seed retry preserves identities/history");
  const auto scene=movement_course_scene(session);
  require(scene.objects.size()>=15 && mesh_from_snapshot(scene).vertices.size()>=540,"authored motherboard obstacle surfaces exist");
  const auto ramp_id=session.world().at("ramp-20").persistent_id;
  bool inclined=false;
  for(const auto& object:scene.objects) if(object.persistent_id==ramp_id) inclined=std::abs(object.rotation.x)>.1f;
  require(inclined,"persisted quaternion drives inclined render/collision scene");
  const auto core=session.world().at("relay-core").persistent_id;
  require(restore_movement_course(session,core).ok,"course interaction applies a recorded repair");
  const auto revision=session.revision();
  require(restore_movement_course(session,core).ok && session.revision()==revision,"healthy repair is idempotent");
  require(!restore_movement_course(session,ramp_id).ok && session.revision()==revision,"surface target is not a repairable core");
  const auto old_mesh=mesh_from_snapshot(movement_course_scene(session));
  const float half_angle=-3.14159265359f/12;
  require(session.apply({"course.rotate",session.revision(),{SetField{"ramp-20","qx",std::sin(half_angle),ramp_id},SetField{"ramp-20","qw",std::cos(half_angle),ramp_id}},"Changed the course ramp to 30 degrees through the authoring SDK"}).ok,"editable source orientation is admitted");
  const auto changed_mesh=mesh_from_snapshot(movement_course_scene(session));
  bool changed=false;
  for(std::size_t i=0;i<old_mesh.vertices.size();++i) changed=changed||old_mesh.vertices[i].position!=changed_mesh.vertices[i].position;
  require(changed,"editing the persisted quaternion changes actual extracted geometry");
  const auto slot=directory/"course.aibs";
  require(CheckpointStore::save(slot,session).ok,"save course orientation and repair");
  CreatorSession restored(movement_course_schema(),"movement-course","main");
  require(CheckpointStore::load(slot,restored).ok,"reload course source");
  require(restored.world_id()==session.world_id() && restored.world()==session.world() && restored.memory().events()==session.memory().events(),"course restart preserves source IDs, quaternion and actual repair memory");
  require(mesh_from_snapshot(movement_course_scene(restored)).vertices.size()==mesh_from_snapshot(movement_course_scene(session)).vertices.size(),"restored geometry can be rebuilt");
  auto bad=restored;
  require(bad.apply({"bad.rotation",bad.revision(),{SetField{"ramp-20","qw",0,ramp_id}}}).ok,"generic authoring prepares malformed rotation fixture");
  bool rejected=false; try { (void)movement_course_scene(bad); } catch(const std::invalid_argument&) { rejected=true; }
  require(rejected,"game projection rejects malformed saved orientation");
  std::filesystem::remove_all(directory);
  std::cout << "PASS: independent motherboard course source, saved orientation, repair, restart and validation\n";
  return 0;
 } catch(const std::exception& error) {
  std::cerr << "FAIL: " << error.what() << '\n';
  std::filesystem::remove_all(directory); return 1;
 }
}
