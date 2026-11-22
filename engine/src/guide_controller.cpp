#include <aibs/guide_controller.hpp>
#include <algorithm>
#include <bit>
#include <cmath>
#include <limits>
#include <optional>
#include <queue>
#include <set>
#include <stdexcept>

namespace aibs {
namespace {
constexpr double tick=1.0/60;
constexpr std::size_t trail_limit=512;
bool finite(Vec3 p){return std::isfinite(p.x)&&std::isfinite(p.y)&&std::isfinite(p.z)&&std::max({std::abs(p.x),std::abs(p.y),std::abs(p.z)})<=1000000;}
float distance(Vec3 a,Vec3 b){return std::sqrt((a.x-b.x)*(a.x-b.x)+(a.y-b.y)*(a.y-b.y)+(a.z-b.z)*(a.z-b.z));}
float horizontal(Vec3 a,Vec3 b){return std::hypot(a.x-b.x,a.z-b.z);}
// Compare exactly the ordered inputs consumed by GroundedCharacter physics.
// Visual metadata and semantic revisions do not change an existing live body.
bool same_float(float a,float b){return std::bit_cast<std::uint32_t>(a)==std::bit_cast<std::uint32_t>(b);}
bool same_point(Vec3 a,Vec3 b){return same_float(a.x,b.x)&&same_float(a.y,b.y)&&same_float(a.z,b.z);}
bool same_collision(const SceneSnapshot& a,const SceneSnapshot& b){
 if(a.objects.size()!=b.objects.size())return false;
 for(std::size_t i=0;i<a.objects.size();++i){const auto& x=a.objects[i];const auto& y=b.objects[i];
  if(!same_point(x.center,y.center)||!same_point(x.half_extent,y.half_extent)||
     !same_float(x.rotation.x,y.rotation.x)||!same_float(x.rotation.y,y.rotation.y)||
     !same_float(x.rotation.z,y.rotation.z)||!same_float(x.rotation.w,y.rotation.w))return false;
 }
 return true;
}
void valid_intent(GuideIntent i){if(i!=GuideIntent::follow&&i!=GuideIntent::wait)throw std::invalid_argument("Invalid guide intent");}
void validate(const GuideRouteGraph& graph,GuideSettings s){
 if(graph.nodes.size()>256||graph.edges.size()>512)throw std::invalid_argument("Guide graph exceeds bounded profile");
 std::set<std::string> ids;
 for(const auto& n:graph.nodes)if(n.id.empty()||n.id.size()>128||!finite(n.feet)||!ids.insert(n.id).second)throw std::invalid_argument("Invalid or duplicate guide route node");
 for(const auto& e:graph.edges)if(!ids.contains(e.from)||!ids.contains(e.to)||e.from==e.to||e.door.size()>128)throw std::invalid_argument("Invalid guide edge");
 for(float f:{s.radius,s.height,s.walk_speed,s.catchup_speed,s.follow_distance,s.catchup_distance,s.graph_attach_distance,s.recall_min_distance,s.recall_max_distance})
  if(!std::isfinite(f)||f<=0)throw std::invalid_argument("Invalid guide settings");
 if(s.radius<.1f||s.radius>1||s.height<2*s.radius||s.height>3||s.walk_speed>10||s.catchup_speed<s.walk_speed||s.catchup_speed>15||s.follow_distance<.8f||s.follow_distance>5||s.catchup_distance<s.follow_distance||s.catchup_distance>30||s.graph_attach_distance>10||s.recall_min_distance<.8f||s.recall_max_distance<s.recall_min_distance||s.recall_max_distance>10)
  throw std::invalid_argument("Guide settings exceed supported profile");
}
CharacterSettings character_settings(GuideSettings s){CharacterSettings c;c.radius=s.radius;c.height=s.height;c.walk_speed=s.walk_speed;c.sprint_speed=s.catchup_speed;c.jump_speed=0;return c;}
std::unique_ptr<GroundedCharacter> supported(const SceneSnapshot& scene,Vec3 feet,GuideSettings settings){
 if(!finite(feet))throw std::invalid_argument("Invalid guide anchor");
 auto candidate=std::make_unique<GroundedCharacter>(scene,feet,character_settings(settings));
 const auto settled=candidate->advance({},8*tick);
 if(!settled.grounded||distance(settled.feet,feet)>.25f)throw std::invalid_argument("Guide anchor needs close stable ground support");
 candidate->suspend();return candidate;
}
}
struct GuideController::Impl {
 SceneSnapshot scene;
 GuideRouteGraph graph;
 GuideSettings settings;
 std::unique_ptr<GroundedCharacter> body;
 std::map<std::string,bool> doors;
 std::vector<Vec3> trail;
 std::vector<Vec3> route;
 std::optional<std::size_t> route_end;
 std::size_t route_cursor=0;
 std::optional<Vec3> previous_player;
 GuideIntentRecord saved;
 GuideActivity activity=GuideActivity::blocked;
 Vec3 destination;
 double accumulator=0,dropped=0;
 Impl(const SceneSnapshot& s,Vec3 spawn,GuideRouteGraph g,GuideSettings config):scene(s),graph(std::move(g)),settings(config){
  validate(graph,settings);body=supported(scene,spawn,settings);saved.waiting_anchor=body->state().feet;destination=saved.waiting_anchor;
 }
 void observe(GuideTarget player){
  if(!player.grounded||player.scene_revision!=scene.revision){trail.clear();previous_player.reset();return;}
  if(previous_player&&distance(*previous_player,player.feet)>1.5f)trail.clear();
  previous_player=player.feet;
  if(trail.empty()||distance(trail.back(),player.feet)>=.25f){
   if(trail.size()==trail_limit)trail.erase(trail.begin());
   trail.push_back(player.feet);
  }
 }
 std::optional<std::size_t> nearest(Vec3 p)const{
  float best=settings.graph_attach_distance;std::optional<std::size_t> result;
  for(std::size_t i=0;i<graph.nodes.size();++i){const auto d=distance(graph.nodes[i].feet,p);if(d<best){best=d;result=i;}}
  return result;
 }
 bool gate_open(const std::string& id)const{if(id.empty())return true;const auto at=doors.find(id);return at!=doors.end()&&at->second;}
 std::optional<Vec3> graph_destination(Vec3 from,Vec3 player){
  const auto end=nearest(player);if(!end)return {};
  if(route_end==end&&!route.empty()){
   while(route_cursor<route.size()&&distance(from,route[route_cursor])<=.3f)++route_cursor;
   if(route_cursor<route.size())return route[route_cursor];return player;
  }
  const auto start=nearest(from);if(!start)return {};
  const auto count=graph.nodes.size();std::vector<std::size_t> previous(count,count);std::queue<std::size_t> work;work.push(*start);previous[*start]=*start;
  while(!work.empty()&&previous[*end]==count){const auto current=work.front();work.pop();
   for(const auto& edge:graph.edges){if(!gate_open(edge.door))continue;std::string next;
    if(edge.from==graph.nodes[current].id)next=edge.to;else if(edge.bidirectional&&edge.to==graph.nodes[current].id)next=edge.from;else continue;
    const auto n=std::find_if(graph.nodes.begin(),graph.nodes.end(),[&](const auto& v){return v.id==next;});const auto index=static_cast<std::size_t>(n-graph.nodes.begin());
    if(previous[index]==count){previous[index]=current;work.push(index);}
   }
  }
  if(previous[*end]==count)return {};
  std::vector<Vec3> path;auto next=*end;path.push_back(graph.nodes[next].feet);
  while(next!=*start){next=previous[next];path.push_back(graph.nodes[next].feet);}
  std::reverse(path.begin(),path.end());route.swap(path);route_end=end;route_cursor=0;
  while(route_cursor<route.size()&&distance(from,route[route_cursor])<=.3f)++route_cursor;
  if(route_cursor<route.size())return route[route_cursor];return player;
 }
 std::optional<Vec3> trail_destination(Vec3 from,Vec3 player)const{
  if(trail.size()<2||distance(trail.back(),player)>.5f)return {};
  float best=1.1f;std::optional<std::size_t> index;
  for(std::size_t i=0;i<trail.size();++i){const auto d=distance(from,trail[i]);if(d<=best){best=d;index=i;}}
  if(!index)return {};
  if(distance(from,trail[*index])>.3f)return trail[*index];
  if(*index+1<trail.size())return trail[*index+1];return player;
 }
 bool safe_step(Vec3 from,Vec3 to)const{
  try {
   const Vec3 chest{from.x,from.y+settings.height*.5f,from.z},desired{to.x,to.y+settings.height*.5f,to.z};
   if(distance(body->camera_position(chest,desired,settings.radius),desired)>.015f)return false;
   // The next horizontal foot location must retain nearby floor support. This
   // query prevents stale graph segments from walking Adam off a removed bridge.
   for(const Vec3 offset:std::initializer_list<Vec3>{{0,0,0},{settings.radius,0,0},{-settings.radius,0,0},{0,0,settings.radius},{0,0,-settings.radius}}){
    const Vec3 high{to.x+offset.x,from.y+.5f,to.z+offset.z},low{high.x,from.y-.25f,high.z};
    const auto hit=body->camera_position(high,low,0);if(hit.y<=low.y+.015f||hit.y>from.y+.41f)return false;
   }
   return true;
  }catch(const std::invalid_argument&){return false;}
 }
 void step(GuideTarget player){
  const auto before=body->state();CharacterInput input{};activity=GuideActivity::blocked;destination=before.feet;
  if(saved.intent==GuideIntent::wait)activity=GuideActivity::waiting;
  else if(player.scene_revision!=scene.revision||!player.grounded)activity=GuideActivity::blocked;
  else if(distance(before.feet,player.feet)<=settings.follow_distance)activity=GuideActivity::near_player;
  else {
   auto next=graph_destination(before.feet,player.feet);if(!next)next=trail_destination(before.feet,player.feet);
   if(next){destination=*next;const auto d=horizontal(before.feet,*next);if(d>.02f){
    input.sprint=horizontal(before.feet,player.feet)>settings.catchup_distance;const auto speed=input.sprint?settings.catchup_speed:settings.walk_speed;
    const float scale=std::min(1.0f,d/(speed*static_cast<float>(tick)));
    input.move={(next->x-before.feet.x)/d*scale,0,(next->z-before.feet.z)/d*scale};
    const Vec3 projected{before.feet.x+input.move.x*speed*static_cast<float>(tick),before.feet.y,before.feet.z+input.move.z*speed*static_cast<float>(tick)};
    if(safe_step(before.feet,projected))activity=GuideActivity::following;else input={};
   }}
  }
  const auto after=body->advance(input,tick);
  if(activity==GuideActivity::following&&horizontal(before.feet,after.feet)<.001f)activity=GuideActivity::blocked;
 }
 GuideState state()const{return {body->state(),saved.intent,activity,destination,trail.size(),dropped};}
};
GuideController::GuideController(const SceneSnapshot& scene,Vec3 spawn,GuideRouteGraph graph,GuideSettings settings):impl_(std::make_unique<Impl>(scene,spawn,std::move(graph),settings)){}
GuideController::~GuideController()=default;
GuideController::GuideController(GuideController&&) noexcept=default;
GuideController& GuideController::operator=(GuideController&&) noexcept=default;
void GuideController::set_doors(std::map<std::string,bool> doors){
 if(doors.size()>128)throw std::invalid_argument("Guide gate state budget exceeded");
 for(const auto& [id,open]:doors){(void)open;if(id.empty()||id.size()>128)throw std::invalid_argument("Invalid guide gate ID");}
 if(impl_->doors!=doors){impl_->doors.swap(doors);impl_->route.clear();impl_->route_end.reset();}
}
void GuideController::set_scene(const SceneSnapshot& scene){
 auto& p=*impl_;if(scene.world_id!=p.scene.world_id||scene.revision<p.scene.revision)throw std::invalid_argument("Guide scene identity or revision mismatch");
 // A valid moving contact may not be a valid freshly settled spawn. Keep
 // its contacts, velocity, fractional tick and actual trail when every collider
 // is identical. Validate ALL incoming metadata before adopting the new epoch.
 if(same_collision(p.scene,scene)){
  (void)mesh_from_snapshot(scene);SceneSnapshot staged=scene;std::swap(p.scene,staged);return;
 }
 auto candidate=supported(scene,p.body->state().feet,p.settings);SceneSnapshot staged=scene;
 p.body.swap(candidate);std::swap(p.scene,staged);p.saved.waiting_anchor=p.body->state().feet;p.trail.clear();p.route.clear();p.route_end.reset();p.previous_player.reset();p.accumulator=0;p.activity=GuideActivity::blocked;p.destination=p.body->state().feet;
}
std::uint64_t GuideController::scene_revision()const noexcept{return impl_->scene.revision;}
void GuideController::set_intent(GuideIntent intent){
 valid_intent(intent);auto& p=*impl_;if(intent==GuideIntent::wait){const auto state=p.body->state();if(!state.grounded)throw std::invalid_argument("Guide cannot Wait without support");p.saved.waiting_anchor=state.feet;}
 p.saved.intent=intent;p.activity=intent==GuideIntent::wait?GuideActivity::waiting:GuideActivity::blocked;p.accumulator=0;p.body->suspend();
}
GuideIntentRecord GuideController::saved_intent()const{return impl_->saved;}
void GuideController::restore_intent(const GuideIntentRecord& saved){
 valid_intent(saved.intent);auto& p=*impl_;auto candidate=supported(p.scene,saved.waiting_anchor,p.settings);
 p.body.swap(candidate);p.saved=saved;p.saved.waiting_anchor=p.body->state().feet;p.accumulator=0;p.trail.clear();p.route.clear();p.route_end.reset();p.previous_player.reset();p.activity=saved.intent==GuideIntent::wait?GuideActivity::waiting:GuideActivity::blocked;p.destination=p.body->state().feet;
}
bool GuideController::recall(Vec3 player,std::span<const Vec3> candidates){return recall(impl_->scene,player,candidates);}
bool GuideController::recall(const SceneSnapshot& scene,Vec3 player,std::span<const Vec3> candidates){
 if(!finite(player)||candidates.size()>16)throw std::invalid_argument("Invalid guide Recall request");auto& p=*impl_;
 if(scene.world_id!=p.scene.world_id||scene.revision<p.scene.revision)throw std::invalid_argument("Guide Recall scene identity or revision mismatch");
 for(const auto candidate:candidates){if(!finite(candidate))continue;const auto d=distance(player,candidate);if(d<p.settings.recall_min_distance||d>p.settings.recall_max_distance)continue;
  try{auto body=supported(scene,candidate,p.settings);const auto settled_distance=distance(player,body->state().feet);if(settled_distance<p.settings.recall_min_distance||settled_distance>p.settings.recall_max_distance)continue;SceneSnapshot staged=scene;p.body.swap(body);std::swap(p.scene,staged);p.accumulator=0;p.trail.clear();p.route.clear();p.route_end.reset();p.previous_player.reset();p.saved.waiting_anchor=p.body->state().feet;p.activity=p.saved.intent==GuideIntent::wait?GuideActivity::waiting:GuideActivity::blocked;p.destination=p.body->state().feet;return true;}catch(const std::invalid_argument&){}
 }
 return false;
}
GuideState GuideController::advance(GuideTarget target,double elapsed){
 if(!finite(target.feet)||!std::isfinite(elapsed)||elapsed<0)throw std::invalid_argument("Invalid guide target or elapsed time");auto& p=*impl_;p.observe(target);
 const auto accepted=std::min(elapsed,4*tick);p.dropped+=elapsed-accepted;p.accumulator+=accepted;
 unsigned ticks=0;while(p.accumulator+1e-12>=tick&&ticks<4){p.step(target);p.accumulator=std::max(0.0,p.accumulator-tick);++ticks;}return p.state();
}
GuideState GuideController::state()const{return impl_->state();}
void GuideController::suspend()noexcept{impl_->accumulator=0;impl_->body->suspend();}
}
