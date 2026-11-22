#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <aibs/creator_viewport.hpp>
#include <aibs/chapter_viewport.hpp>
#include <aibs/placed_assets.hpp>
#include <aibs/content_lighting.hpp>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <optional>
#include <string>
#include <thread>

namespace {
void require(bool value,const char* why){if(!value)throw std::runtime_error(why);}
// BEGIN SNAPSHOT WATCH HEALTH
// The existing valid scene stays visible during replacement. A transient miss
// is not a rejected document; prolonged unavailability must be observable.
struct SnapshotHealth {
 using Clock=std::chrono::steady_clock;
 std::optional<Clock::time_point> since;
 std::string reason;
 bool announced=false;
 bool pending()const{return since.has_value();}
 bool failure(Clock::time_point now,const std::string& next_reason,bool transient){
  if(!since)since=now;
  const bool due=!transient||now-*since>=std::chrono::seconds(2);
  const bool report=due&&(!announced||reason!=next_reason);
  reason=next_reason;announced=announced||report;return report;
 }
 bool recover(){const bool reported=announced;since.reset();reason.clear();announced=false;return reported;}
};
// END SNAPSHOT WATCH HEALTH
struct SnapshotOpenError:std::runtime_error {
 explicit SnapshotOpenError(DWORD code):std::runtime_error("Snapshot unavailable (Win32 "+std::to_string(code)+")"){}
};
std::filesystem::path shaders(){std::wstring p(32768,L'\0');auto n=GetModuleFileNameW(nullptr,p.data(),static_cast<DWORD>(p.size()));require(n&&n<p.size(),"Executable directory unavailable");p.resize(n);return std::filesystem::path(p).parent_path()/"shaders";}
struct Snapshot: aibs::CreatorViewportSnapshot {std::optional<aibs::ChapterViewportSnapshot> chapter;};
Snapshot read(const std::filesystem::path& path){
 std::vector<unsigned char> bytes;
 {
  // The publisher atomically replaces this file. Share deletion so even the
  // brief read cannot block that rename, and close before costly validation.
  struct File {HANDLE handle;~File(){if(handle!=INVALID_HANDLE_VALUE)CloseHandle(handle);}};
  const File file{CreateFileW(path.c_str(),GENERIC_READ,FILE_SHARE_READ|FILE_SHARE_DELETE,nullptr,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL|FILE_FLAG_SEQUENTIAL_SCAN,nullptr)};
  if(file.handle==INVALID_HANDLE_VALUE)throw SnapshotOpenError(GetLastError());LARGE_INTEGER length{};
  require(GetFileSizeEx(file.handle,&length)&&length.QuadPart>=0&&static_cast<std::uint64_t>(length.QuadPart)<=aibs::chapter_viewport_maximum_bytes,"Snapshot size failure");
  bytes.resize(static_cast<std::size_t>(length.QuadPart));DWORD copied=0;
  require(ReadFile(file.handle,bytes.data(),static_cast<DWORD>(bytes.size()),&copied,nullptr)&&copied==bytes.size(),"Snapshot read failure");
 }
 Snapshot result;
 if(bytes.size()>6&&bytes[6]==2){auto chapter=aibs::decode_chapter_viewport_snapshot(bytes);result.snapshot_id=chapter.snapshot_id;result.scope=chapter.scope;result.checkpoint_id=chapter.checkpoint_id;result.selected_id=chapter.selected_id;result.revision=chapter.revision;result.chapter=std::move(chapter);}
 else static_cast<aibs::CreatorViewportSnapshot&>(result)=aibs::decode_viewport_snapshot(bytes);
 return result;
}
aibs::SceneSnapshot project(const Snapshot& snapshot){return snapshot.chapter?aibs::chapter_viewport_scene(*snapshot.chapter):aibs::viewport_scene(snapshot);}
struct Projection {
 aibs::SceneSnapshot base,picks;
 aibs::SceneMesh mesh;
 aibs::SceneLighting lighting;
 std::shared_ptr<const aibs::PlacedAssetVisuals> placed;
};
const aibs::TexturedScene& texture_layer(const std::shared_ptr<const aibs::PlacedAssetVisuals>& placed){
 static const aibs::TexturedScene empty;
 return placed?placed->textured():empty;
}
Projection project_visual(const Snapshot& snapshot,const std::filesystem::path& store){
 Projection result;result.base=project(snapshot);
 if(snapshot.chapter){
  const auto& chapter=*snapshot.chapter;
  // Creator-only markers are selectable authoring aids, never gameplay colliders.
  for(const auto& memory:chapter.content.definition().memories)result.base.objects.push_back({memory.entity_id,memory.name,{memory.position.x,memory.position.y+.45f,memory.position.z},{.45f,.45f,.35f},{.82f,.47f,.12f},.25f,true,{}});
const auto baseline=aibs::first_boot_content_baseline(chapter.content);
  const aibs::GameplayStoreRecovery state{{chapter.scope.project,chapter.scope.world_id,chapter.scope.branch,chapter.content.definition().definition_id,aibs::GameplayContext::temporary_play},baseline.revision,baseline.sequence,baseline.components};
  result.lighting=aibs::first_boot_content_lighting(state,chapter.content);
  result.placed=std::make_shared<aibs::PlacedAssetVisuals>(snapshot.chapter->content,store);
  result.mesh=result.placed->mesh(result.base);result.picks=result.placed->picking_scene(result.base);
 }else {result.mesh=aibs::mesh_from_snapshot(result.base);result.picks=result.base;}
 return result;
}
void publish_projection(aibs::Dx12Renderer& renderer,const Projection& projection,
 const std::shared_ptr<const aibs::PlacedAssetVisuals>& candidate,const std::shared_ptr<const aibs::PlacedAssetVisuals>& previous,bool modern){
 if(!modern){renderer.set_scene_character_asset(projection.mesh,texture_layer(candidate),projection.lighting,candidate?candidate->companion_model():nullptr);return;}
 constexpr std::size_t limit=128u*1024u*1024u;std::size_t cpu=2u*1024u*1024u; // Bounded snapshot/control metadata reserve.
 const auto add=[&](std::size_t bytes){require(bytes<=limit-cpu,"Creator candidate CPU residency exceeds128MiB");cpu+=bytes;};
 if(candidate)add(candidate->resident_bytes());
 // A candidate is loaded before replacing the current owner; charge both until
 // publication completes. Same immutable projection owner is charged once.
 if(previous&&previous.get()!=candidate.get())add(previous->resident_bytes());
 add(projection.mesh.vertices.capacity()*sizeof(aibs::SceneVertex));add(projection.mesh.landmarks.capacity()*sizeof(std::string));for(const auto& name:projection.mesh.landmarks)add(name.capacity()+1);
 renderer.set_scene_character_asset_bounded(projection.mesh,texture_layer(candidate),projection.lighting,candidate?candidate->companion_model():nullptr,limit-cpu);
}
std::optional<aibs::CharacterInstance> character_instance(const Snapshot& snapshot,
 const std::shared_ptr<const aibs::PlacedAssetVisuals>& placed,double seconds){
 const auto* model=placed?placed->companion_model():nullptr;
 if(!model||!snapshot.chapter)return {};
 aibs::CharacterInstance instance;instance.pose=aibs::sample_character_clip(model->mesh,0,seconds);
 aibs::CharacterJointTransform world;world.translation=snapshot.chapter->content.definition().companions.front().spawn;
 instance.world=aibs::character_transform_matrix(world);instance.tint={.55f,.85f,1};instance.emission=.85f;instance.opacity=.78f;return instance;
}
aibs::Vec3 ray(const aibs::Camera& camera,float x,float y,float aspect){
 const auto sy=std::sin(camera.yaw),cy=std::cos(camera.yaw),sp=std::sin(camera.pitch),cp=std::cos(camera.pitch);const auto scale=std::tan(3.14159265f/8);
 return {sy*cp+x*scale*aspect*cy-y*scale*sy*sp,sp+y*scale*cp,cy*cp-x*scale*aspect*sy-y*scale*cy*sp};
}
void emit(const char* kind,const aibs::CreatorViewportSnapshot& s,const std::string& id=""){
 std::cout<<"AIBV1 "<<kind<<' '<<s.snapshot_id<<' '<<s.scope.world_id<<' '<<s.revision;
 if(*kind=='P')std::cout<<' '<<(id.empty()?"-":id);std::cout<<std::endl;
}
void fit(aibs::Camera& camera,const aibs::SceneSnapshot& scene){
 if(scene.objects.empty()){camera={{0,5,-10},0,-.4f};return;}
 auto low=scene.objects.front().center,high=low;
 for(const auto& o:scene.objects){low.x=std::min(low.x,o.center.x-o.half_extent.x);low.y=std::min(low.y,o.center.y-o.half_extent.y);low.z=std::min(low.z,o.center.z-o.half_extent.z);high.x=std::max(high.x,o.center.x+o.half_extent.x);high.y=std::max(high.y,o.center.y+o.half_extent.y);high.z=std::max(high.z,o.center.z+o.half_extent.z);}
 const auto radius=std::max({high.x-low.x,high.y-low.y,high.z-low.z,4.f});
 camera={{(low.x+high.x)*.5f+radius*.7f,(low.y+high.y)*.5f+radius*.65f,(low.z+high.z)*.5f-radius*.9f},-.661f,-.519f};
}
void focus_probe(aibs::Camera& camera,const aibs::SceneSnapshot& scene,const std::string& selected){
 auto opaque=scene;for(auto& object:opaque.objects)object.selectable=true;
 for(const auto& target:scene.objects){
  if(!target.selectable||(!selected.empty()&&selected!=target.persistent_id))continue;
  const auto extent=std::max({target.half_extent.x,target.half_extent.y,target.half_extent.z,.5f});
  // Stay inside Camera::update's pitch clamp; a vertical look would move the
  // real Win32 click away from thin fixtures after the camera update.
  for(const auto side:std::array<aibs::Vec3,8>{{{0,1,-1},{1,1,-1},{-1,1,-1},{1,1,0},{-1,1,0},{0,1,1},{1,1,1},{-1,1,1}}}){
   const aibs::Vec3 offset{side.x*(extent*3+2),side.y*(extent*3+2),side.z*(extent*3+2)};
   const aibs::Vec3 origin{target.center.x+offset.x,target.center.y+offset.y,target.center.z+offset.z};const aibs::Vec3 direction{-offset.x,-offset.y,-offset.z};
   const auto hit=aibs::pick_scene(opaque,origin,direction,1000000);if(!hit||hit->persistent_id!=target.persistent_id)continue;
   const auto length=std::sqrt(offset.x*offset.x+offset.y*offset.y+offset.z*offset.z);
   camera={origin,std::atan2(direction.x,direction.z),std::asin(direction.y/length)};return;
  }
 }
 throw std::runtime_error("No visible authored fixture available for chapter click probe");
}
}
int wmain(int argc,wchar_t** argv){
 try {
  std::filesystem::path source,stop,capture,report,asset_root;bool probe=false;
  for(int i=1;i<argc;++i){const std::wstring arg=argv[i];
   if(arg==L"--self-test")probe=true;
   else if((arg==L"--snapshot"||arg==L"--stop-file"||arg==L"--capture"||arg==L"--report"||arg==L"--asset-root")&&i+1<argc){auto path=std::filesystem::path(argv[++i]);if(arg==L"--snapshot")source=path;else if(arg==L"--stop-file")stop=path;else if(arg==L"--capture")capture=path;else if(arg==L"--asset-root")asset_root=path;else report=path;}
   else throw std::invalid_argument("Unknown viewport argument");
  }
  require(!source.empty()&&!stop.empty(),"Explicit snapshot and stop-file required");
  require(!probe||(!capture.empty()&&!report.empty()),"Self-test requires capture/report");
  auto snapshot=read(source);auto projection=project_visual(snapshot,asset_root);
  auto scene=std::move(projection.base),picking=std::move(projection.picks);auto placed=std::move(projection.placed);
  SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);
  aibs::NativeWindow window(1100,740,L"AI-BS Creator Preview | WASD + right-mouse look | Space/Ctrl vertical | V frame world | Click select | Esc close",!probe);
  aibs::Dx12Renderer renderer(window,{},shaders());publish_projection(renderer,projection,placed,{},snapshot.chapter&&snapshot.chapter->content.definition().asset_profile==aibs::AssetContentProfile::warm_beginning);projection.mesh={};aibs::Camera camera;fit(camera,picking);
  if(probe&&!snapshot.chapter)camera={{0,0,-8},0,0};
  // Force the first poll after renderer setup: the publisher may have replaced
  // the initial bytes while decoding or creating the GPU resources.
  auto stamp=std::filesystem::file_time_type::min();auto previous=std::chrono::steady_clock::now();auto next_read=previous;
  std::string selected=snapshot.selected_id;unsigned frames=0;double animation_seconds=0;emit("READY",snapshot);
  constexpr const wchar_t* preview_status=L"READ-ONLY CREATOR PREVIEW | Click selects the persistent object in AI-BS.\nWASD/right-mouse look; Space/Ctrl rise/lower; V frames the world. Authoring Save stays in AI-BS.";
  window.set_status(preview_status);SnapshotHealth snapshot_health;
  while(window.poll()){
   if(std::filesystem::exists(stop))break;
   const auto now=std::chrono::steady_clock::now();const float seconds=std::chrono::duration<float>(now-previous).count();previous=now;
   if(now>=next_read){next_read=now+std::chrono::milliseconds(100);std::error_code metadata_error;const auto changed=std::filesystem::last_write_time(source,metadata_error);
    // ReplaceFileW can briefly hide the watched name. Retain the displayed
    // scene and retry; a failed read must not mark this timestamp as consumed.
    if(metadata_error){
     if(snapshot_health.failure(now,metadata_error.message(),true)){
      std::cerr<<"Snapshot unavailable: "<<metadata_error.message()<<"; retaining last valid scene"<<std::endl;
      window.set_status(L"SNAPSHOT UNAVAILABLE | Retaining the last valid scene and retrying. Authoring Save stays in AI-BS.");
     }
    }else if(changed!=stamp||snapshot_health.pending()){
     try{
      auto replacement=read(source);require(replacement.scope==snapshot.scope,"Viewport document scope changed");require(replacement.chapter.has_value()==snapshot.chapter.has_value(),"Viewport projection mode changed");require(replacement.revision>=snapshot.revision,"Viewport revision rolled back");
      auto projected=project_visual(replacement,asset_root);publish_projection(renderer,projected,projected.placed,placed,replacement.chapter&&replacement.chapter->content.definition().asset_profile==aibs::AssetContentProfile::warm_beginning);
      snapshot=std::move(replacement);scene=std::move(projected.base);picking=std::move(projected.picks);placed=std::move(projected.placed);selected=snapshot.selected_id;animation_seconds=0;stamp=changed;
      if(snapshot_health.recover())std::cerr<<"Snapshot recovered: valid scene adopted"<<std::endl;
      window.set_status(preview_status);emit("READY",snapshot);
     }catch(const std::exception& error){
      const bool transient=dynamic_cast<const SnapshotOpenError*>(&error)!=nullptr;
      if(snapshot_health.failure(now,error.what(),transient)){
       std::cerr<<(transient?"Snapshot unavailable: ":"Snapshot rejected: ")<<error.what()<<"; retaining last valid scene"<<std::endl;
       window.set_status(transient?L"SNAPSHOT UNAVAILABLE | Retaining the last valid scene and retrying.":L"SNAPSHOT REJECTED | Retaining the last valid scene; check AI-BS authoring diagnostics.");
      }
     }
    }
   }
   if(window.minimized()){std::this_thread::sleep_for(std::chrono::milliseconds(20));continue;}
   if(probe&&frames==1){if(snapshot.chapter)focus_probe(camera,picking,snapshot.selected_id);SendMessageW(static_cast<HWND>(window.native_handle()),WM_LBUTTONDOWN,MK_LBUTTON,MAKELPARAM(window.width()/2,window.height()/2));SendMessageW(static_cast<HWND>(window.native_handle()),WM_LBUTTONUP,0,MAKELPARAM(window.width()/2,window.height()/2));}
   const auto input=window.input();if(input.active||probe){camera.update(input,seconds);if(input.cycle_camera)fit(camera,picking);
    if(input.interact){const auto direction=ray(camera,input.pointer_interact?input.pointer_x:0,input.pointer_interact?input.pointer_y:0,static_cast<float>(window.width())/static_cast<float>(window.height()));const auto hit=aibs::pick_scene(picking,camera.position,direction,1000000);selected=hit?hit->persistent_id:"";emit("PICK",snapshot,selected);}
   }
   aibs::SceneSnapshot highlight{scene.world_id,scene.revision,{}};
   for(const auto& object:scene.objects)if(object.persistent_id==selected){auto o=object;o.color={1,.64f,.1f};o.emission=.5f;
    o.half_extent.x+=std::max(.005f,o.half_extent.x*.002f);o.half_extent.y+=std::max(.005f,o.half_extent.y*.002f);o.half_extent.z+=std::max(.005f,o.half_extent.z*.002f);highlight.objects.push_back(o);}
   auto highlighted=aibs::mesh_from_snapshot(highlight);
   if(placed){const auto edges=placed->selection_mesh(selected);highlighted.vertices.insert(highlighted.vertices.end(),edges.vertices.begin(),edges.vertices.end());}
   if(input.active||probe)animation_seconds+=std::min(static_cast<double>(seconds),4./60);
   const auto character=character_instance(snapshot,placed,animation_seconds);
   if(character)renderer.render(camera,highlighted.vertices.size()<=aibs::Dx12Renderer::transient_vertex_limit?highlighted:aibs::SceneMesh{},*character);
   else if(highlighted.vertices.size()<=aibs::Dx12Renderer::transient_vertex_limit)renderer.render(camera,highlighted);else renderer.render(camera);
   if(probe&&frames==0){auto before=capture;before+=L".unselected.bmp";renderer.capture(before);}
   if(probe&&++frames>=6){require(!selected.empty(),"Actual Win32 click did not select geometry");const auto pixels=renderer.capture(capture);renderer.wait_idle();const auto stats=renderer.stats();require(stats.debug_errors==0,"GPU debug errors");std::ofstream out(report);out<<"{\"nonbackground_pixels\":"<<pixels<<",\"debug_errors\":"<<stats.debug_errors<<",\"debug_warnings\":"<<stats.debug_warnings<<",\"character_frames\":"<<stats.character_frames<<",\"character_kind\":\""<<(placed&&placed->companion_model()?"cooked_character":"none")<<"\",\"debug_layer\":"<<(stats.debug_layer?"true":"false")<<",\"world_id\":\""<<scene.world_id<<"\",\"selected_uuid\":\""<<selected<<"\"}";require(out.good(),"Report write failed");break;}
   std::this_thread::sleep_for(std::chrono::milliseconds(8));
  }
  renderer.wait_idle();return 0;
 }catch(const std::exception& error){std::cerr<<"Creator viewport: "<<error.what()<<'\n';return 1;}
}
