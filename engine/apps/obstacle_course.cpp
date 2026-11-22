#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <aibs/movement_course.hpp>
#include <aibs/persistence.hpp>
#include <aibs/player.hpp>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>
#include <stdexcept>
#include <thread>

namespace {
void require(bool ok,const char* message) { if(!ok) throw std::runtime_error(message); }
std::string quoted(const std::string& input) {
 std::string out="\"";
 for(unsigned char c:input) { if(c=='"'||c=='\\') out+='\\'; if(c>=32) out+=static_cast<char>(c); }
 return out+'"';
}
std::string utc() {
 SYSTEMTIME t{};GetSystemTime(&t);char out[48]{};
 std::snprintf(out,sizeof(out),"%04u-%02u-%02uT%02u:%02u:%02u+00:00",t.wYear,t.wMonth,t.wDay,t.wHour,t.wMinute,t.wSecond);return out;
}
std::filesystem::path binary_directory() {
 std::wstring out(32768,L'\0');const auto n=GetModuleFileNameW(nullptr,out.data(),static_cast<DWORD>(out.size()));
 require(n && n<out.size(),"Cannot locate course executable");out.resize(n);return std::filesystem::path(out).parent_path();
}
std::filesystem::path course_slot() {
 std::wstring out(32768,L'\0');const auto n=GetEnvironmentVariableW(L"LOCALAPPDATA",out.data(),static_cast<DWORD>(out.size()));
 require(n && n<out.size(),"LOCALAPPDATA unavailable; supply --checkpoint");out.resize(n);
 return std::filesystem::path(out)/"AI-BS/MovementCourse/native-course.aibs";
}
std::wstring wide(const std::string& text) {
 if(text.empty()) return {};
 const auto n=MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,text.data(),static_cast<int>(text.size()),nullptr,0);
 if(!n) return L"Text unavailable";
 std::wstring out(static_cast<std::size_t>(n),L'\0');MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,text.data(),static_cast<int>(text.size()),out.data(),n);return out;
}
void validate_course(const aibs::CreatorSession& candidate) { (void)aibs::movement_course_scene(candidate); }
aibs::Vec3 forward(const aibs::Camera& camera) {
 return {std::sin(camera.yaw)*std::cos(camera.pitch),std::sin(camera.pitch),std::cos(camera.yaw)*std::cos(camera.pitch)};
}
aibs::Vec3 aim(const aibs::Camera& camera,const aibs::WindowInput& input,float aspect) {
 if(!input.pointer_interact) return forward(camera);
 const float sy=std::sin(camera.yaw),cy=std::cos(camera.yaw),sp=std::sin(camera.pitch),cp=std::cos(camera.pitch);
 const float scale=std::tan(3.14159265358979323846f/8);
 return {sy*cp+input.pointer_x*scale*aspect*cy-input.pointer_y*scale*sy*sp,
         sp+input.pointer_y*scale*cp,
         cy*cp-input.pointer_x*scale*aspect*sy-input.pointer_y*scale*cy*sp};
}
constexpr aibs::Vec3 spawn{-32,.2f,-28};
aibs::SceneMesh proxy(const aibs::SceneSnapshot& snapshot,const aibs::PlayerController& player) {
 if(!player.avatar_visible()) return {};
 const auto p=player.state().feet;
 return aibs::mesh_from_snapshot({snapshot.world_id,snapshot.revision,{{snapshot.world_id,"BS temporary proxy",{p.x,p.y+.9f,p.z},{.3f,.9f,.3f},{.8f,.5f,.18f},0,false}}});
}
void tick(aibs::PlayerController& player,aibs::WindowInput input,int count) { for(int i=0;i<count;++i) player.update(input,1.0/60); }
aibs::Result interact(aibs::CreatorSession& session,const aibs::SceneSnapshot& snapshot,
                      const aibs::Camera& camera,const aibs::WindowInput& input,float aspect) {
 if(!input.interact) return {false,"No interaction press",session.revision()};
 const auto hit=aibs::pick_scene(snapshot,camera.position,aim(camera,input,aspect),25);
 return hit?aibs::restore_movement_course(session,hit->persistent_id)
           :aibs::Result{false,"Aim at the relay core on the CPU deck and press E.",session.revision()};
}
void stage_report(const std::filesystem::path& file,const std::string& stage,const aibs::CreatorSession& session,
                  const aibs::SceneSnapshot& scene,const aibs::RenderStats& gpu,std::uint64_t pixels,const std::map<std::string,bool>& checks) {
 std::ofstream out(file);
 out<<"{\"schema_version\":1,\"status\":\"passed\",\"stage\":"<<quoted(stage)<<",\"completed_at\":"<<quoted(utc())
    <<",\"adapter\":"<<quoted(gpu.adapter)<<",\"world_id\":"<<quoted(session.world_id())<<",\"checkpoint_id\":"<<quoted(session.checkpoint_id())
    <<",\"revision\":"<<session.revision()<<",\"memory_events\":"<<session.memory().events().size()<<",\"entity_ids\":{";
 bool first=true;for(const auto& [alias,e]:session.world()) { if(!first) out<<',';first=false;out<<quoted(alias)<<':'<<quoted(e.persistent_id); }
 const auto& q=session.world().at("ramp-20").fields;
 out<<"},\"ramp_rotation\":["<<q.at("qx")<<','<<q.at("qy")<<','<<q.at("qz")<<','<<q.at("qw")<<"],\"target_state\":"<<session.world().at("relay-core").fields.at("state")
    <<",\"object_count\":"<<scene.objects.size()<<",\"metrics\":{";
 first=true;for(const auto& [name,passed]:checks) { if(!first) out<<',';first=false;out<<quoted(name)<<':'<<(passed?"true":"false"); }
 if(!first) out<<',';
 out<<"\"debug_errors\":"<<gpu.debug_errors<<",\"debug_layer\":"<<(gpu.debug_layer?"true":"false")<<",\"capture_pixels\":"<<pixels
    <<",\"walkable_slope_degrees\":20,\"steep_slope_degrees\":60},\"checks\":[";
 first=true;for(const auto& [name,passed]:checks) if(passed) { if(!first) out<<',';first=false;out<<quoted(name+" verified in "+stage+" process"); }
 out<<"]}";require(out.good(),"Could not publish course stage result");
}
}

