// Current-content diagnostic traversal. Planning queries never become actor
// evidence: every accepted segment is walked again by BS through normal W,
// collision, door, E and Build handling. Ordinary player mode has no dwell.
#include "workshop_tour_path.hpp"
namespace workshop_tour {
float distance(Vec3 a,Vec3 b){return std::hypot(a.x-b.x,a.z-b.z);}
const GuideRouteGraph& graph(const ChapterLive& live){
 require(live.content&&!live.content->definition().companions.empty(),"Workshop tour requires Adam's authored routes");
 const auto& g=live.content->definition().companions.front().routes;
 require(!g.nodes.empty()&&g.nodes.size()<=64&&g.edges.size()<=128,"Workshop tour route graph exceeds bounds");return g;
}
std::size_t index(const GuideRouteGraph& g,const std::string& id){
 for(std::size_t n=0;n<g.nodes.size();++n)if(g.nodes[n].id==id)return n;
 throw std::runtime_error("Workshop tour has no authored waypoint: "+id);
}
bool clear(const ChapterLive& live,const std::vector<Vec3>& points,Vec3* standing=nullptr){
 if(points.empty()||points.size()>3||!live.player.state().grounded)return false;
 return workshop_tour_path::clear(live.scene,live.player.state().feet,points,chapter_board(live).y-.2f,standing);
}
void walk(ChapterLive& live,const std::vector<Vec3>& points,std::vector<Vec3>* actual_breadcrumbs=nullptr){
 const auto from=live.player.state().feet;
 if(actual_breadcrumbs){actual_breadcrumbs->clear();actual_breadcrumbs->push_back(from);}
 std::cerr<<"WORKSHOP_TOUR_WALK {\"from\":["<<from.x<<','<<from.y<<','<<from.z<<"],\"grounded\":"<<(live.player.state().grounded?"true":"false")<<",\"revision\":"<<live.owner->snapshot()->revision<<",\"points\":[";
 bool first=true;for(const auto p:points){if(!first)std::cerr<<',';first=false;std::cerr<<'['<<p.x<<','<<p.y<<','<<p.z<<']';}std::cerr<<"]}\n";
 require(clear(live,points),"Workshop tour walking plan is blocked at ("+std::to_string(from.x)+","+std::to_string(from.y)+","+std::to_string(from.z)+"); no teleport substituted");const auto board=chapter_board(live);
 const auto recoveries=chapter_record(*live.owner->snapshot(),live.ids().progress).fields.at("recoveries");
 for(const auto p:points){chapter_walk(live,p.x-board.x,p.z-board.z);
  if(actual_breadcrumbs)actual_breadcrumbs->push_back(live.player.state().feet);
  require(chapter_record(*live.owner->snapshot(),live.ids().progress).fields.at("recoveries")==recoveries,"Workshop tour path triggered fall/arc recovery");}
}
void go(ChapterLive& live,const std::string& target){
 std::cerr<<"WORKSHOP_TOUR_NODE "<<quoted(target)<<'\n';
 const auto& g=graph(live);const auto goal=index(g,target);const auto state=live.owner->snapshot();const auto feet=live.player.state().feet;
 std::size_t start=g.nodes.size();float nearest=5.5f;
 for(std::size_t n=0;n<g.nodes.size();++n){const auto& node=g.nodes[n];const auto length=distance(feet,node.feet);
  if(length<nearest&&live.region(*state,node.feet)==live.region(*state,feet)&&clear(live,{node.feet})){nearest=length;start=n;}}
 require(start<g.nodes.size(),"Workshop tour cannot attach current BS to a walkable waypoint");
 std::vector<std::size_t> previous(g.nodes.size(),g.nodes.size()),queue{start};previous[start]=start;
 for(std::size_t cursor=0;cursor<queue.size()&&previous[goal]==g.nodes.size();++cursor){const auto at=queue[cursor];
  for(const auto& edge:g.edges){std::string next;
   if(edge.from==g.nodes[at].id)next=edge.to;else if(edge.bidirectional&&edge.to==g.nodes[at].id)next=edge.from;else continue;
   if(!edge.door.empty()&&!chapter_flag(chapter_record(*state,edge.door),"open"))continue;
   const auto n=index(g,next);if(previous[n]==g.nodes.size()){previous[n]=at;queue.push_back(n);}
  }}
 require(previous[goal]<g.nodes.size(),"Workshop tour route is gated by a closed door");walk(live,{g.nodes[start].feet});std::vector<std::size_t> path;
 for(auto at=goal;at!=start;at=previous[at]){require(path.size()<g.nodes.size(),"Workshop tour route cycle");path.push_back(at);}
 std::reverse(path.begin(),path.end());for(const auto at:path)walk(live,{g.nodes[at].feet});
}
std::vector<Vec3> approach(const ChapterLive& live,const std::string& id,bool body_visibility=true){
 const auto target=chapter_target(live,id),start=live.player.state().feet;const auto region=live.region(*live.owner->snapshot(),start);
 const auto& d=live.content->definition();const auto floor=region=="jenison"?d.jenison_returns.front().y:d.hub_returns.front().y;
 auto solids=live.scene;for(auto& o:solids.objects)o.selectable=true;
 constexpr std::array<Vec3,8> offsets{{{1.2f,0,0},{-1.2f,0,0},{0,0,1.2f},{0,0,-1.2f},{2.5f,0,0},{-2.5f,0,0},{0,0,2.5f},{0,0,-2.5f}}};
 for(const auto offset:offsets){const Vec3 candidate{target.x+offset.x,floor,target.z+offset.z};
  const std::array<std::vector<Vec3>,3> plans{{{candidate},{{start.x,floor,candidate.z},candidate},{{candidate.x,floor,start.z},candidate}}};
  for(const auto& plan:plans){Vec3 standing;
   if(!clear(live,plan,&standing)||live.region(*live.owner->snapshot(),standing)!=region)continue;
   if(!body_visibility&&std::hypot(standing.x-target.x,standing.y-target.y,standing.z-target.z)>3.2f)continue;
   // Mechanisms use the authoritative body and camera rays. Inspection panels
   // use their existing camera-visibility plus feet-distance contract; a page
   // on a table need not be visible through that table from waist height.
   bool visible=true;for(const float eye_height:{.9f,1.62f}){if(!body_visibility&&eye_height<1)continue;const Vec3 eye{standing.x,standing.y+eye_height,standing.z};
    const auto hit=pick_scene(solids,eye,{target.x-eye.x,target.y-eye.y,target.z-eye.z},3.2f);if(!hit||hit->persistent_id!=id){visible=false;break;}}
   if(visible&&(body_visibility?
       workshop_tour_path::reversible_station(live.scene,start,plan,start,chapter_board(live).y-.2f):
       workshop_tour_path::reversible(live.scene,start,plan,start,chapter_board(live).y-.2f)))return plan;
  }}
 throw std::runtime_error("Workshop tour has no visible physical approach to "+id);
}
void return_evidence(const ChapterLive& live,Vec3 anchor,const std::string& context,const char* phase){
 const auto body=live.player.state();const auto feet=body.feet;
 std::cerr<<std::setprecision(17)<<"WORKSHOP_TOUR_RETURN {\"phase\":"<<quoted(phase)<<",\"context\":"<<quoted(context)
  <<",\"feet\":["<<feet.x<<','<<feet.y<<','<<feet.z<<"],\"velocity\":["<<body.velocity.x<<','<<body.velocity.y<<','<<body.velocity.z
  <<"],\"grounded\":"<<(body.grounded?"true":"false")<<",\"anchor\":["<<anchor.x<<','<<anchor.y<<','<<anchor.z<<"],\"revision\":"<<live.owner->snapshot()->revision;
 const auto blocker=workshop_tour_path::nearest_blocker(live.scene,feet);
 if(blocker)std::cerr<<",\"nearest_blocker\":{\"id\":"<<quoted(blocker->id)<<",\"name\":"<<quoted(blocker->name)
  <<",\"center\":["<<blocker->center.x<<','<<blocker->center.y<<','<<blocker->center.z<<"],\"half_extent\":["<<blocker->half_extent.x<<','<<blocker->half_extent.y<<','<<blocker->half_extent.z
  <<"],\"capsule_clearance\":"<<blocker->clearance<<'}';
 std::cerr<<"}\n";
}
std::vector<Vec3> reverse_breadcrumbs(const std::vector<Vec3>& actual,Vec3 anchor){
 std::vector<Vec3> points;for(std::size_t n=actual.size();n>1;--n)points.push_back(actual[n-2]);
 if(points.empty()||distance(points.back(),anchor)>.001f)points.push_back(anchor);return points;
}
std::vector<Vec3> actual_return_plan(const ChapterLive& live,const std::vector<Vec3>& actual,Vec3 anchor){
 auto points=reverse_breadcrumbs(actual,anchor);
 if(!clear(live,points))points=workshop_tour_path::return_plan(live.scene,live.player.state().feet,anchor,chapter_board(live).y-.2f);
 return points;
}
void back(ChapterLive& live,const std::vector<Vec3>& actual,Vec3 anchor,const std::string& context){
 return_evidence(live,anchor,context,"after-interaction");
 const auto points=actual_return_plan(live,actual,anchor);
 if(points.empty())return_evidence(live,anchor,context,"no-return-plan");
 require(!points.empty(),"Workshop tour has no collision-checked return to its authored corridor");walk(live,points);
}
void station(ChapterLive& live,const OpeningWorkshopBinding& binding,std::size_t slot,std::size_t expected_delta){
 require(expected_delta<=1,"Workshop station probe expects zero or one outcome");
 std::cerr<<"WORKSHOP_TOUR_STATION "<<slot<<'\n';
 constexpr std::array<const char*,5> anchors{{"nook-turn","west10","west10","fault","hub"}};
 go(live,anchors.at(slot));const auto anchor=live.player.state().feet;const auto& id=binding.fixtures.at(slot);const auto plan=approach(live,id);std::vector<Vec3> actual;walk(live,plan,&actual);
 return_evidence(live,anchor,id,"before-station");
 require(!actual_return_plan(live,actual,anchor).empty(),"Actual station approach has no collision-checked return; interaction not sent");
 const auto before=live.owner->snapshot()->revision;
 require(chapter_press(live,chapter_target(live,id)),"Workshop tour station E failed: "+live.notice);
 require(live.owner->snapshot()->revision==before+expected_delta,"Workshop station outcome count differs from the expected change/idempotent action");back(live,actual,anchor,id);
}
void read(ChapterLive& live,const OpeningTourTargets& targets,OpeningTourRole role,const char* anchor_id){
 std::cerr<<"WORKSHOP_TOUR_READ "<<quoted(std::string(opening_tour_role_name(role)))<<'\n';
 go(live,anchor_id);const auto anchor=live.player.state().feet;const auto& id=targets.ids.at(static_cast<std::size_t>(role));
 const auto plan=approach(live,id,false);std::vector<Vec3> actual;walk(live,plan,&actual);
 return_evidence(live,anchor,std::string(opening_tour_role_name(role)),"before-read");
 require(!actual_return_plan(live,actual,anchor).empty(),"Actual reading approach has no collision-checked return; panel not opened");
 opening_tour_read(live,targets,role,live.player.state().feet);back(live,actual,anchor,std::string(opening_tour_role_name(role)));
}
void isolation(ChapterLive& live){
 const auto before=live.player.state().feet;const auto x=live.content->definition().isolation_switch.x;
 walk(live,{{x-1.3f,before.y,before.z}});
 require(chapter_press(live,chapter_target(live,live.ids().fault,"Isolation switch")),"Workshop tour isolation E failed: "+live.notice);walk(live,{before});
}
void run(ChapterLive& live,const OpeningTourTargets& targets){
 const auto binding=first_boot_content_workshop_binding(live.content->definition());require(binding.has_value(),"Workshop tour binding absent");const auto ids=live.ids();
 read(live,targets,OpeningTourRole::controller,"nook-turn");read(live,targets,OpeningTourRole::truck,"nook-turn");station(live,*binding,0);
 station(live,*binding,1);station(live,*binding,2);
 if(live.config.tour_route=="bypass")station(live,*binding,2);
 read(live,targets,OpeningTourRole::diagnostic,"west10");read(live,targets,OpeningTourRole::bypass,"west10");
 go(live,"west");chapter_walk(live,-37,-25);chapter_walk(live,-37,-6.5f);chapter_walk(live,-35.5f,-6.5f);
 require(chapter_press(live,chapter_target(live,ids.fault,"Downstream power fault")),"Workshop tour fault diagnosis failed: "+live.notice);
 chapter_walk(live,-35.5f,-5.2f);isolation(live);
 if(live.config.tour_route=="repair"){
  chapter_walk(live,-33,-5.2f);require(chapter_press(live,chapter_target(live,ids.fault,"Downstream power fault")),"Workshop tour repair failed: "+live.notice);
  chapter_walk(live,-35.5f,-5.2f);isolation(live);
 }else{
  chapter_walk(live,-42,-5.2f);const auto socket=chapter_point(chapter_record(*live.owner->snapshot(),ids.fault),"socket_");
  require(chapter_press(live,{socket.x,socket.y+1,socket.z},'B'),"Workshop tour relay Build failed: "+live.notice);std::string relay;
  for(const auto& node:chapter_nodes(*live.owner->snapshot()).components)if(chapter_flag(node,"alive")&&chapter_number(node,"firstboot.kind")==6&&std::hypot(chapter_number(node,"x")-socket.x,chapter_number(node,"z")-socket.z)<.1f)relay=node.entity_id;
  require(!relay.empty()&&chapter_press(live,chapter_target(live,relay)),"Workshop tour bypass connection failed: "+live.notice);
 }
 station(live,*binding,3);
 if(live.config.tour_route=="repair"){
  go(live,"main-front");require(chapter_press(live,chapter_target(live,ids.main_door)),"Workshop tour main door failed: "+live.notice);chapter_walk(live,-33,6);
 }else{
  go(live,"service-front");require(chapter_press(live,chapter_target(live,ids.service_door)),"Workshop tour service door failed: "+live.notice);chapter_walk(live,-41,6);
 }
 require(chapter_text(chapter_record(*live.owner->snapshot(),ids.progress),"first_route")==live.config.tour_route,"Workshop tour did not earn the walked route");station(live,*binding,4);
 const auto record=chapter_record(*live.owner->snapshot(),binding->fixtures[4]);
 require(chapter_flag(record,"bench_claimed")&&opening_workshop_online(record,*binding,first_boot_content_workshop_circuit(*live.owner->snapshot(),*live.content)),"Workshop tour bench is not online and claimed");
 read(live,targets,OpeningTourRole::seats,"hub");read(live,targets,OpeningTourRole::shelter,"hub");go(live,"pencil-front");
 require(chapter_press(live,chapter_target(live,ids.pencil_door)),"Workshop tour Pencil door failed: "+live.notice);chapter_walk(live,-37,15);
 read(live,targets,OpeningTourRole::pencil,"pencil-back");
 require(chapter_flag(chapter_record(*live.owner->snapshot(),ids.progress),"pencil_visited")&&live.tour_reads.size()==opening_tour_stop_count,"Workshop tour missed an authored stop or physical Pencil Room entry");
 const auto deadline=Clock::now()+std::chrono::seconds(20);
 for(unsigned n=0;n<1200;++n){const auto guide=live.companion->state();
  if(guide.guide&&!guide.recall_required&&guide.saved.intent==GuideIntent::follow&&distance(guide.guide->character.feet,live.player.state().feet)<3.5f){live.proof_companion_route=true;break;}
  require(!live.config.walkthrough||Clock::now()<deadline,"Adam could not follow the Workshop tour without Recall");require(live.tour_frame(1./60),"Workshop catch-up frame closed");}
 require(live.proof_companion_route,"Adam did not follow the Workshop tour");live.proof_opening_tour=true;
}
} // namespace workshop_tour
