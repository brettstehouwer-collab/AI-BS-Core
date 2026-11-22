#include <aibs/movement_course.hpp>
#include <cmath>
#include <stdexcept>

namespace aibs {
namespace {
constexpr float pi=3.14159265358979323846f;
double field(const Entity& entity,const char* key) {
 const auto found=entity.fields.find(key);
 if (found==entity.fields.end() || !std::isfinite(found->second)) throw std::invalid_argument("Incomplete/nonfinite movement-course source");
 return found->second;
}
Entity make(std::string id,std::string name,unsigned kind,Vec3 center,Vec3 half,float slope=0) {
 const float angle=-slope*pi/180;
 return {std::move(id),std::move(name),{{"course.kind",kind},{"x",center.x},{"y",center.y},{"z",center.z},
  {"hx",half.x},{"hy",half.y},{"hz",half.z},{"qx",std::sin(angle/2)},{"qy",0},{"qz",0},{"qw",std::cos(angle/2)},{"state",0}}};
}
}
SchemaRegistry movement_course_schema() {
 SchemaRegistry schema;
 for (const auto& f:std::vector<FieldSchema>{{"course.kind",1,7},{"x",-200,200},{"y",-50,100},{"z",-200,200},
   {"hx",.01,100},{"hy",.01,100},{"hz",.01,100},{"qx",-1,1},{"qy",-1,1},{"qz",-1,1},{"qw",-1,1},{"state",0,100}})
  if (!schema.add(f)) throw std::logic_error("Course schema registration failed");
 return schema;
}
Result seed_movement_course(CreatorSession& session) {
 if (!session.world().empty()) {
  try { (void)movement_course_scene(session); }
  catch(const std::invalid_argument& e) { return {false,e.what(),session.revision()}; }
  return {true,"Motherboard course already initialized",session.revision()};
 }
 std::vector<Edit> edits;
 auto add=[&](Entity e) { edits.push_back(Create{std::move(e)}); };
 add(make("board","Motherboard traversal foundation",1,{0,-1,0},{47,1,36}));
 for(int i=0;i<3;++i) {
  const float height=.3f*static_cast<float>(i+1);
  add(make("step-"+std::to_string(i+1),"Socket stair "+std::to_string(i+1),2,{-18,height/2,-25+2*static_cast<float>(i)},{2,height/2,1}));
 }
 add(make("step-deck","Raised socket deck",2,{-18,.6f,-18},{2,.6f,2}));
 const float a=20*pi/180, steep=60*pi/180;
 const float rise=12*std::sin(a), ramp_center=6*std::sin(a)-.1f*std::cos(a);
 const float high_z=-15+6*std::cos(a)-.1f*std::sin(a);
 add(make("ramp-20","20 degree CPU access ramp",3,{0,ramp_center,-15},{2.5f,.1f,6},20));
 add(make("cpu-deck","CPU inspection platform",2,{0,rise/2,high_z+3},{2.5f,rise/2,3}));
 add(make("ramp-60","60 degree steep-surface barrier",4,{18,6*std::sin(steep)-.1f*std::cos(steep),-15},{2.5f,.1f,6},60));
 add(make("wall","GPU service wall",5,{0,3.5f,20},{24,3.5f,.6f}));
 add(make("rtx-fe","RTX Founders Edition landmark",6,{0,10,30},{23,10,3.5f}));
 for(int i=0;i<4;++i) add(make("ram-"+std::to_string(i),"DDR5 tower",6,{30+3*static_cast<float>(i),5,-5},{.7f,5,7}));
 add(make("relay-core","Course relay core",7,{0,rise+.7f,-6},{.5f,.7f,.5f}));
 return session.apply({"course.seed."+new_uuid(),session.revision(),std::move(edits),"Established the separate motherboard traversal course"});
}
SceneSnapshot movement_course_scene(const CreatorSession& session) {
 SceneSnapshot scene{session.world_id(),session.revision(),{}};
 unsigned boards=0,targets=0;
 for(const auto& [alias,e]:session.world()) {
  if (alias!=e.id || !is_uuid(e.persistent_id) || e.name.empty()) throw std::invalid_argument("Invalid course entity identity");
  const auto kind=field(e,"course.kind"),state=field(e,"state");
  if (kind<1 || kind>7 || std::floor(kind)!=kind || state<0 || state>100) throw std::invalid_argument("Invalid course kind/state");
  const Vec3 p{static_cast<float>(field(e,"x")),static_cast<float>(field(e,"y")),static_cast<float>(field(e,"z"))};
  const Vec3 h{static_cast<float>(field(e,"hx")),static_cast<float>(field(e,"hy")),static_cast<float>(field(e,"hz"))};
  const Quaternion q{static_cast<float>(field(e,"qx")),static_cast<float>(field(e,"qy")),static_cast<float>(field(e,"qz")),static_cast<float>(field(e,"qw"))};
  Vec3 color{.25f,.3f,.35f}; float emission=0;
  if (kind==1) { ++boards; color={.035f,.13f,.10f}; }
  if (kind==3) color={.20f,.48f,.55f};
  if (kind==4) color={.65f,.19f,.10f};
  if (kind==6) color={.16f,.20f,.25f};
  if (kind==7) { ++targets; color=state==100?Vec3{.25f,.9f,.5f}:Vec3{.9f,.43f,.10f}; emission=state==100?.8f:.15f; }
  scene.objects.push_back({e.persistent_id,e.name,p,h,color,emission,kind!=1,q});
 }
 if (boards!=1 || targets!=1) throw std::invalid_argument("Course requires one motherboard and one relay core");
 (void)mesh_from_snapshot(scene);
 return scene;
}
Result restore_movement_course(CreatorSession& session,const std::string& persistent_id) {
 try { (void)movement_course_scene(session); }
 catch(const std::invalid_argument& e) { return {false,e.what(),session.revision()}; }
 for(const auto& [alias,e]:session.world()) if(e.persistent_id==persistent_id) {
  if(field(e,"course.kind")!=7) return {false,"Aim at the course relay core",session.revision()};
  if(field(e,"state")==100) return {true,"Relay core already recorded as restored",session.revision()};
  return session.apply({"course.repair."+new_uuid(),session.revision(),{SetField{alias,"state",100,persistent_id}},"Restored the traversal course relay core"});
 }
 return {false,"Course target no longer exists",session.revision()};
}
}