int run_obstacle_course(int argc,wchar_t** argv) {
 std::filesystem::path slot,capture,report;std::string test;
 try {
  for(int i=1;i<argc;++i) {
   const std::wstring flag(argv[i]);if(flag==L"--obstacle-course") continue;
   require(i+1<argc,"Course option needs a value");
   if(flag==L"--checkpoint") slot=argv[++i];
   else if(flag==L"--capture") capture=argv[++i];
   else if(flag==L"--course-report") report=argv[++i];
   else if(flag==L"--course-test") {
    const std::wstring v(argv[++i]);
    if(v==L"traverse") test="traverse";else if(v==L"restart") test="restart";else test="invalid";
   }
   else throw std::invalid_argument("Unknown obstacle-course option");
  }
  const bool automated=!test.empty();
  require(!automated||test=="traverse"||test=="restart","Course test must be traverse or restart");
  require(!automated||(!slot.empty()&&!capture.empty()&&!report.empty()),"Automated course needs explicit checkpoint, capture and report paths");
  if(slot.empty()) slot=course_slot();
  if(!slot.parent_path().empty()) std::filesystem::create_directories(slot.parent_path());
  if(automated) {
   if(!report.parent_path().empty()) std::filesystem::create_directories(report.parent_path());
   if(!capture.parent_path().empty()) std::filesystem::create_directories(capture.parent_path());
   std::ofstream started(report);started<<"{\"schema_version\":1,\"status\":\"failed\",\"completed_at\":"<<quoted(utc())<<",\"checks\":[\"Course stage has not completed\"]}";
  }
  aibs::CreatorSession session(aibs::movement_course_schema(),"movement-course","main");
  const bool existed=std::filesystem::exists(slot);
  require(test!="restart"||existed,"Restart stage requires an existing course checkpoint");
  if(existed) { const auto r=aibs::CheckpointStore::load(slot,session,validate_course);require(r.ok,r.message.c_str()); }
  else {
   const auto seeded=aibs::seed_movement_course(session);require(seeded.ok,seeded.message.c_str());
   const auto saved=aibs::CheckpointStore::save(slot,session);require(saved.ok,saved.message.c_str());
  }
  auto snapshot=aibs::movement_course_scene(session);
  SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);
  aibs::NativeWindow window(automated?960u:1440u,automated?640u:900u,L"AI-BS motherboard movement course | WASD walk | Space jump | V camera | E repair | F9 reload",!automated);
  aibs::Dx12Renderer renderer(window,aibs::mesh_from_snapshot(snapshot),binary_directory()/"shaders");
  aibs::PlayerController player(snapshot,spawn);
  if(automated) {
   std::map<std::string,bool> checks;
   if(test=="traverse") {
    const auto initial_revision=session.revision();const auto initial_events=session.memory().events();
    aibs::WindowInput go;go.forward=1;
    player.reset({-18,.05f,-28});tick(player,{},30);tick(player,go,80);
    std::cout<<"stairs feet "<<player.state().feet.x<<','<<player.state().feet.y<<','<<player.state().feet.z<<'\n';
    require(player.state().feet.z>-21 && player.state().feet.y>.85f,"Socket stairs failed to support BS");checks["steps"]=true;
    player.reset({0,.05f,-23});tick(player,{},30);
    bool supported=true;for(int i=0;i<150;++i) { player.update(go,1.0/60);supported=supported&&player.state().grounded; }
    std::cout<<"ramp feet "<<player.state().feet.x<<','<<player.state().feet.y<<','<<player.state().feet.z<<" supported="<<supported<<'\n';
    require(supported && std::abs(player.state().feet.y-4.10424f)<.1f && player.state().feet.z>-8.5f,"BS failed supported ascent and upper-platform transition");
    for(int frame=0;frame<3;++frame) renderer.render(player.camera());
    auto slope_capture=capture;slope_capture+=L".slope.bmp";require(renderer.capture(slope_capture)>10000,"Slope traversal GPU capture was blank");
    aibs::WindowInput back;back.forward=-1;tick(player,back,170);
    require(player.state().feet.y<.1f && player.state().grounded,"BS failed descent and lower-floor transition");
    player.reset({18,.05f,-21});tick(player,{},30);tick(player,go,120);
    std::cout<<"steep feet "<<player.state().feet.x<<','<<player.state().feet.y<<','<<player.state().feet.z<<'\n';
    require(player.state().feet.y<.5f && player.state().feet.z<-17.7f,"60 degree surface allowed unsupported forced ascent");checks["slopes"]=true;
    player.reset({-12,.05f,15});tick(player,{},30);tick(player,go,120);
    require(player.state().feet.z>18.5f && player.state().feet.z<19.1f,"GPU wall did not block BS");checks["walls"]=true;
    player.reset({42,.05f,34});tick(player,{},30);tick(player,go,90);
    require(player.state().feet.z>37 && player.state().feet.y<-1 && !player.state().grounded,"Motherboard edge did not produce a fall");
    player.reset(spawn);tick(player,{},30);require(player.state().grounded,"Fall recovery did not restore supported play");checks["falls"]=true;
    auto handle=static_cast<HWND>(window.native_handle());
    SendMessageW(handle,WM_KEYDOWN,'W',0);SendMessageW(handle,WM_KEYDOWN,VK_SPACE,0);
    auto edge=window.input();require(edge.jump&&!window.input().jump,"Space input was not edge triggered");
    player.update(edge,0);
    SendMessageW(handle,WM_ACTIVATEAPP,FALSE,0);auto inactive=window.input();
    const auto before=player.state();player.update(inactive,60);
    require(!inactive.active&&inactive.forward==0&&player.state().ticks==before.ticks&&player.state().feet==before.feet,"Focus loss advanced the course or retained controls");
    SendMessageW(handle,WM_ACTIVATEAPP,TRUE,0);player.update(window.input(),1.0/60);
    require(player.state().grounded,"Focus restore replayed a queued jump");
    window.minimize();window.poll();const auto prior_frames=renderer.stats().frames;renderer.render(player.camera());
    require(window.minimized()&&renderer.stats().frames==prior_frames,"Minimized course submitted a GPU frame");
    aibs::WindowInput pause;pause.active=false;player.update(pause,0);window.restore(false);window.poll();checks["focus"]=true;
    SendMessageW(handle,WM_ACTIVATEAPP,TRUE,0);
    require(session.revision()==initial_revision&&session.memory().events()==initial_events,"Locomotion changed authoring or Adam history");
    player.reset({0,4.12f,-8});tick(player,{},30);
    aibs::WindowInput look;look.pitch_delta=-.38f;player.update(look,0);
    const auto hit=aibs::pick_scene(snapshot,player.camera().position,forward(player.camera()));
    require(hit&&hit->persistent_id==session.world().at("relay-core").persistent_id,"Core interaction did not target its actual rendered surface");
    SendMessageW(handle,WM_KEYDOWN,'E',0);const auto pressed=window.input();require(pressed.interact&&!window.input().interact,"Course interaction key repeated without a press");SendMessageW(handle,WM_KEYUP,'E',0);
    const auto repaired=interact(session,snapshot,player.camera(),pressed,static_cast<float>(window.width())/static_cast<float>(window.height()));require(repaired.ok,repaired.message.c_str());
    const auto saved=aibs::CheckpointStore::save(slot,session);require(saved.ok,saved.message.c_str());checks["interaction"]=true;
    snapshot=aibs::movement_course_scene(session);renderer.set_scene(aibs::mesh_from_snapshot(snapshot));
   } else {
    require(session.world().at("relay-core").fields.at("state")==100&&session.memory().events().size()==2,"Restart lost or duplicated recorded repair");
    tick(player,{},60);require(player.state().grounded,"Restarted course player did not settle");checks["restart"]=true;
   }
   aibs::Camera overview;
   for(int frame=0;frame<3;++frame) { window.poll();renderer.render(overview); }
   const auto pixels=renderer.capture(capture);require(pixels>10000,"Course GPU capture was blank");renderer.wait_idle();const auto gpu=renderer.stats();require(gpu.debug_errors==0,"Course GPU validation failed");
   stage_report(report,test,session,snapshot,gpu,pixels,checks);
   std::cout<<"PASS: motherboard course "<<test<<" on "<<gpu.adapter<<'\n';return 0;
  }
  std::string notice="Traversal yard: cyan ramp is 20 degrees; red barrier is 60. Adam lines here are authored game guidance.";
  auto saved_revision=session.revision();auto previous=std::chrono::steady_clock::now();
  while(window.poll()) {
   const auto now=std::chrono::steady_clock::now();const double elapsed=std::chrono::duration<double>(now-previous).count();previous=now;
   auto input=window.input();if(window.minimized()) input.active=false;
   if(!input.active) { player.update(input,0);std::this_thread::sleep_for(std::chrono::milliseconds(20));continue; }
   player.update(input,elapsed);if(player.state().feet.y<-20) { player.reset(spawn);notice="Returned to the motherboard entrance after falling."; }
   if(input.reload) {
    auto candidate=session;const auto loaded=aibs::CheckpointStore::load(slot,candidate,validate_course);notice=loaded.message;
    if(loaded.ok) {
     try {
      auto next=aibs::movement_course_scene(candidate);aibs::PlayerController replacement(next,spawn);
      renderer.set_scene(aibs::mesh_from_snapshot(next));player=std::move(replacement);session=std::move(candidate);snapshot=std::move(next);saved_revision=session.revision();
     } catch(const std::invalid_argument& e) { notice=std::string("Reload blocked: ")+e.what(); }
    }
   } else if(input.interact) {
     auto candidate=session;const auto r=interact(candidate,snapshot,player.camera(),input,static_cast<float>(window.width())/static_cast<float>(window.height()));notice=r.message;
     if(candidate.revision()!=session.revision()) {
      auto next=aibs::movement_course_scene(candidate);player.set_scene(next);renderer.set_scene(aibs::mesh_from_snapshot(next));session=std::move(candidate);snapshot=std::move(next);
      const auto saved=aibs::CheckpointStore::save(slot,session);if(saved.ok) saved_revision=session.revision();else notice="UNSAVED: "+saved.message;
     }
   } else if(input.save) {
    const auto saved=aibs::CheckpointStore::save(slot,session);notice=saved.message;if(saved.ok) saved_revision=session.revision();
   }
   window.set_status(L"WASD walk | Right-drag look | Space jump | Shift sprint | V camera | F2 inspect\nE repair core | F5 save | F9 reload/return | Esc close\nAdam: Follow the cyan CPU ramp; the red surface is too steep.\n"
    +(saved_revision==session.revision()?std::wstring(L"SAVED | "):std::wstring(L"UNSAVED | "))+wide(notice));
   renderer.render(player.camera(),proxy(snapshot,player));
  }
  renderer.wait_idle();return 0;
 } catch(const std::exception& e) {
  std::cerr<<"Obstacle course failed: "<<e.what()<<'\n';
  if(test.empty()) MessageBoxW(nullptr,wide(e.what()).c_str(),L"AI-BS course could not continue",MB_OK|MB_ICONERROR);
  return 1;
 }
}
