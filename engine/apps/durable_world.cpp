#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <aibs/durable_first_boot.hpp>
#include <aibs/first_boot_chapter.hpp>
#include <aibs/first_boot_content.hpp>
#include <aibs/placed_assets.hpp>
#include <aibs/content_lighting.hpp>
#include <aibs/companion_runtime.hpp>
#include <aibs/guide_presentation.hpp>
#include <aibs/guide_camera.hpp>
#include <aibs/memory_playback.hpp>
#include <aibs/opening_inspections.hpp>
#include <aibs/initial_view.hpp>
#include <aibs/frame_measurement.hpp>
#include <aibs/opening_tour.hpp>
#include <psapi.h>
#include <sqlite3.h>
#include <aibs/content_dependencies.hpp>
#include <aibs/gameplay_codec.hpp>
#include <aibs/legacy_import.hpp>
#include <algorithm>
#include <array>
#include <atomic>
#include <chrono>
#include <charconv>
#include <cmath>
#include <condition_variable>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <mutex>
#include <sstream>
#include <stdexcept>
#include <thread>
#include <type_traits>
#include "memory_content_budget.hpp"
#include "video_encoder.hpp"
#include "recording_hud.hpp"
#include "opening_tour_guard.hpp"
#include "performance_readiness.hpp"
#include "controlled_motion.hpp"
#include "performance_phases.hpp"
#include "player_targeting.hpp"
#include "tour_diagnostics.hpp"

namespace {
using namespace aibs;
using Clock=std::chrono::steady_clock;
void require(bool value,const std::string& why) { if(!value) throw std::runtime_error(why); }
std::string quoted(const std::string& source) {
 std::string out="\"";constexpr char hex[]="0123456789abcdef";
 for(unsigned char ch:source) {
  if(ch=='"'||ch=='\\') { out+='\\';out+=static_cast<char>(ch); }
  else if(ch<32) { out+="\\u00";out+=hex[ch>>4];out+=hex[ch&15]; }
  else out+=static_cast<char>(ch);
 }
 return out+'"';
}
std::wstring wide(const std::string& text) {
 if(text.empty()) return {};
 const int count=MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,text.data(),static_cast<int>(text.size()),nullptr,0);
 if(!count) return L"Text unavailable";
 std::wstring result(static_cast<std::size_t>(count),L'\0');
 MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,text.data(),static_cast<int>(text.size()),result.data(),count);return result;
}
std::string narrow(std::wstring_view text) {
 const auto count=WideCharToMultiByte(CP_UTF8,WC_ERR_INVALID_CHARS,text.data(),static_cast<int>(text.size()),nullptr,0,nullptr,nullptr);
 require(count>0,"Invalid command text");std::string result(static_cast<std::size_t>(count),'\0');
 require(WideCharToMultiByte(CP_UTF8,WC_ERR_INVALID_CHARS,text.data(),static_cast<int>(text.size()),result.data(),count,nullptr,nullptr)==count,"Invalid command text");return result;
}
std::string utc() {
 SYSTEMTIME t{};GetSystemTime(&t);char text[48]{};
 std::snprintf(text,sizeof(text),"%04u-%02u-%02uT%02u:%02u:%02u+00:00",t.wYear,t.wMonth,t.wDay,t.wHour,t.wMinute,t.wSecond);return text;
}
std::filesystem::path environment_directory() {
 std::wstring value(32768,L'\0');const auto size=GetEnvironmentVariableW(L"LOCALAPPDATA",value.data(),static_cast<DWORD>(value.size()));
 require(size&&size<value.size(),"LOCALAPPDATA unavailable; supply --world-db PATH");value.resize(size);return value;
}
std::filesystem::path shaders() {
 std::wstring value(32768,L'\0');const auto size=GetModuleFileNameW(nullptr,value.data(),static_cast<DWORD>(value.size()));
 require(size&&size<value.size(),"Cannot locate native executable");value.resize(size);return std::filesystem::path(value).parent_path()/"shaders";
}
struct Options {
 std::filesystem::path database,capture,report,request,import_source,proof_gate,content_definition,stop_file,asset_root;
 std::string project,branch,play_session,timeline_id;
 std::wstring step;
 bool chapter=false,upgrade_chapter=false,persistent_play=false;
 std::uint32_t width=0,height=0;
 std::filesystem::path performance_report;
 double performance_seconds=15,performance_warmup=2;
 bool performance_timing_supplied=false;
 bool performance_gameplay=false;
 bool performance_controlled_motion=false;
 bool walkthrough=false;
 std::filesystem::path record_mp4,record_ffmpeg;
 std::string record_encoder="auto";
 bool recording()const noexcept{return !record_mp4.empty();}
 std::filesystem::path tour_bindings;
 std::string tour_route="repair";
 double walkthrough_read_seconds=8;
 bool offscreen_tour_proof=false;
 std::string offscreen_camera;
 std::filesystem::path input_trace;
 bool ordinary_input_trace=false;
 bool performance()const noexcept{return !performance_report.empty();}
 std::uint32_t window_width()const noexcept{return width?width:proof()?960u:1440u;}
 std::uint32_t window_height()const noexcept{return height?height:proof()?640u:900u;}
 bool proof() const { return !step.empty(); }
 bool managed() const { return !content_definition.empty(); }
};
Options options(int argc,wchar_t** argv) {
 Options o;
 const auto unsigned_value=[](std::wstring_view text){const auto value=narrow(text);std::uint32_t number=0;const auto parsed=std::from_chars(value.data(),value.data()+value.size(),number);require(parsed.ec==std::errc{}&&parsed.ptr==value.data()+value.size(),"Expected a bounded unsigned display size");return number;};
 const auto seconds_value=[](std::wstring_view text){const auto value=narrow(text);double number=0;const auto parsed=std::from_chars(value.data(),value.data()+value.size(),number);require(parsed.ec==std::errc{}&&parsed.ptr==value.data()+value.size()&&std::isfinite(number),"Expected finite diagnostic seconds");return number;};
 for(int i=1;i<argc;++i) {
  const std::wstring flag(argv[i]);if(flag==L"--durable-world") continue;
  if(flag==L"--chapter") { o.chapter=true;continue; }
  if(flag==L"--upgrade-chapter") { o.upgrade_chapter=true;continue; }
  if(flag==L"--walkthrough") { o.walkthrough=true;continue; }
  if(flag==L"--offscreen-tour-proof") { require(!o.offscreen_tour_proof,"Duplicate offscreen proof option");o.offscreen_tour_proof=true;continue; }
  if(flag==L"--persistent-play") { require(!o.persistent_play,"Duplicate --persistent-play option");o.persistent_play=true;continue; }
  if(flag==L"--performance-gameplay") {require(!o.performance_gameplay,"Duplicate gameplay performance option");o.performance_gameplay=true;continue;}
  if(flag==L"--performance-controlled-motion") {require(!o.performance_controlled_motion,"Duplicate controlled motion option");o.performance_controlled_motion=true;continue;}
  require(i+1<argc,"A durable-world option is missing its value");
  if(flag==L"--world-db"||flag==L"--database") o.database=argv[++i];
  else if(flag==L"--content-definition") o.content_definition=argv[++i];
  else if(flag==L"--asset-root") o.asset_root=argv[++i];
  else if(flag==L"--stop-file") o.stop_file=argv[++i];
  else if(flag==L"--project") o.project=narrow(argv[++i]);
  else if(flag==L"--branch") o.branch=narrow(argv[++i]);
  else if(flag==L"--play-session") o.play_session=narrow(argv[++i]);
  else if(flag==L"--timeline-id") {require(o.timeline_id.empty(),"Duplicate --timeline-id option");o.timeline_id=narrow(argv[++i]);}
  else if(flag==L"--capture") o.capture=argv[++i];
  else if(flag==L"--durable-report") o.report=argv[++i];
  else if(flag==L"--request-file") o.request=argv[++i];
  else if(flag==L"--import-checkpoint") o.import_source=argv[++i];
  else if(flag==L"--proof-gate") o.proof_gate=argv[++i];
  else if(flag==L"--durable-step") o.step=argv[++i];
  else if(flag==L"--width") o.width=unsigned_value(argv[++i]);
  else if(flag==L"--height") o.height=unsigned_value(argv[++i]);
  else if(flag==L"--performance-report") o.performance_report=argv[++i];
  else if(flag==L"--performance-seconds"){o.performance_seconds=seconds_value(argv[++i]);o.performance_timing_supplied=true;}
  else if(flag==L"--performance-warmup"){o.performance_warmup=seconds_value(argv[++i]);o.performance_timing_supplied=true;}
  else if(flag==L"--record-mp4"){o.record_mp4=argv[++i];o.walkthrough=true;}
  else if(flag==L"--record-ffmpeg")o.record_ffmpeg=argv[++i];
  else if(flag==L"--record-encoder")o.record_encoder=narrow(argv[++i]);
  else if(flag==L"--opening-tour-bindings")o.tour_bindings=argv[++i];
  else if(flag==L"--opening-tour-route")o.tour_route=narrow(argv[++i]);
  else if(flag==L"--walkthrough-read-seconds")o.walkthrough_read_seconds=seconds_value(argv[++i]);
  else if(flag==L"--frame-input-trace"){require(o.input_trace.empty(),"Duplicate frame-input trace option");o.input_trace=argv[++i];}
  else if(flag==L"--ordinary-input-trace"){require(o.input_trace.empty(),"Duplicate input trace option");o.input_trace=argv[++i];o.ordinary_input_trace=true;}
  else if(flag==L"--offscreen-camera"){require(o.offscreen_camera.empty(),"Duplicate offscreen camera option");o.offscreen_camera=narrow(argv[++i]);}
  else throw std::invalid_argument("Unknown durable-world option");
 }
 require(!o.persistent_play||(o.managed()&&is_uuid(o.timeline_id)),"Persistent Play requires managed content and a canonical stable --timeline-id UUID");
 require(o.persistent_play||o.timeline_id.empty(),"--timeline-id requires --persistent-play");
 require(!o.persistent_play||!o.proof(),"Persistent Play cannot run destructive proof/fault-injection steps against a retained player slot");
 if(o.managed()) {
  require(!o.database.empty()&&!o.stop_file.empty()&&!o.project.empty()&&!o.branch.empty()&&is_uuid(o.play_session),"Managed Play requires explicit --database, --stop-file, --project, --branch and canonical --play-session UUID");
  require(o.import_source.empty()&&!o.upgrade_chapter&&o.request.empty()&&o.proof_gate.empty(),"Managed Play cannot import or migrate a player world");
  require(o.content_definition.extension()==L".aibd"&&std::filesystem::is_regular_file(o.content_definition),"Managed Play requires an existing immutable .aibd definition");
  o.content_definition=std::filesystem::canonical(o.content_definition);o.database=std::filesystem::absolute(o.database).lexically_normal();o.stop_file=std::filesystem::absolute(o.stop_file).lexically_normal();
  require(std::filesystem::is_directory(o.database.parent_path())&&std::filesystem::canonical(o.database.parent_path())==o.database.parent_path(),"Managed Play scratch directory must already exist and be canonical");
  require(o.stop_file.parent_path()==o.database.parent_path()&&o.stop_file!=o.database&&o.database!=o.content_definition&&o.stop_file!=o.content_definition,"Managed Play stop marker must be separate and adjacent to its scratch database");
  require(std::filesystem::weakly_canonical(o.database)==o.database&&!std::filesystem::is_symlink(o.stop_file),"Managed Play paths must not redirect");
  require(!std::filesystem::exists(o.stop_file),"Managed Play stop marker already exists; use a fresh session or explicitly remove the old request");
  if(o.persistent_play) {
   require(o.stop_file.filename()==std::filesystem::path("stop."+o.play_session+".request"),"Persistent Play requires its invocation-specific adjacent stop.<play_session>.request marker");
   const auto lock=o.database.parent_path()/L"player.lock";
   require(lock!=o.database&&lock!=o.stop_file&&lock!=o.content_definition,"Persistent Play lock must be distinct from database, content and stop marker");
  }
  o.chapter=true;
 } else require(o.stop_file.empty()&&o.project.empty()&&o.branch.empty()&&o.play_session.empty()&&o.asset_root.empty(),"Managed Play arguments require --content-definition");
 require((o.width==0)==(o.height==0),"Supply --width and --height together");
 require(!o.width||(o.managed()&&o.width>=640&&o.width<=3840&&o.height>=480&&o.height<=2160),"Explicit display sizes require managed Play and client640..3840 by480..2160");
 require(!o.performance_timing_supplied||o.performance(),"Performance timing requires --performance-report");
 require(!o.performance_gameplay||o.performance(),"Gameplay performance requires --performance-report");
 if(o.performance_controlled_motion)require(controlled_motion::allowed(o.performance(),o.performance_gameplay,o.managed(),!std::filesystem::exists(o.database),o.proof(),o.walkthrough,o.recording(),o.offscreen_tour_proof),
  "Controlled motion requires a fresh explicit managed database and performance report, separate from ordinary gameplay, proof, tour, recording and offscreen modes");
 require(o.tour_route=="repair"||o.tour_route=="bypass","Tour route must be repair or bypass");
 require(o.walkthrough_read_seconds>=2&&o.walkthrough_read_seconds<=30,"Walkthrough read dwell must be2..30 real seconds; ordinary Play has no reading timer");
 if(o.walkthrough||o.step==L"opening-tour"){
  require(o.managed()&&!o.tour_bindings.empty()&&!o.capture.empty()&&!o.report.empty()&&!o.performance(),"Tour requires explicit managed content, pinned bindings, capture/report and no concurrent performance sampling");
  require(!o.walkthrough||!o.proof(),"Real walkthrough is a live wall-clock mode, separate from synthetic proof steps");
  o.tour_bindings=std::filesystem::absolute(o.tour_bindings).lexically_normal();
  require(o.tour_bindings.extension()==L".aibtour"&&o.tour_bindings.parent_path()==o.content_definition.parent_path()&&std::filesystem::is_regular_file(o.tour_bindings)&&!std::filesystem::is_symlink(o.tour_bindings)&&std::filesystem::canonical(o.tour_bindings)==o.tour_bindings&&std::filesystem::file_size(o.tour_bindings)<=4096,"Tour bindings must be a bounded existing owned chapter sidecar");
 }else require(o.tour_bindings.empty(),"Tour sidecar is diagnostic-only and requires a tour proof or --walkthrough mode");
 require(!o.offscreen_tour_proof||(o.managed()&&o.step==L"opening-tour"&&!o.walkthrough&&!o.persistent_play&&!o.input_trace.empty()&&!std::filesystem::exists(o.database)),
  "Offscreen tour is a controlled synthetic proof only: fresh explicit managed scratch database, opening-tour step and input trace required");
 require(o.offscreen_camera.empty()||(o.offscreen_tour_proof&&(o.offscreen_camera=="first-person"||o.offscreen_camera=="third-person")),"Offscreen camera requires its controlled proof and first-person or third-person mode");
 if(o.offscreen_tour_proof&&o.offscreen_camera.empty())o.offscreen_camera="first-person";
 if(o.offscreen_tour_proof){
  o.capture=std::filesystem::absolute(o.capture).lexically_normal();o.report=std::filesystem::absolute(o.report).lexically_normal();
  require(o.capture.extension()==L".bmp"&&o.report.extension()==L".json"&&o.capture.parent_path()==o.database.parent_path()&&o.report.parent_path()==o.database.parent_path()
   &&o.capture!=o.report&&o.capture!=o.database&&o.report!=o.database&&o.capture!=o.stop_file&&o.report!=o.stop_file
   &&!std::filesystem::exists(o.capture)&&!std::filesystem::exists(o.report)&&!std::filesystem::is_symlink(o.capture)&&!std::filesystem::is_symlink(o.report),
   "Offscreen proof capture/report must be new distinct adjacent owned BMP/JSON files; retained evidence is never overwritten");
 }
 if(o.ordinary_input_trace)require(tour_diagnostic::ordinary_input_trace_allowed(o.managed(),o.proof(),o.walkthrough,o.recording(),o.performance(),o.offscreen_tour_proof),
  "Ordinary input trace requires explicit managed ordinary Play, without proof, walkthrough, recording, performance or controlled input");
 if(!o.input_trace.empty()){
  require(o.managed()&&(o.ordinary_input_trace||o.walkthrough||o.step==L"opening-tour"),"Frame-input trace requires the explicit managed tour diagnostic or ordinary input observation");
  o.input_trace=std::filesystem::absolute(o.input_trace).lexically_normal();
  require(o.input_trace.extension()==L".jsonl"&&o.input_trace.parent_path()==o.database.parent_path()&&!std::filesystem::exists(o.input_trace)&&!std::filesystem::is_symlink(o.input_trace)&&o.input_trace!=o.database&&o.input_trace!=o.stop_file&&o.input_trace!=o.report&&o.input_trace!=o.capture,
   "Input trace must be a new adjacent owned JSONL file separate from database/report/capture/stop");
 }
 if(o.recording()){
  require(o.managed()&&!o.proof()&&o.width&&o.height&&!o.performance(),"Recording requires managed real walkthrough, explicit client dimensions and no performance sampler");
  require(o.record_encoder=="auto"||o.record_encoder=="nvenc"||o.record_encoder=="software","Recording encoder must be auto, nvenc or software");
  o.record_mp4=std::filesystem::absolute(o.record_mp4).lexically_normal();o.record_ffmpeg=std::filesystem::absolute(o.record_ffmpeg).lexically_normal();
  require(o.record_mp4.extension()==L".mp4"&&o.record_mp4.parent_path()==o.database.parent_path()&&!std::filesystem::exists(o.record_mp4)&&!std::filesystem::is_symlink(o.record_mp4),"Recording must be a NEW adjacent owned MP4");
  require(std::filesystem::is_regular_file(o.record_ffmpeg)&&o.record_ffmpeg.extension()==L".exe","Recording requires an explicit installed trusted ffmpeg executable");
 }else require(o.record_ffmpeg.empty()&&o.record_encoder=="auto","Encoder configuration requires --record-mp4");
 if(o.performance()){
  require(o.managed()&&!o.proof()&&o.width&&o.height,"Performance capture requires managed live Play, explicit client dimensions and no synthetic --durable-step");
  require(o.performance_seconds>=15&&o.performance_seconds<=((o.performance_gameplay||o.performance_controlled_motion)?900:120)&&o.performance_warmup>=2&&o.performance_warmup<=30,"Performance requires15..120 stationary or15..900 gameplay/controlled-motion wall seconds and2..30 warmup seconds");
  o.performance_report=std::filesystem::absolute(o.performance_report).lexically_normal();
  require(o.performance_report.extension()==L".json"&&o.performance_report.parent_path()==o.database.parent_path()&&!std::filesystem::exists(o.performance_report)&&!std::filesystem::is_symlink(o.performance_report)&&o.performance_report!=o.database&&o.performance_report!=o.stop_file,"Performance report must be a new adjacent owned JSON file");
 }
 // Destructive/fault-injection verification must never inherit a player's slot.
 if(o.proof()) require(!o.database.empty(),"Native verification requires an explicit --world-db PATH");
 require(!o.upgrade_chapter||o.chapter,"--upgrade-chapter requires --chapter");
 if(o.database.empty()) o.database=environment_directory()/(o.chapter?"AI-BS/FirstBootChapter/world.sqlite":"AI-BS/FirstBootDurableWorld/world.sqlite");
 if(o.proof()) {
  require(!o.capture.empty()&&!o.report.empty(),"Durable proof requires --capture and --durable-report");
  const std::vector<std::wstring> steps=o.managed()?std::vector<std::wstring>{L"seed",L"inspect",L"reload",L"content-route",L"repair-route",L"bypass-route",L"companion-controls",L"memory-controls",L"opening-controls",L"opening-tour",L"door-cycle",L"help",L"decline",L"depart-return",L"feed-loss",L"fall-return",L"relay-rebuild",L"stop-drain"}:o.chapter?std::vector<std::wstring>{L"seed",L"inspect",L"reload",L"repair-route",L"bypass-route",L"door-cycle",L"help",L"decline",L"depart-return",L"feed-loss",L"fall-return",L"relay-rebuild",L"hazard",L"remote-nodes",L"translated-walk",L"reload-failure",L"fail-retry",L"close-drain"}:
   std::vector<std::wstring>{L"seed",L"inspect",L"reload",L"repair",L"build",L"dismantle",L"retry",L"fail-retry",L"close-drain",L"before-commit",L"after-commit"};
  require(std::find(steps.begin(),steps.end(),o.step)!=steps.end(),"Unknown durable verification step");
 }
 require(o.request.empty()||(o.proof()&&o.request.extension()==L".batch"&&
  std::filesystem::weakly_canonical(o.request.parent_path())==std::filesystem::weakly_canonical(o.database.parent_path())),
  "Proof request files must be .batch files beside their explicit database");
 if(o.step==L"retry"||o.step==L"before-commit"||o.step==L"after-commit") require(!o.request.empty(),"This proof requires --request-file PATH.batch");
 require(o.proof_gate.empty()||(o.chapter&&o.proof()&&std::filesystem::weakly_canonical(o.proof_gate.parent_path())==std::filesystem::weakly_canonical(o.database.parent_path())),"Proof gates require an explicit chapter verification database and adjacent path");
 return o;
}
// Lifetime deliberately belongs to run_durable_world, outside run_chapter:
// its archive connection and renderer are destroyed AFTER STOPPED is emitted.
class PersistentSlotLock {
 HANDLE handle_=INVALID_HANDLE_VALUE;
public:
 explicit PersistentSlotLock(const Options& o) {
  if(!o.persistent_play)return;
  const auto path=o.database.parent_path()/L"player.lock";
  handle_=CreateFileW(path.c_str(),GENERIC_READ|GENERIC_WRITE,0,nullptr,OPEN_ALWAYS,
   FILE_ATTRIBUTE_NORMAL|FILE_FLAG_OPEN_REPARSE_POINT,nullptr);
  require(handle_!=INVALID_HANDLE_VALUE,"Persistent player slot is already owned or its lock is unavailable");
  BY_HANDLE_FILE_INFORMATION info{};
  if(!GetFileInformationByHandle(handle_,&info)||(info.dwFileAttributes&(FILE_ATTRIBUTE_REPARSE_POINT|FILE_ATTRIBUTE_DIRECTORY))||GetFileType(handle_)!=FILE_TYPE_DISK) {
   CloseHandle(handle_);handle_=INVALID_HANDLE_VALUE;throw std::runtime_error("Persistent player lock must be a nonredirected regular file");
  }
 }
 ~PersistentSlotLock(){if(handle_!=INVALID_HANDLE_VALUE)CloseHandle(handle_);}
 PersistentSlotLock(const PersistentSlotLock&)=delete;PersistentSlotLock& operator=(const PersistentSlotLock&)=delete;
};
GameplayScope initialize(const Options& o) {
 const auto definitions=durable_first_boot_schemas();
 if(!o.import_source.empty()) {
  require(!std::filesystem::exists(o.database),"Import requires a new database path. Existing durable worlds are never overwritten; launch without --import-checkpoint to resume.");
  const auto imported=import_format1_checkpoint(o.import_source,o.database,first_boot_schema(),"first-boot-world","main",
   definitions,durable_first_boot_components,{},durable_first_boot_validate_source);
  require(imported.ok,"Original checkpoint import failed: "+imported.message);return imported.scope;
 }
 std::vector<GameplayScope> matches;
 if(std::filesystem::exists(o.database)) {
  const auto found=GameplayStore::list_scopes(o.database);
  for(const auto& scope:found) if(scope.project_id=="first-boot-world"&&scope.branch_id=="main"&&scope.context==GameplayContext::player_world) matches.push_back(scope);
  require(matches.size()==1,"The database must contain exactly one First Boot player timeline. Choose its dedicated database; no arbitrary timeline was selected.");
 }
 GameplayScope scope=matches.empty()?GameplayScope{"first-boot-world",new_uuid(),"main",new_uuid(),GameplayContext::player_world}:matches.front();
 GameplayStore store(o.database,scope,definitions);
 if(!store.baseline()) {
  const auto recovered=store.recover();
  require(recovered.revision==0&&recovered.sequence==0&&recovered.components.empty(),"Existing gameplay without an authored baseline needs explicit recovery, not reseeding");
  CreatorSession authored(first_boot_schema(),scope.project_id,scope.branch_id);
  require(seed_first_boot(authored).ok,"Could not author the First Boot foundation");
  const auto seeded=store.seed(durable_first_boot_baseline(authored));
  require(seeded.status==GameplayStoreStatus::committed||seeded.status==GameplayStoreStatus::retry,seeded.message);
 }
 durable_first_boot_validate(store.recover());return scope;
}
struct Gate {
 std::mutex mutex;std::condition_variable changed;bool entered=false,released=false;
 std::atomic<bool> fail_once=true;
 void arrive() {
  std::unique_lock lock(mutex);entered=true;changed.notify_all();
  require(changed.wait_for(lock,std::chrono::seconds(15),[&]{return released;}),"Native save proof rendezvous timed out");
 }
 void await() {
  std::unique_lock lock(mutex);require(changed.wait_for(lock,std::chrono::seconds(15),[&]{return entered;}),"Save worker did not reach the requested commit boundary");
 }
 void release() { { std::lock_guard lock(mutex);released=true; }changed.notify_all(); }
};
GameplayStoreObserver observer(const Options& o,const std::shared_ptr<Gate>& gate) {
 if(o.step==L"fail-retry") return [gate](auto stage) {
  if(stage==GameplayStoreStage::before_commit&&gate->fail_once.exchange(false)) throw std::runtime_error("One-shot native save failure; live changes retained for F5 retry");
 };
 if(o.step==L"before-commit"||o.step==L"after-commit"||o.step==L"close-drain") return [step=o.step,gate](auto stage) {
  if((step==L"after-commit"&&stage==GameplayStoreStage::after_commit)||
     (step!=L"after-commit"&&stage==GameplayStoreStage::before_commit)) {
   gate->arrive();if(step!=L"close-drain") ExitProcess(step==L"before-commit"?73:74);
  }
 };
 return {};
}
Vec3 ray(const Camera& c,float x,float y,float aspect) {
 const float sy=std::sin(c.yaw),cy=std::cos(c.yaw),sp=std::sin(c.pitch),cp=std::cos(c.pitch),scale=std::tan(3.14159265f/8);
 return {sy*cp+x*scale*aspect*cy-y*scale*sy*sp,sp+y*scale*cp,cy*cp-x*scale*aspect*sy-y*scale*cy*sp};
}
SceneMesh avatar(const SceneSnapshot& world,const PlayerController& player) {
 if(!player.avatar_visible()) return {};
 SceneSnapshot proxy{world.world_id,world.revision,{}};const auto p=player.state().feet;
 proxy.objects.push_back({world.world_id,"BS capsule proxy",{p.x,p.y+.9f,p.z},{.3f,.9f,.3f},{.85f,.50f,.16f},0,false});return mesh_from_snapshot(proxy);
}
void write_request(const std::filesystem::path& path,const GameplayChangeBatch& batch) {
 if(path.empty()) return;
 const auto bytes=gameplay_codec::encode_batch(batch);
 HANDLE file=CreateFileW(path.c_str(),GENERIC_WRITE,0,nullptr,CREATE_NEW,FILE_ATTRIBUTE_NORMAL,nullptr);
 require(file!=INVALID_HANDLE_VALUE,"Cannot create the new proof request file");DWORD written=0;
 const bool ok=WriteFile(file,bytes.data(),static_cast<DWORD>(bytes.size()),&written,nullptr)&&written==bytes.size()&&FlushFileBuffers(file);
 CloseHandle(file);require(ok,"Cannot flush proof request bytes");
}
GameplayChangeBatch read_request(const std::filesystem::path& path) {
 const auto size=std::filesystem::file_size(path);require(size>0&&size<=4*1024*1024,"Invalid bounded proof request size");
 std::ifstream file(path,std::ios::binary);std::vector<std::uint8_t> bytes(static_cast<std::size_t>(size));
 require(static_cast<bool>(file.read(reinterpret_cast<char*>(bytes.data()),static_cast<std::streamsize>(bytes.size()))),"Cannot read proof request");return gameplay_codec::decode_batch(bytes);
}
bool has_status(const NativeWindow& window,const std::wstring& text) {
 const auto parent=static_cast<HWND>(window.native_handle());HWND child=nullptr;
 while((child=FindWindowExW(parent,child,L"STATIC",nullptr))) {
  const auto length=GetWindowTextLengthW(child);if(length<=0||length>16384) continue;
  std::wstring actual(static_cast<std::size_t>(length)+1,L'\0');
  const int copied=GetWindowTextW(child,actual.data(),static_cast<int>(actual.size()));actual.resize(static_cast<std::size_t>(copied));
  if(actual.find(text)!=std::wstring::npos) return true;
 }
 return false;
}
std::string hud_fact(const DurableFirstBootGuidance& memory,const GameplayStoreRecovery& snapshot) {
 std::string text;
 if(!memory.committed_facts.empty()) text=memory.committed_facts.front();
 else if(const auto marker=memory.original_evidence.find("Imported edit record: ");marker!=std::string::npos)
  text="Imported saved action: "+memory.original_evidence.substr(marker+22);
 else return "No saved gameplay actions are recorded here yet.";
 if(const auto metadata=text.rfind(" [revision ");metadata!=std::string::npos) text.erase(metadata);
 if(text.starts_with("Committed gameplay: ")) text.erase(0,20);
 for(const auto& record:snapshot.components) if(const auto at=text.find(record.entity_id);at!=std::string::npos)
  text.replace(at,record.entity_id.size(),std::get<std::string>(record.fields.at("name")));
 if(text.size()>150) {
  std::size_t end=150;while(end>0&&(static_cast<unsigned char>(text[end])&0xc0)==0x80) --end;
  text.resize(end);text+="...";
 }
 return text;
}
class LiveWorld {
public:
 const Options& config;GameplayScope scope;
 std::unique_ptr<GameplayStore> archive;
 std::unique_ptr<GameplayWorld> owner;
 std::set<std::string> historical_ids;
 SceneSnapshot scene;PlayerController player;
 NativeWindow& window;Dx12Renderer& renderer;
 DurableFirstBootGuidance memory;std::string remembered,notice="World restored. Changes save in the background; F5 retries a failed save.";
 std::string last_operation;
 std::uint64_t memory_revision=0,memory_visible_revision=0;bool memory_loaded=false,exit_requested=false;
 bool live_retry=false,close_drained=false;unsigned reloads=0;
 LiveWorld(const Options& o,GameplayScope s,std::unique_ptr<GameplayStore> a,std::unique_ptr<GameplayWorld> w,
           SceneSnapshot snapshot,PlayerController bs,NativeWindow& native,Dx12Renderer& gpu)
  :config(o),scope(std::move(s)),archive(std::move(a)),owner(std::move(w)),
   historical_ids(durable_first_boot_imported_ids(*archive)),scene(std::move(snapshot)),player(std::move(bs)),window(native),renderer(gpu) { refresh_memory(); }
 void refresh_memory() {
  const auto state=owner->state();
  if(!memory_loaded||state.durable_revision!=memory_revision||state.visible_revision!=memory_visible_revision) {
   memory=durable_first_boot_guidance(*owner,*archive);remembered=hud_fact(memory,*owner->snapshot());
   memory_revision=state.durable_revision;memory_visible_revision=state.visible_revision;memory_loaded=true;
  }
 }
 void poll() {
  while(const auto completion=owner->poll()) {
   notice=(completion->result.status==GameplayStoreStatus::committed||completion->result.status==GameplayStoreStatus::retry)
    ?"World change and its memory committed.":"UNSAVED: "+completion->result.message;
  }
  refresh_memory();
 }
 bool apply(const GameplayChangeBatch& batch,bool capture_request=false) {
  const auto prepared=owner->prepare(batch,[&](const auto& before,const auto& after,const auto& immutable) {
   durable_first_boot_rules(before,after,immutable,historical_ids);
  });
  if(prepared.status==GameplayPrepareStatus::retry) { notice="This exact action is already recorded; no duplicate change.";return true; }
  if(prepared.status!=GameplayPrepareStatus::prepared) { notice="Change blocked: "+prepared.message;return false; }
  auto next=durable_first_boot_scene(*prepared.change->snapshot());
  const auto next_mesh=mesh_from_snapshot(next),previous_mesh=mesh_from_snapshot(scene);
  if(capture_request) write_request(config.request,*prepared.change->batch());
  // Pause publication between staging and admission. No simulation tick or draw
  // can observe candidate dependencies until the owner has accepted publication.
  try { player.set_scene(next); }
  catch(const std::invalid_argument& error) { notice=std::string("Construction blocked: ")+error.what();return false; }
  try { renderer.set_scene(next_mesh); }
  catch(...) { player.set_scene(scene);throw; }
  const auto result=owner->publish(prepared.change);
  if(!result.ok) {
   // Rollback failure is fatal; never draw geometry for a rejected world change.
   player.set_scene(scene);renderer.set_scene(previous_mesh);notice="Change blocked: "+result.message;return false;
  }
  scene=std::move(next);last_operation=batch.operation_id;notice=result.message;return true;
 }
 bool action(const WindowInput& input) {
  const auto before=owner->snapshot();const auto& camera=player.camera();
  const float aspect=static_cast<float>(window.width())/static_cast<float>(window.height());
  const auto hit=pick_scene(scene,camera.position,ray(camera,input.pointer_interact?input.pointer_x:0,input.pointer_interact?input.pointer_y:0,aspect));
  if(input.interact) {
   if(!hit) { notice="Aim at Core Node 01 or a relay.";return false; }
   const auto projected=durable_first_boot_world(*before);const auto* target=first_boot_entity(projected,hit->persistent_id);
   if(!target) { notice="That component is no longer present.";return false; }
   if(target->fields.at("firstboot.kind")!=2&&target->fields.at("firstboot.kind")!=6) { notice="Inspecting "+target->name;return false; }
   const auto repair=durable_first_boot_repair(*before,hit->persistent_id);
   if(!repair) { notice="Already restored. Its recorded history is unchanged.";return true; }
   return apply(*repair,config.proof()&&!config.request.empty()&&config.step!=L"retry");
  }
  if(input.build) {
   const auto placement=durable_first_boot_placement(*before,camera.position,ray(camera,0,0,aspect));
   if(!placement) { notice="Look toward the board surface within building range.";return false; }
   return apply(durable_first_boot_build(*before,*placement));
  }
  if(input.dismantle) {
   if(!hit) { notice="Aim at a built relay to dismantle it.";return false; }
   const auto removed=durable_first_boot_dismantle(*before,hit->persistent_id);
   if(!removed) { notice="The relay is already dismantled.";return true; }return apply(*removed);
  }
  return false;
 }
 void reload() {
  if(!owner->state().saved) { notice="Finish or retry the pending save before reloading.";return; }
  std::unique_ptr<GameplayWorld> replacement;std::unique_ptr<PlayerController> bs;SceneSnapshot next;
  try {
   replacement=std::make_unique<GameplayWorld>(config.database,scope,durable_first_boot_schemas());
   next=durable_first_boot_scene(*replacement->snapshot());
   bs=std::make_unique<PlayerController>(durable_first_boot_player(*replacement->snapshot()));
   renderer.set_scene(mesh_from_snapshot(next));
  } catch(const std::exception& error) { notice=std::string("Reload blocked; current world retained: ")+error.what();return; }
  const auto stopped=owner->close();
  require(stopped.ok,"Unexpected failure closing a saved world during reload: "+stopped.message);
  owner.swap(replacement);scene=std::move(next);player=std::move(*bs);memory_loaded=false;refresh_memory();++reloads;notice="Committed world restored at a clear entrance.";
 }
 bool frame(double elapsed) {
  if(!window.poll()) exit_requested=true;
  poll();const auto input=window.input();
  if(input.save) {
   if(owner->state().failed) { const auto retry=owner->retry_pending();notice=retry.message; }
   else notice=owner->state().saved?"All visible changes are saved.":"Waiting for the current save to complete.";
  }
  if(exit_requested) {
   WindowInput paused;paused.active=false;player.update(paused,0);
   if(owner->state().saved) { require(owner->close().ok,"Could not close the saved world");return false; }
   notice=owner->state().failed?"UNSAVED. Close is waiting; press F5 to retry.":"Closing after pending world changes are saved.";
  } else if(!window.minimized()&&input.active) {
   player.update(input,elapsed);
   if(player.state().feet.y<-20) { player=durable_first_boot_player(*owner->snapshot());notice="BS returned to a clear board entrance."; }
   try { if(input.reload) reload();else if(input.interact||input.build||input.dismantle) action(input); }
   catch(const std::invalid_argument& error) { notice=std::string("Change blocked: ")+error.what(); }
  } else { WindowInput paused;paused.active=false;player.update(paused,0); }
  refresh_memory();const auto state=owner->state();
  const std::string heads=(state.saved?"SAVED":state.failed?"UNSAVED / RETRY":"SAVING")+std::string(" | visible ")+std::to_string(state.visible_revision)+" | durable "+std::to_string(state.durable_revision);
  window.set_status(L"WASD walk | Right-drag look | Space jump | V camera | F2 inspect\nE/click repair | B build | Delete dismantle | F5 retry | F9 reload\nAdam (authored guidance): "+wide(memory.authored_hint)+L"\nRecorded: "+wide(remembered)+L"\n"+wide(heads)+L"\n"+wide(notice));
  if(!window.minimized()) renderer.render(player.camera(),avatar(scene,player));
  return true;
 }
};
void key(NativeWindow& window,WPARAM code) {
 SendMessageW(static_cast<HWND>(window.native_handle()),WM_KEYDOWN,code,0);
 SendMessageW(static_cast<HWND>(window.native_handle()),WM_KEYUP,code,0);
}
void aim(PlayerController& player,Vec3 target) {
 aibs::app_input::aim(player,target);
}
void repair_input(LiveWorld& live) {
 const auto world=durable_first_boot_world(*live.owner->snapshot());const auto& core=world.at("core-01");
 aim(live.player,{static_cast<float>(core.fields.at("x")),static_cast<float>(core.fields.at("y")),static_cast<float>(core.fields.at("z"))});
 key(live.window,'E');require(live.action(live.window.input()),"Native aimed E repair failed: "+live.notice);
}
void drain(LiveWorld& live,bool expect_failure=false) {
 const auto deadline=Clock::now()+std::chrono::seconds(15);
 while(!live.owner->state().saved&&!live.owner->state().failed) {
  live.poll();live.window.poll();require(Clock::now()<deadline,"Native save did not complete within its bounded proof deadline");
  if(!live.window.minimized()) live.renderer.render(live.player.camera());std::this_thread::sleep_for(std::chrono::milliseconds(1));
 }
 if(expect_failure) require(live.owner->state().failed&&!live.owner->state().saved,"Expected actual native save failure was not observed");
 else require(live.owner->state().saved,"Native save failed: "+live.owner->state().error);
}
void report(LiveWorld& live) {
 const auto& o=live.config;if(o.capture.empty()||o.report.empty()) return;
 if(!o.capture.parent_path().empty()) std::filesystem::create_directories(o.capture.parent_path());
 if(!o.report.parent_path().empty()) std::filesystem::create_directories(o.report.parent_path());
 // Stable overview excludes transient BS pose and UI; this is real DX12 readback.
 Camera overview;for(int i=0;i<3;++i) { live.window.poll();live.renderer.render(overview); }
 const auto pixels=live.renderer.capture(o.capture);live.renderer.wait_idle();const auto stats=live.renderer.stats();
 require(pixels>10000&&stats.debug_errors==0,"Native durable-world GPU verification failed");
 const auto state=live.owner->state();const auto snapshot=live.owner->snapshot();const auto nodes=durable_first_boot_world(*snapshot);
 std::vector<GameplayChangeBatch> batches;std::uint64_t cursor=0;std::size_t history_bytes=0;
 for(;;) {
  auto page=live.owner->read_batches(cursor);if(page.empty()) break;
  for(const auto& batch:page) {
   const auto size=gameplay_codec::encode_batch(batch).size();
   require(size<=16*1024*1024-history_bytes&&batches.size()<4096,"Proof history exceeds its explicit item/16MiB bound");
   history_bytes+=size;batches.push_back(batch);
  }
  cursor=page.back().revision;
 }
 std::uint64_t original_events=0;
 if(const auto base=live.archive->baseline();base&&!base->legacy_checkpoint.empty()) {
  CreatorSession source(first_boot_schema(),live.scope.project_id,live.scope.branch_id);
  require(restore_imported_checkpoint(*live.archive,source).ok,"Cannot verify original imported evidence");original_events=source.memory().events().size();
 }
 std::ofstream f(o.report);require(f.good(),"Cannot open native durable report");
 f<<std::setprecision(17)<<"{\"schema_version\":1,\"status\":\"passed\",\"completed_at\":"<<quoted(utc())
  <<",\"scope\":{\"project_id\":"<<quoted(live.scope.project_id)<<",\"world_id\":"<<quoted(live.scope.world_id)<<",\"branch_id\":"<<quoted(live.scope.branch_id)
  <<",\"timeline_id\":"<<quoted(live.scope.timeline_id)<<",\"context\":\"player_world\"},\"visible_revision\":"<<state.visible_revision
  <<",\"durable_revision\":"<<state.durable_revision<<",\"durable_sequence\":"<<state.durable_sequence<<",\"saved\":"<<(state.saved?"true":"false")
  <<",\"pending_batches\":"<<state.pending_batches<<",\"core_capacity\":"<<nodes.at("core-01").fields.at("capacity")
  <<",\"imported_original_events\":"<<original_events<<",\"original_evidence\":"<<quoted(live.memory.original_evidence)
  <<",\"proposed_operation\":"<<quoted(live.last_operation)<<",\"entity_ids\":{";
 bool first=true;
 for(const auto& record:snapshot->components) { if(!first) f<<',';first=false;f<<quoted(std::get<std::string>(record.fields.at("alias")))<<':'<<quoted(record.entity_id); }
 f<<"},\"alive_ids\":[";first=true;
 for(const auto& [unused,e]:nodes) { (void)unused;if(!first) f<<',';first=false;f<<quoted(e.persistent_id); }
 f<<"],\"tombstones\":[";first=true;
 for(const auto& record:snapshot->components) if(!std::get<bool>(record.fields.at("alive"))) { if(!first) f<<',';first=false;f<<quoted(record.entity_id); }
 f<<"],\"events\":[";first=true;
 for(const auto& batch:batches) for(const auto& event:batch.events) {
  if(!first) f<<',';first=false;
  f<<"{\"event_id\":"<<quoted(event.event_id)<<",\"operation_id\":"<<quoted(event.operation_id)<<",\"sequence\":"<<event.sequence
   <<",\"type\":"<<quoted(semantic_event_type(event))<<",\"subject_id\":"<<quoted(event.subject_ids.empty()?"":event.subject_ids.front())<<'}';
 }
 f<<"],\"metrics\":{\"debug_layer\":"<<(stats.debug_layer?"true":"false")<<",\"debug_errors\":"<<stats.debug_errors<<",\"nonbackground_pixels\":"<<pixels
  <<",\"live_retry\":"<<(live.live_retry?"true":"false")<<",\"close_drained\":"<<(live.close_drained?"true":"false")<<",\"reload\":"<<(live.reloads?"true":"false")<<"}}\n";
 require(f.good(),"Could not finish native durable report");
}
void prove(LiveWorld& live,const std::shared_ptr<Gate>& gate) {
 const auto& step=live.config.step;
 if(step==L"repair"||step==L"fail-retry"||step==L"close-drain"||step==L"before-commit"||step==L"after-commit") repair_input(live);
 else if(step==L"build") {
  const auto nodes=durable_first_boot_world(*live.owner->snapshot());float plane=1;
  for(const auto& [unused,e]:nodes) { (void)unused;if(e.fields.at("firstboot.kind")==1) plane=static_cast<float>(e.fields.at("y")+e.fields.at("half_y"))+1; }
  aim(live.player,{30,plane,-20});key(live.window,'B');require(live.action(live.window.input()),"Native B construction failed: "+live.notice);
 }
 else if(step==L"dismantle") {
  const auto nodes=durable_first_boot_world(*live.owner->snapshot());const Entity* relay=nullptr;
  for(const auto& [unused,e]:nodes) { (void)unused;if(e.fields.at("firstboot.kind")==6) { require(!relay,"Proof requires a single relay");relay=&e; } }
  require(relay,"No built relay is available to dismantle");aim(live.player,{static_cast<float>(relay->fields.at("x")),static_cast<float>(relay->fields.at("y")),static_cast<float>(relay->fields.at("z"))});
  key(live.window,VK_DELETE);require(live.action(live.window.input()),"Native Delete dismantle failed: "+live.notice);
 } else if(step==L"retry") require(live.apply(read_request(live.config.request)),"Exact native request retry failed");
 else if(step==L"reload") { key(live.window,VK_F9);require(live.frame(0)&&live.reloads==1,"Native F9 did not reload committed typed state"); }
 if(step==L"before-commit"||step==L"after-commit") {
  gate->await();const auto state=live.owner->state();
  require(state.pending_batches==1&&state.visible_revision>state.durable_revision&&!state.saved,"Pending native state was mislabeled durable before completion");
  require(live.frame(0)&&has_status(live.window,L"SAVING | visible "),"Actual native HUD did not distinguish pending visibility from saved state");
  report(live);gate->release();
  const auto until=Clock::now()+std::chrono::seconds(10);while(Clock::now()<until) std::this_thread::sleep_for(std::chrono::milliseconds(1));
  throw std::runtime_error("Requested native process interruption did not occur");
 }
 if(step==L"fail-retry") {
  drain(live,true);const auto revision=live.owner->state().visible_revision;
  require(live.frame(0)&&has_status(live.window,L"UNSAVED / RETRY"),"Actual native HUD did not show failed saving");
  key(live.window,VK_F5);require(live.frame(0),"Retry unexpectedly closed the native window");drain(live);
  require(live.owner->state().visible_revision==revision,"F5 created a second gameplay action");
  require(live.frame(0)&&has_status(live.window,L"SAVED | visible "),"Actual native HUD did not acknowledge the saved retry");live.live_retry=true;
 } else if(step==L"close-drain") {
  gate->await();live.window.minimize();SendMessageW(static_cast<HWND>(live.window.native_handle()),WM_CLOSE,0,0);
  require(live.frame(0)&&!live.owner->state().closed&&!live.owner->state().saved&&IsWindow(static_cast<HWND>(live.window.native_handle())),"Window closed before saving pending work");
  gate->release();const auto deadline=Clock::now()+std::chrono::seconds(15);
  while(live.frame(0)) { require(Clock::now()<deadline,"Close did not drain the actual save");std::this_thread::sleep_for(std::chrono::milliseconds(1)); }
  require(live.owner->state().saved&&live.owner->state().closed,"Close did not consume a real durable completion");live.close_drained=true;live.window.restore(false);live.window.poll();
 } else drain(live);
 live.refresh_memory();report(live);
 if(!live.owner->state().closed) require(live.owner->close().ok,"Native durable proof did not flush on close");
}

GameplayStoreRecovery chapter_nodes(const GameplayStoreRecovery& source) {
 auto result=source;std::erase_if(result.components,[](const auto& record){return record.type_id!="firstboot.Node";});return result;
}
const ComponentRecord& chapter_record(const GameplayStoreRecovery& source,const std::string& id) {
 const auto found=std::find_if(source.components.begin(),source.components.end(),[&](const auto& record){return record.entity_id==id;});
 require(found!=source.components.end(),"Chapter component is missing");return *found;
}
double chapter_number(const ComponentRecord& record,const char* key) { return std::get<double>(record.fields.at(key)); }
bool chapter_flag(const ComponentRecord& record,const char* key) { return std::get<bool>(record.fields.at(key)); }
std::string chapter_text(const ComponentRecord& record,const char* key) { return std::get<std::string>(record.fields.at(key)); }
Vec3 chapter_point(const ComponentRecord& record,const std::string& prefix={}) {
 return {static_cast<float>(std::get<double>(record.fields.at(prefix+"x"))),static_cast<float>(std::get<double>(record.fields.at(prefix+"y"))),static_cast<float>(std::get<double>(record.fields.at(prefix+"z")))};
}
GameplayScope initialize_chapter(const Options& o) {
 const bool existing=std::filesystem::exists(o.database);GameplayScope scope;
 if(!existing&&o.step==L"translated-walk"&&o.import_source.empty()) {
  CreatorSession translated(first_boot_schema(),"first-boot-world","main");require(seed_first_boot(translated).ok,"Cannot seed translated synthetic board");
  Transaction moved{"proof.translate-board",translated.revision(),{}};
  for(const auto& [alias,entity]:translated.world()) moved.edits.push_back(SetField{alias,"y",entity.fields.at("y")-30,entity.persistent_id});
  require(translated.apply(moved).ok,"Cannot prepare translated synthetic board");Options captured=o;captured.import_source=o.database;captured.import_source+=L".translated.aibs";
  require(CheckpointStore::save(captured.import_source,translated).ok,"Cannot capture translated synthetic authoring fixture");scope=initialize(captured);
 }
 else if(!existing||!o.import_source.empty()) scope=initialize(o);
 else {
  std::vector<GameplayScope> matches;
  for(const auto& candidate:GameplayStore::list_scopes(o.database))
   if(candidate.project_id=="first-boot-world"&&candidate.branch_id=="main"&&candidate.context==GameplayContext::player_world) matches.push_back(candidate);
  require(matches.size()==1,"Choose a database containing exactly one First Boot player timeline");scope=matches.front();
 }
 const auto current=GameplayStore::inspect_registry(o.database,scope);
 const auto current_bytes=gameplay_codec::encode_schemas(current),node_bytes=gameplay_codec::encode_schemas(durable_first_boot_schemas());
 const auto target=first_boot_chapter_schemas();const auto target_bytes=gameplay_codec::encode_schemas(target);
 require(current_bytes==node_bytes||current_bytes==target_bytes,"Chapter requires a recognized Node or chapter registry; no implicit migration was selected");
 if(current_bytes==node_bytes) {
  require(!existing||!o.import_source.empty()||o.upgrade_chapter,"Existing M2 worlds require explicit --upgrade-chapter; their original Node world remains unchanged");
  GameplayStoreRecovery before;
  { GameplayStore old(o.database,scope,durable_first_boot_schemas());before=old.recover();first_boot_chapter_preflight(before); }
  const auto extended=GameplayStore::extend_registry(o.database,scope,durable_first_boot_schemas(),target,"firstboot.chapter.registry.v1",before.revision,before.sequence);
  require(extended.status==GameplayStoreStatus::committed||extended.status==GameplayStoreStatus::retry,extended.message);
 }
 GameplayStore archive(o.database,scope,target);const auto historical=durable_first_boot_imported_ids(archive);
 GameplayWorld install(o.database,scope,target);
 if(const auto proposed=first_boot_chapter_install(*install.snapshot())) {
  const auto prepared=install.prepare(*proposed,[&](const auto& before,const auto& after,const auto& batch) {
   first_boot_chapter_rules(before,after,batch,FirstBootChapterActor{},historical);
  });
  require(prepared.status==GameplayPrepareStatus::prepared,prepared.message);
  const auto published=install.publish(prepared.change);require(published.ok,published.message);
 }
 const auto closed=install.close();require(closed.ok,closed.message);first_boot_chapter_validate(*install.snapshot());return scope;
}
std::shared_ptr<const FirstBootContent> load_content(const Options& o) {
 const auto size=std::filesystem::file_size(o.content_definition);require(size>0&&size<=1024*1024,"Invalid bounded content definition size");
 std::ifstream file(o.content_definition,std::ios::binary);std::vector<unsigned char> bytes(static_cast<std::size_t>(size));
 require(static_cast<bool>(file.read(reinterpret_cast<char*>(bytes.data()),static_cast<std::streamsize>(bytes.size()))),"Cannot read immutable content definition");
 return std::make_shared<const FirstBootContent>(first_boot_content_decode(bytes));
}
std::filesystem::path saved_world_claim_path(const Options& o){auto path=o.database;path+=L".initialized";return path;}
std::string saved_world_claim(const GameplayScope& scope,const FirstBootContent& content){
 return "{\"schema_version\":1,\"project_id\":"+quoted(scope.project_id)+",\"branch_id\":"+quoted(scope.branch_id)+
  ",\"world_id\":"+quoted(scope.world_id)+",\"timeline_id\":"+quoted(scope.timeline_id)+",\"content_fingerprint\":"+quoted(content.fingerprint())+"}\n";
}
std::string saved_play_lifecycle(const Options& o,const GameplayScope& scope,const FirstBootContent& content,
 const GameplayWorldState& status,bool ready,bool critical){
 require(o.persistent_play&&scope.context==GameplayContext::player_world&&scope.timeline_id==o.timeline_id,"Saved Play lifecycle scope mismatch");
 std::ostringstream out;
 out<<"{\"event\":"<<quoted(ready?"aibs.saved_play.ready":"aibs.saved_play.stopped")<<",\"schema_version\":1,\"play_session\":"<<quoted(o.play_session)
  <<",\"project_id\":"<<quoted(scope.project_id)<<",\"branch_id\":"<<quoted(scope.branch_id)<<",\"world_id\":"<<quoted(scope.world_id)<<",\"timeline_id\":"<<quoted(scope.timeline_id)
  <<",\"context\":\"player_world\",\"content_fingerprint\":"<<quoted(content.fingerprint())<<",\"saved\":"<<(status.saved&&!critical?"true":"false")
  <<",\"durable_revision\":"<<status.durable_revision<<",\"durable_sequence\":"<<status.durable_sequence<<"}\n";return out.str();
}
void validate_saved_world_claim(const Options& o,const GameplayScope& scope,const FirstBootContent& content,bool existing_database){
 const auto path=saved_world_claim_path(o);const auto expected=saved_world_claim(scope,content);
 require(expected.size()<=4096,"Saved player initialization claim exceeds its bound");
 const bool present=std::filesystem::exists(path)||std::filesystem::is_symlink(path);
 require(existing_database==present,existing_database?"Retained player database has no initialization claim; implicit adoption is prohibited":"Retained player initialization claim exists but its database is missing; no automatic reseed");
 if(!present) {
  // Reserve first initialization durably before RW SQLite open. On any failure
  // this claim stays, making missing/partial initialization explicit on retry.
  const auto file=CreateFileW(path.c_str(),GENERIC_WRITE,0,nullptr,CREATE_NEW,
   FILE_ATTRIBUTE_NORMAL|FILE_FLAG_WRITE_THROUGH|FILE_FLAG_OPEN_REPARSE_POINT,nullptr);
  require(file!=INVALID_HANDLE_VALUE,"Cannot exclusively reserve new saved player initialization");
  DWORD written=0;const bool ok=WriteFile(file,expected.data(),static_cast<DWORD>(expected.size()),&written,nullptr)&&written==expected.size()&&FlushFileBuffers(file);
  CloseHandle(file);require(ok,"Cannot flush saved player initialization claim; incomplete slot retained");return;
 }
 const auto file=CreateFileW(path.c_str(),GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,FILE_FLAG_OPEN_REPARSE_POINT,nullptr);
 require(file!=INVALID_HANDLE_VALUE,"Cannot read saved player initialization claim");
 BY_HANDLE_FILE_INFORMATION info{};LARGE_INTEGER size{};std::array<char,4096> bytes{};DWORD read=0;
 const bool ok=GetFileInformationByHandle(file,&info)&&!(info.dwFileAttributes&(FILE_ATTRIBUTE_REPARSE_POINT|FILE_ATTRIBUTE_DIRECTORY))&&
  GetFileSizeEx(file,&size)&&size.QuadPart==static_cast<LONGLONG>(expected.size())&&ReadFile(file,bytes.data(),static_cast<DWORD>(expected.size()),&read,nullptr)&&
  read==expected.size()&&std::string_view(bytes.data(),read)==expected;
 CloseHandle(file);require(ok,"Saved player initialization claim is corrupt or belongs to another immutable content/timeline");
}
#include "workshop_save_compatibility.inl"
GameplayScope initialize_content(const Options& o,const FirstBootContent& content,std::vector<ComponentSchema>* selected=nullptr) {
 const GameplayScope scope{o.project,content.definition().world_id,o.branch,o.persistent_play?o.timeline_id:o.play_session,
  o.persistent_play?GameplayContext::player_world:GameplayContext::temporary_play};
 (void)gameplay_codec::encode_scope(scope);const bool existing=std::filesystem::exists(o.database);
 auto schemas=first_boot_content_relay_assembly_schemas(content);
 if(o.persistent_play) {
  // Content, path, registry and full binding admission precede any RW open.
  if(!existing){const auto baseline=first_boot_content_baseline(content);first_boot_content_validate({scope,baseline.revision,baseline.sequence,baseline.components},content);}
  validate_saved_world_claim(o,scope,content,existing);
  if(existing) {
   // The single read-only probe checks scope, registry and full stream under
   // source write-denial handles without creating WAL/SHM files.
   schemas=chapter_save_registry(o,scope,content);if(selected)*selected=schemas;return scope;
  }
 }
 if(existing) {
  const auto scopes=GameplayStore::list_scopes(o.database);require(scopes.size()==1&&scopes.front()==scope,"Managed Play scratch scope mismatch; no player/authoring timeline was selected or modified");
  schemas=chapter_save_registry(o,scope,content);
 }
 GameplayStore store(o.database,scope,schemas);
 if(!store.baseline()) {
  require(!existing,"Managed Play scratch is missing its immutable baseline; no reseeding");
  const auto seeded=store.seed(first_boot_content_baseline(content));require(seeded.status==GameplayStoreStatus::committed,seeded.message);
 }
 first_boot_content_validate(store.recover(),content);if(selected)*selected=schemas;return scope;
}
struct ChapterControl { std::atomic<bool> hold_next=false,fail_next=false;Gate gate; };
struct ChapterIntent { GameplayChangeBatch batch;FirstBootChapterActor actor;bool recovery=false; };
#include "memory_runtime.inl"
#include "opening_inspection_panel.inl"
#include "opening_runtime.inl"
#include "chapter_aim_prompt.inl"
struct OpeningTourReadProof {
 OpeningTourRole role=OpeningTourRole::controller;
 std::string id,title,text,source;std::filesystem::path glyph;
 std::uint64_t revision_before=0,revision_after=0,sequence_before=0,sequence_after=0;
};
#include "recording_runtime.inl"
class ChapterLive {
public:
 const Options& config;GameplayScope scope;std::unique_ptr<GameplayStore> archive;std::unique_ptr<GameplayWorld> owner;
 std::vector<ComponentSchema> registered_schemas;
 GameplayWorkerLimits save_limits;
 GameplayStoreObserver save_observer;
 bool previous_workshop_registry=false;
 bool reopen_after_registry_change=false;
 const std::shared_ptr<const FirstBootContent> content;
 const std::shared_ptr<const PlacedAssetVisuals> placed_assets;
 SceneSnapshot scene;PlayerController player;NativeWindow& window;Dx12Renderer& renderer;FirstBootChapterClock clock;
 chapter_aim::SolidCache aim_solids;
 std::shared_ptr<const GameplayStoreRecovery> build_plane_snapshot;
 double build_plane_top=0;
 std::shared_ptr<const GameplayStoreRecovery> assembly_snapshot;
 FirstBootRelayAssemblyState assembly_state;
 const bool workshop_hud=content&&first_boot_content_workshop_binding(content->definition()).has_value();
 std::wstring hud_status,compact_hud_status;std::uint64_t hud_text_publications=0;
 std::unique_ptr<CompanionRuntime> companion;
 std::unique_ptr<ChapterMemoryRuntime> original_memory;
 std::unique_ptr<ChapterOpeningRuntime> opening;
 bool proof_opening_controls=false;unsigned proof_opening_checks=0;
 std::string guidance_context;double guidance_remaining=0,guidance_cooldown=0;unsigned guidance_gestures=0;
 bool proof_memory_controls=false;std::uint64_t proof_memory_paused_frame=0,proof_memory_resumed_frame=0;unsigned proof_memory_checks=0;
 std::optional<CharacterMesh> guide_mesh;
 std::unique_ptr<GuidePresentation> guide_presentation;
 std::unique_ptr<FirstBootInitialViewPolicy> initial_view;
 std::optional<CharacterInstance> guide_instance;
 std::set<std::string> historical;std::optional<ChapterIntent> critical;std::optional<Vec3> entry_previous;
 std::string observed_region,notice="Jenison is not home. Follow what still responds.",remembered="No acknowledged chapter outcomes yet.",last_target;
 bool exit_requested=false,memory_loaded=false,recovered_this_frame=false;std::uint64_t remembered_head=0;unsigned reloads=0;
 bool proof_repair=false,proof_bypass=false,proof_door=false,proof_help=false,proof_decline=false,proof_return=false,proof_feed_loss=false,proof_fall=false,proof_rebuild=false,proof_hazard=false,proof_pause=false,proof_backpressure=false;
 bool proof_remote=false,proof_translated=false,proof_reload_failure=false,proof_consumed=false,proof_stale=false,proof_empty_socket=false;
 bool proof_live_retry=false,proof_close_drained=false,proof_companion_controls=false,proof_companion_route=false;
 bool proof_opening_tour=false;
 std::vector<OpeningTourReadProof> tour_reads;
 std::optional<Clock::time_point> walkthrough_previous;
 std::unique_ptr<ChapterRecorder> recording;
 tour_diagnostic::Controls diagnostic_controls;
 WindowInput controlled_performance_input=[] {WindowInput input;input.active=false;return input;}();
 performance_phases::FrameStages controlled_frame_stages;
 bool saved_close_complete=false;
 tour_diagnostic::Trace input_trace;
 std::uint64_t diagnostic_frame_index=0;
 ChapterLive(const Options& o,GameplayScope s,std::unique_ptr<GameplayStore> original,std::unique_ptr<GameplayWorld> world,
  SceneSnapshot view,PlayerController bs,NativeWindow& native,Dx12Renderer& gpu,std::shared_ptr<const FirstBootContent> definition={},std::shared_ptr<const PlacedAssetVisuals> visuals={})
  :config(o),scope(std::move(s)),archive(std::move(original)),owner(std::move(world)),content(std::move(definition)),placed_assets(std::move(visuals)),scene(std::move(view)),player(std::move(bs)),window(native),renderer(gpu),input_trace(o.input_trace,o.ordinary_input_trace) {
  historical=durable_first_boot_imported_ids(*archive);observed_region=region(*owner->snapshot(),player.state().feet);(void)clock.sample(*owner->snapshot());refresh_memory();
  if(content)initial_view=std::make_unique<FirstBootInitialViewPolicy>(content->definition(),observed_region=="jenison");
  if(config.walkthrough||config.step==L"opening-tour")tour_reads.reserve(opening_tour_stop_count);
  if(content&&!content->definition().companions.empty()&&!(placed_assets&&placed_assets->companion_model()))guide_mesh=make_guide_placeholder();
  if(content){
   auto candidate=std::make_unique<ChapterOpeningRuntime>(content->definition(),static_cast<HWND>(window.native_handle()),!config.offscreen_tour_proof);
   if(candidate->count())opening=std::move(candidate);
  }
  if(content&&!content->definition().memories.empty()){
   const auto companion_cpu=guide_mesh?character_mesh_cost(*guide_mesh).decoded_bytes:0;
   original_memory=std::make_unique<ChapterMemoryRuntime>(content,placed_assets,window,renderer,o.step==L"memory-controls",companion_cpu);
   publish_render_mesh(render_mesh(scene),*owner->snapshot());
  }
  if(content&&!content->definition().companions.empty()){
   companion=std::make_unique<CompanionRuntime>(*owner->snapshot(),*content);
   if(const auto* model=placed_assets?placed_assets->companion_model():nullptr)guide_presentation=std::make_unique<GuidePresentation>(model->mesh);
   else{
    guide_presentation=std::make_unique<GuidePresentation>(*guide_mesh);
    if(original_memory){const auto composed=render_mesh(scene);const auto lights=first_boot_content_lighting(*owner->snapshot(),*content);renderer.set_scene_character_bounded(composed,render_textures(),lights,&*guide_mesh,original_memory->remaining_gpu_bytes(composed));}
    else if(opening){const auto composed=render_mesh(scene);const auto lights=first_boot_content_lighting(*owner->snapshot(),*content);renderer.set_scene_character_bounded(composed,render_textures(),lights,&*guide_mesh,opening_gpu_remainder(composed));}
    else renderer.set_character(*guide_mesh);
   }
   const auto guide=companion->state();guide_instance=guide_presentation->sample(guide.guide,0,false,guide.recall_required);
   request_guidance_gesture();
  }
 }
 bool reading()const noexcept{return opening&&opening->visible();}
 void proof_key(unsigned code){if(config.offscreen_tour_proof)diagnostic_controls.press(code);else key(window,code);}
 void proof_forward(bool held){if(config.offscreen_tour_proof)diagnostic_controls.forward(held);else SendMessageW(static_cast<HWND>(window.native_handle()),held?WM_KEYDOWN:WM_KEYUP,'W',0);}
 WindowInput proof_input(){const auto observed=window.input();return config.offscreen_tour_proof?diagnostic_controls.take():observed;}
 bool tour_frame(double synthetic,bool draw=true){
  if(!config.walkthrough)return frame(synthetic,draw);
  const auto now=Clock::now();const auto elapsed=walkthrough_previous?std::chrono::duration<double>(now-*walkthrough_previous).count():0;walkthrough_previous=now;return frame(elapsed,true);
 }
 std::uint64_t opening_gpu_remainder(const SceneMesh& mesh)const{
  require(placed_assets!=nullptr,"Opening needs the admitted asset closure");
  const auto fallback=guide_mesh?character_mesh_cost(*guide_mesh).decoded_bytes:0;
  require(fallback<=memory_playback_maximum_resident_bytes-2u*1024u*1024u,"Opening fallback guide exceeds128MiB profile");
  require(placed_assets->resident_bytes()<=memory_playback_maximum_resident_bytes-2u*1024u*1024u-fallback,"Opening CPU closure exceeds128MiB profile");
  return static_cast<std::uint64_t>(memory_scene_gpu_remainder(placed_assets->resident_bytes()+2u*1024u*1024u+fallback,mesh));
 }
 void request_guidance_gesture(){
  if(!guide_presentation||guidance_cooldown>0)return;
  const auto* model=placed_assets?placed_assets->companion_model():nullptr;
  const auto& mesh=model?model->mesh:*guide_mesh;guidance_remaining=mesh.clips.at(3).duration_seconds;guidance_cooldown=8;++guidance_gestures;
 }
 const std::vector<ComponentSchema>& schemas()const{return registered_schemas;}
 SceneSnapshot view(const GameplayStoreRecovery& s)const{return content?first_boot_content_scene(s,*content):first_boot_chapter_scene(s);}
 SceneMesh render_mesh(const SceneSnapshot& s)const{
  auto output=placed_assets?placed_assets->mesh(s):mesh_from_snapshot(s);
  if(original_memory){const auto& markers=original_memory->markers();require(output.vertices.size()<=1000000&&markers.vertices.size()<=1000000-output.vertices.size(),"Memory station markers exceed scene budget");output.vertices.insert(output.vertices.end(),markers.vertices.begin(),markers.vertices.end());}
  return output;
 }
 const TexturedScene& render_textures()const{static const TexturedScene empty;return placed_assets?placed_assets->textured():empty;}
 void publish_render_mesh(const SceneMesh& mesh,const GameplayStoreRecovery& state){const auto lights=content?first_boot_content_lighting(state,*content):SceneLighting{};if(original_memory)renderer.set_scene_bounded(mesh,render_textures(),lights,original_memory->remaining_gpu_bytes(mesh));else if(opening)renderer.set_scene_bounded(mesh,render_textures(),lights,opening_gpu_remainder(mesh));else renderer.set_scene(mesh,render_textures(),lights);}
 void render_frame(const Camera& camera,const SceneMesh& transient){
  if(guide_instance){
   const auto& world=guide_instance->world;
   const float visibility=guide_camera_visibility(camera.position,{world[12],world[13],world[14]});
   if(visibility>0){auto visual=*guide_instance;visual.opacity*=visibility;renderer.render(camera,transient,visual);return;}
  }
  renderer.render(camera,transient);
 }
 Vec3 safe_return(const GameplayStoreRecovery& s)const{return content?first_boot_content_safe_return(s,*content):first_boot_chapter_safe_return(s);}
 std::string region(const GameplayStoreRecovery& s,Vec3 p)const{return content?first_boot_content_region(s,p,*content):first_boot_chapter_region(s,p);}
 std::string hint(const GameplayStoreRecovery& s,const FirstBootChapterActor& a,std::string target={})const{return content?first_boot_content_hint(s,a,*content,std::move(target)):first_boot_chapter_hint(s,a,std::move(target));}
 FirstBootChapterIds ids()const{
  if(!content)return first_boot_chapter_ids(*owner->snapshot());FirstBootChapterIds result;
  for(const auto& r:content->definition().initial_records){if(r.type_id=="firstboot.Door"){const auto role=chapter_text(r,"role");(role=="main"?result.main_door:role=="service"?result.service_door:result.pencil_door)=r.entity_id;}else if(r.type_id=="firstboot.PowerFault")result.fault=r.entity_id;else if(r.type_id=="firstboot.ChapterProgress")result.progress=r.entity_id;else if(r.type_id=="firstboot.NPCQuest")result.npc_quest=r.entity_id;}return result;
 }
 std::optional<GameplayChangeBatch> propose(const GameplayStoreRecovery& s,const FirstBootChapterCommand& c,const FirstBootChapterActor& a)const{return content?first_boot_content_action(s,c,a,*content):first_boot_chapter_action(s,c,a);}
 std::optional<Vec3> placement(const std::shared_ptr<const GameplayStoreRecovery>& snapshot,Vec3 origin,Vec3 direction){
  if(!content)return durable_first_boot_placement(chapter_nodes(*snapshot),origin,direction);
  const auto length=std::hypot(direction.x,direction.y,direction.z);if(!std::isfinite(length)||length<=0||direction.y>=0)return {};
  // The prompt and B action use the same centre-ray projection. Validate the
  // board once per immutable snapshot, including a newly reopened save.
  if(build_plane_snapshot!=snapshot){
   const auto hardware=durable_first_boot_world(chapter_nodes(*snapshot),scope.context);
   const auto board=std::find_if(hardware.begin(),hardware.end(),[](const auto& row){return row.second.fields.at("firstboot.kind")==1;});
   if(board==hardware.end())throw std::invalid_argument("Content placement requires its authored motherboard");
   const auto& fields=board->second.fields;
   build_plane_top=fields.at("y")+fields.at("half_y");build_plane_snapshot=snapshot;
  }
  const double top=build_plane_top,distance=(top+1-origin.y)/(direction.y/length);
  const auto x=origin.x+direction.x/length*distance,z=origin.z+direction.z/length*distance;
  if(!std::isfinite(distance)||!std::isfinite(x)||!std::isfinite(z)||distance<=0||distance>=200||top+1.2<-50||top+1.2>100||x<-200||x>200||z<-200||z>200)return {};
  return Vec3{static_cast<float>(x),static_cast<float>(top+1.2),static_cast<float>(z)};
 }
 void lifecycle(const char* event){
  if(!content)return;const auto status=owner->state();
  input_trace.ordinary_lifecycle(std::string_view(event)=="aibs.play.ready",status.saved&&!critical,status.durable_revision,status.durable_sequence);
  if(config.persistent_play){
   std::cout<<saved_play_lifecycle(config,scope,*content,status,std::string_view(event)=="aibs.play.ready",critical.has_value())<<std::flush;return;
  }
  std::cout<<"{\"event\":"<<quoted(event)<<",\"play_session\":"<<quoted(config.play_session)<<",\"world_id\":"<<quoted(scope.world_id)<<",\"content_fingerprint\":"<<quoted(content->fingerprint())<<",\"saved\":"<<(status.saved&&!critical?"true":"false")<<",\"durable_revision\":"<<status.durable_revision<<"}\n"<<std::flush;
 }
 FirstBootChapterActor actor(Vec3 previous) {
  const auto state=player.state();FirstBootChapterActor result;result.previous_feet=previous;result.feet=state.feet;result.grounded=state.grounded;
  result.inspection_mode=player.inspection_mode()||reading();result.active_tick=clock.tick();result.hazard=clock.sample(*owner->snapshot());return result;
 }
 void refresh_memory() {
  const auto status=owner->state();if(memory_loaded&&remembered_head==status.durable_revision) return;
  remembered="No acknowledged chapter outcomes yet.";
  const auto from=status.durable_revision>64?status.durable_revision-64:0;
  for(const auto& batch:owner->read_batches(from,64)) {
   if(batch.revision>status.durable_revision) continue;
   for(const auto& event:batch.events) {
    if(const auto* mechanism=std::get_if<MechanismOutcome>(&event.payload)) {
     const auto& attribute=mechanism->attribute_id;
     if(attribute=="diagnosed") remembered="Inspected the downstream power fault.";
     else if(attribute=="isolated") remembered=mechanism->after?"Isolated the damaged main feed.":"Reconnected the main feed.";
     else if(attribute=="bypass_connected") remembered=mechanism->after?"Connected a real relay to the bypass feed.":"Disconnected the bypass feed.";
     else if(attribute=="open") remembered=mechanism->after?"Opened a workshop door.":"Closed a workshop door.";
     else if(attribute=="unlocked") remembered="Released a powered door latch.";
     else if(attribute=="shelter_secured") remembered="Secured the workshop shelter.";
     else if(attribute=="pencil_visited") remembered="Reached the Pencil Room.";
     else if(attribute=="lamp_connected") remembered="Connected the Caretaker's table lamp.";
     else if(attribute=="hint_seen") remembered="Spoke with the fictional Caretaker.";
     else remembered="A mechanism change was saved.";
    }
    else if(const auto* guide=std::get_if<CompanionOutcome>(&event.payload)) remembered=guide->action==CompanionAction::follow?"Asked Adam to follow.":guide->action==CompanionAction::wait?"Asked Adam to wait at a supported point.":"Recalled Adam to a clear nearby point.";
    else if(const auto* quest=std::get_if<QuestOutcome>(&event.payload)) {
     if(quest->before==QuestState::unavailable) remembered=quest->after_step=="jenison"?"Restoration began in Jenison.":"The optional table-lamp task became available.";
     else if(quest->after_step=="hub") remembered="Reached the sheltered workshop.";
     else if(quest->after_step=="pencil") remembered="Reached the Pencil Room.";
     else if(quest->after_step=="jenison") remembered="Returned to Jenison outside the shelter.";
     else if(quest->after_step=="lamp.accepted") remembered="Chose to help with the table lamp.";
     else if(quest->after_step=="lamp.deferred") remembered="Left the optional lamp task for later.";
     else if(quest->after_step=="lamp.connected") remembered="Connected the Caretaker's table lamp.";
     else remembered="A quest choice was saved.";
    }
    else if(std::get_if<RepairOutcome>(&event.payload)) remembered="Repaired a damaged power component.";
    else if(const auto* construction=std::get_if<ConstructionOutcome>(&event.payload)) remembered=construction->built?"A real relay was built.":"A real relay was dismantled.";
    else if(std::holds_alternative<HazardOutcome>(event.payload)) remembered="Physical arc contact and a safe return were recorded.";
    else remembered="A traversed route was recorded.";
   }
  }
  remembered_head=status.durable_revision;memory_loaded=true;
 }
 void poll() {
  while(const auto completed=owner->poll()) notice=(completed->result.status==GameplayStoreStatus::committed||completed->result.status==GameplayStoreStatus::retry)?"Change and its outcome saved.":"UNSAVED: "+completed->result.message;
  refresh_memory();
 }
 bool apply(const GameplayChangeBatch& request,const FirstBootChapterActor& evidence,bool recovery=false) {
  if(previous_workshop_registry&&std::any_of(request.deltas.begin(),request.deltas.end(),[](const auto& d){return d.component.type_id==opening_workshop_assembly_component_type;})){
   if(!owner->state().saved||critical){notice="Wait for the current save before collecting or reclaiming the relay assembly.";return false;}
   const auto before=owner->snapshot();const auto next_registry=first_boot_content_relay_assembly_schemas(*content);
   try {preserve_workshop_save(config.database,*before,registered_schemas);}
   catch(const std::exception& error){notice=std::string("Save backup failed; relay assembly held: ")+error.what();return false;}
   const auto upgraded=GameplayStore::extend_registry(config.database,scope,registered_schemas,next_registry,
    "firstboot.workshop.relay-assembly.v1",before->revision,before->sequence);
   if(upgraded.status!=GameplayStoreStatus::committed&&upgraded.status!=GameplayStoreStatus::retry){notice="Relay assembly held: "+upgraded.message;return false;}
   // The old owner must never accept writes after a committed registry upgrade.
   registered_schemas=next_registry;previous_workshop_registry=false;
   try {
    require(owner->close().ok,"Cannot close the previous Workshop save owner");
    auto next_archive=std::make_unique<GameplayStore>(config.database,scope,next_registry);
    auto next_owner=std::make_unique<GameplayWorld>(config.database,scope,next_registry,save_limits,save_observer);
    const auto restored=next_owner->snapshot();
    require(restored->revision==before->revision&&restored->sequence==before->sequence&&restored->components==before->components,
            "Workshop save drifted at the assembly upgrade");
    archive=std::move(next_archive);owner=std::move(next_owner);
   }catch(const std::exception& error){
    reopen_after_registry_change=true;exit_requested=true;
    notice=std::string("Reopen this saved chapter to continue the assembly upgrade: ")+error.what();
    std::cerr<<notice<<'\n';return false;
   }
  }
  const auto prepared=owner->prepare(request,[&](const auto& before,const auto& after,const auto& immutable) {
   const auto current=actor(evidence.previous_feet);
   require(current.feet==evidence.feet&&current.inspection_mode==evidence.inspection_mode,"Body evidence changed before chapter publication");
   if(recovery) require(current.hazard.activation_id==evidence.hazard.activation_id&&current.hazard.cycle==evidence.hazard.cycle&&current.hazard.phase==FirstBootArcPhase::arc,"Old arc contact cannot be published in another activation or cycle");
   if(content)first_boot_content_rules(before,after,immutable,current,*content,historical);else first_boot_chapter_rules(before,after,immutable,current,historical);
  });
  if(prepared.status==GameplayPrepareStatus::retry) { notice="This exact outcome is already recorded.";return true; }
  if(prepared.status!=GameplayPrepareStatus::prepared) { notice="Blocked: "+prepared.message;return false; }
  auto next=view(*prepared.change->snapshot());
  const auto destination=recovery?std::optional<Vec3>(safe_return(*prepared.change->snapshot())):std::nullopt;
  try { player.set_scene(next); } catch(const std::invalid_argument& error) { notice=std::string("Occupied or unsafe change blocked: ")+error.what();return false; }
  try { const auto next_mesh=render_mesh(next);publish_render_mesh(next_mesh,*prepared.change->snapshot()); } catch(...) { player.set_scene(scene);throw; }
  const auto accepted=owner->publish(prepared.change);
  if(!accepted.ok) { player.set_scene(scene);publish_render_mesh(render_mesh(scene),*owner->snapshot());notice="Waiting to publish: "+accepted.message;return false; }
  scene=std::move(next);if(companion)companion->synchronize(*owner->snapshot());notice=accepted.message;
  if(destination) { player.reset(*destination);clock.acknowledge_recovery(evidence.hazard);entry_previous.reset();observed_region=region(*owner->snapshot(),player.state().feet);recovered_this_frame=true; }
  return true;
 }
 bool command(FirstBootChapterCommand request,const FirstBootChapterActor& evidence) {
  const auto proposed=propose(*owner->snapshot(),request,evidence);
  if(!proposed) { notice="That state already holds; no new outcome was invented.";return true; }return apply(*proposed,evidence);
 }
 CompanionActor companion_actor()const{return {{player.state().feet,player.state().grounded,scene.revision},player.inspection_mode()||reading(),exit_requested||window.minimized()||static_cast<bool>(critical),clock.tick()};}
 bool companion_action(CompanionAction action){
  if(reading()){notice="Continue reading before changing Adam's intent.";return false;}
  if(!companion){notice="This chapter has no authored companion.";return false;}
  const auto evidence=companion_actor();const auto feet=evidence.target.feet;
  const std::array<Vec3,12> candidates{{{feet.x+2,feet.y,feet.z},{feet.x-2,feet.y,feet.z},{feet.x,feet.y,feet.z+2},{feet.x,feet.y,feet.z-2},{feet.x+1.5f,feet.y,feet.z+1.5f},{feet.x-1.5f,feet.y,feet.z+1.5f},{feet.x+1.5f,feet.y,feet.z-1.5f},{feet.x-1.5f,feet.y,feet.z-1.5f},{feet.x+3,feet.y,feet.z},{feet.x-3,feet.y,feet.z},{feet.x,feet.y,feet.z+3},{feet.x,feet.y,feet.z-3}}};
  auto choice=companion->prepare_choice(*owner->snapshot(),action,evidence,candidates);
  if(!choice){notice="Adam already has that intent; no new outcome was invented.";return true;}
  const auto prepared=owner->prepare(choice->batch(),[&](const auto& before,const auto& after,const auto& batch){companion->validate_choice(*choice,before,after,batch,companion_actor());});
  if(prepared.status!=GameplayPrepareStatus::prepared){notice="Companion choice blocked: "+prepared.message;return false;}
  require(companion->ready(*choice),"Companion candidate became stale before admission");const auto accepted=owner->publish(prepared.change);
  if(!accepted.ok){notice="Waiting to save Adam's choice: "+accepted.message;return false;}
  require(companion->publish(std::move(choice)),"Admitted companion choice could not activate");scene.revision=owner->snapshot()->revision;notice="Adam's choice is visible; waiting for durable acknowledgement.";return true;
 }
 void retry_critical() {
  if(!critical) return;
  if(critical->recovery) {
   const auto current=clock.sample(*owner->snapshot());
   if(current.activation_id!=critical->actor.hazard.activation_id||current.cycle!=critical->actor.hazard.cycle||current.phase==FirstBootArcPhase::dormant) {
    critical.reset();notice="The fault changed; old contact evidence was cancelled.";return;
   }
  }
  if(owner->state().failed) { notice="Critical outcome retained. F5 retries the failed save first.";return; }
  if(apply(critical->batch,critical->actor,critical->recovery)) { critical.reset();entry_previous.reset(); }
 }
 void observe_body(Vec3 previous) {
  const auto snapshot=owner->snapshot();auto evidence=actor(previous);const auto ids=this->ids();
  if(first_boot_chapter_hazard_contact(*snapshot,evidence)&&evidence.hazard.recovery_available) {
   FirstBootChapterCommand action;action.action=FirstBootChapterAction::recover_arc;
   action.operation_id="firstboot.arc."+evidence.hazard.activation_id+"."+std::to_string(evidence.hazard.cycle);
   if(const auto proposed=propose(*snapshot,action,evidence)) critical=ChapterIntent{*proposed,evidence,true};
  } else {
   const auto actual=region(*snapshot,evidence.feet);
   if(actual!=observed_region) { entry_previous=previous;observed_region=actual; }
   const auto recorded=chapter_text(chapter_record(*snapshot,ids.progress),"step");
   if(actual==recorded) entry_previous.reset();
   else if(entry_previous&&evidence.grounded) {
    evidence.previous_feet=*entry_previous;FirstBootChapterCommand action;
    action.action=actual=="pencil"?FirstBootChapterAction::enter_pencil:actual=="hub"?FirstBootChapterAction::arrive_hub:FirstBootChapterAction::depart_hub;
    if(const auto proposed=propose(*snapshot,action,evidence)) critical=ChapterIntent{*proposed,evidence,false};
   }
  }
  retry_critical();
 }
 const FirstBootRelayAssemblyState* assembly(const std::shared_ptr<const GameplayStoreRecovery>& snapshot){
  if(!workshop_hud)return nullptr;
  if(assembly_snapshot!=snapshot){assembly_state=first_boot_content_relay_assembly(*snapshot,*content);assembly_snapshot=snapshot;}
  return &assembly_state;
 }
 chapter_aim::Prompt focused_prompt() {
  const auto& camera=player.camera();const auto direction=ray(camera,0,0,static_cast<float>(window.width())/static_cast<float>(window.height()));
  const auto picked=aim_solids.pick(scene,camera.position,direction);
  // Original-memory markers precede authored readings and core mechanisms,
  // just as explicit E selection does. This never loads or binds any audio.
  if(original_memory){
   const auto hit=pick_scene(original_memory->station_scene(),camera.position,direction,10);
   if(hit&&(!picked.solid||hit->distance<picked.solid->distance))return {"Original memory: try select nearby station",false};
  }
  FirstBootChapterActor evidence;const auto body=player.state();evidence.feet=evidence.previous_feet=body.feet;evidence.grounded=body.grounded;evidence.inspection_mode=player.inspection_mode();
  const auto* inspection=opening&&picked.solid?opening->find(picked.solid->persistent_id):nullptr;
  const auto snapshot=owner->snapshot();
  return chapter_aim::describe(picked,aim_solids.sync(scene),*snapshot,ids(),content.get(),evidence,inspection,assembly(snapshot));
 }
 bool action(const WindowInput& input) {
  if(reading()||player.inspection_mode()) { notice="Reading or inspection pauses chapter actions; Continue or F2 returns to BS.";return false; }
  const auto snapshot=owner->snapshot();const auto ids=this->ids();const auto evidence=actor(player.state().feet);
  if(input.undo||input.redo) { last_target=ids.npc_quest;return command({input.undo?FirstBootChapterAction::decline_caretaker:FirstBootChapterAction::help_caretaker},evidence); }
  if(original_memory&&input.interact&&!input.build&&!input.dismantle){bool consumed=false;const bool selected=original_memory->interact(scene,player.camera(),player.state().feet,input,consumed);if(consumed)return selected;}
  const auto& camera=player.camera();const float aspect=static_cast<float>(window.width())/static_cast<float>(window.height());
  const auto direction=ray(camera,input.pointer_interact?input.pointer_x:0,input.pointer_interact?input.pointer_y:0,aspect);
  if(opening&&input.interact&&!input.build&&!input.dismantle){bool consumed=false;const bool selected=opening->interact(scene,camera,direction,player.state().feet,consumed);if(consumed){notice=opening->notice();if(selected)request_guidance_gesture();return selected;}}
  if(input.build) {
   const auto point=placement(snapshot,camera.position,ray(camera,0,0,aspect));
   if(!point) { notice="Aim down at the board to build a relay.";return false; }
   return apply(content?first_boot_content_build(*snapshot,*point,evidence,*content):durable_first_boot_build(chapter_nodes(*snapshot),*point),evidence);
  }
  const auto aimed=aim_solids.pick(scene,camera.position,direction);const auto& hit=aimed.selected;const auto nodes=chapter_nodes(*snapshot);
  if(!hit) { notice="Aim at a visible mechanism, relay, fault or Caretaker.";return false; }
  // E/click cannot select through opaque geometry, including a nearer part
  // sharing the target UUID. Build/Delete preserve their existing semantics.
  if(input.interact&&!input.dismantle&&!aimed.visible()){notice="That view is blocked. Find a clear approach to the mechanism.";return false;}
  const auto point=aimed.point;
  last_target=hit->persistent_id;const auto found=std::find_if(snapshot->components.begin(),snapshot->components.end(),[&](const auto& record){return record.entity_id==hit->persistent_id;});
  if(content){if(const auto binding=first_boot_content_workshop_binding(content->definition())){const auto fixture=std::find(binding->fixtures.begin(),binding->fixtures.end(),hit->persistent_id);if(fixture!=binding->fixtures.end()){
   if(input.dismantle){notice="These stations stay in place. Delete dismantles built relays.";return false;}
   FirstBootChapterCommand request;request.action=static_cast<FirstBootChapterAction>(static_cast<unsigned>(FirstBootChapterAction::collect_probe)+static_cast<unsigned>(std::distance(binding->fixtures.begin(),fixture)));request.target_id=hit->persistent_id;
   const bool take_part=request.action==FirstBootChapterAction::sample_path&&assembly(snapshot)->pickup_available;
   if(take_part)request.action=FirstBootChapterAction::collect_relay_part;
   const bool changed=command(std::move(request),evidence);
   if(changed){notice=take_part?"Relay assembly collected. Carry it to the service socket.":opening_workshop_reading(first_boot_content_workshop_circuit(*owner->snapshot(),*content));request_guidance_gesture();}
   return changed;
  }}}
  if(found==snapshot->components.end()){notice="Inspecting an authored world fixture.";return false;}const auto& selected=*found;
  if(selected.type_id=="firstboot.Node") {
   const auto body=player.state().feet;
   if(std::hypot(point.x-body.x,point.y-(body.y+evidence.height*.5f),point.z-body.z)>3) { notice="Move within reach of that component before repairing or dismantling it.";return false; }
   const auto& fault=chapter_record(*snapshot,ids.fault);const auto socket=chapter_point(fault,"socket_");
   if(!input.dismantle&&chapter_number(selected,"firstboot.kind")==6&&chapter_number(selected,"capacity")==100&&
      std::hypot(chapter_number(selected,"x")-socket.x,chapter_number(selected,"z")-socket.z)<=2) {
    FirstBootChapterCommand feed;feed.action=chapter_flag(fault,"bypass_connected")?FirstBootChapterAction::disconnect_bypass:FirstBootChapterAction::connect_bypass;
    feed.relay_id=selected.entity_id;return command(std::move(feed),evidence);
   }
   const auto proposed=content?(input.dismantle?first_boot_content_dismantle(*snapshot,selected.entity_id,evidence,*content):first_boot_content_repair(*snapshot,selected.entity_id,evidence,*content)):(input.dismantle?durable_first_boot_dismantle(nodes,selected.entity_id):durable_first_boot_repair(nodes,selected.entity_id));
   if(!proposed) { notice="Already in that state.";return true; }return apply(*proposed,evidence);
  }
  if(input.dismantle) { notice="Only a built relay can be dismantled.";return false; }
  FirstBootChapterCommand requested;
  if(selected.type_id=="firstboot.Door") { requested.action=chapter_flag(selected,"open")?FirstBootChapterAction::close_door:FirstBootChapterAction::open_door;requested.target_id=selected.entity_id; }
  else if(selected.entity_id==ids.fault) {
   const auto fault=chapter_point(selected),socket=chapter_point(selected,"socket_");
   const auto isolation=content?content->definition().isolation_switch:Vec3{fault.x-2.5f,fault.y,fault.z};
   const auto part=chapter_aim::fault_part(point,socket,isolation);
   if(part==chapter_aim::FaultPart::socket) {
    if(chapter_flag(selected,"bypass_connected")) requested.action=FirstBootChapterAction::disconnect_bypass;
    else {
     requested.action=FirstBootChapterAction::connect_bypass;double nearest=2.00001;
     for(const auto& node:nodes.components) if(std::get<bool>(node.fields.at("alive"))&&chapter_number(node,"firstboot.kind")==6&&chapter_number(node,"capacity")==100) {
      const auto distance=std::hypot(chapter_number(node,"x")-socket.x,chapter_number(node,"z")-socket.z);
      if(distance<nearest) { nearest=distance;requested.relay_id=node.entity_id; }
     }
     if(requested.relay_id.empty()) { notice="Build a healthy relay at the service socket before connecting its feed.";return false; }
    }
   } else if(part==chapter_aim::FaultPart::isolation) { requested.action=FirstBootChapterAction::set_isolation;requested.enabled=!chapter_flag(selected,"isolated"); }
   else requested.action=!chapter_flag(selected,"diagnosed")?FirstBootChapterAction::inspect_fault:FirstBootChapterAction::repair_fault;
  } else if(selected.entity_id==ids.npc_quest) {
   const auto lamp=chapter_point(selected,"lamp_");requested.action=chapter_aim::lamp_part(point,lamp)?FirstBootChapterAction::connect_lamp:FirstBootChapterAction::help_caretaker;
  } else { notice="Inspecting the authored chapter.";return false; }
  return command(std::move(requested),evidence);
 }
 void reload() {
  if(critical||!owner->state().saved) { notice="Finish or retry pending outcomes before F9 reload.";return; }
  std::unique_ptr<GameplayWorld> replacement;std::unique_ptr<PlayerController> bs;std::unique_ptr<CompanionRuntime> guide;std::unique_ptr<ChapterOpeningRuntime> next_opening;std::unique_ptr<FirstBootInitialViewPolicy> next_initial_view;SceneSnapshot next;
  try {
   replacement=std::make_unique<GameplayWorld>(config.database,scope,schemas());next=view(*replacement->snapshot());
   if(opening)next_opening=std::make_unique<ChapterOpeningRuntime>(content->definition(),static_cast<HWND>(window.native_handle()),!config.offscreen_tour_proof);
   bs=std::make_unique<PlayerController>(next,safe_return(*replacement->snapshot()));if(content)next_initial_view=std::make_unique<FirstBootInitialViewPolicy>(content->definition(),region(*replacement->snapshot(),bs->state().feet)=="jenison");if(companion)guide=std::make_unique<CompanionRuntime>(*replacement->snapshot(),*content);publish_render_mesh(render_mesh(next),*replacement->snapshot());
  } catch(const std::exception& error) { notice=std::string("Reload blocked; current chapter retained: ")+error.what();return; }
  if(original_memory)original_memory->stop_for_reload();
  if(opening)opening->close();opening.swap(next_opening);initial_view.swap(next_initial_view);guidance_remaining=guidance_cooldown=0;guidance_context.clear();
  require(owner->close().ok,"Saved chapter did not close during reload");owner.swap(replacement);companion.swap(guide);scene=std::move(next);player=std::move(*bs);clock=FirstBootChapterClock{};
  if(guide_presentation){guide_presentation->reset();const auto restored=companion->state();guide_instance=guide_presentation->sample(restored.guide,0,false,restored.recall_required);}
  (void)clock.sample(*owner->snapshot());observed_region=region(*owner->snapshot(),player.state().feet);entry_previous.reset();memory_loaded=false;++reloads;refresh_memory();notice="Saved chapter restored at a collision-checked return point.";
 }
 bool frame(double elapsed,bool draw=true) {
  performance_phases::Marks phases(config.performance_controlled_motion);
  recovered_this_frame=false;const bool window_open=window.poll();
  phases.mark(performance_phases::Phase::window_poll);
  if(!window_open||(content&&std::filesystem::exists(config.stop_file))) exit_requested=true;
  poll();const auto observed_input=window.input();const auto input=config.performance_controlled_motion?controlled_performance_input:config.offscreen_tour_proof?diagnostic_controls.take():observed_input;
  phases.mark(performance_phases::Phase::owner_input);
  const bool trace_inputs=tour_diagnostic::trace_enabled(config.ordinary_input_trace,config.walkthrough,config.step==L"opening-tour");tour_diagnostic::Frame observed_frame;
  if(trace_inputs){
   observed_frame.observed=observed_input;observed_frame.effective=input;observed_frame.before=player.state();observed_frame.camera=player.camera();observed_frame.elapsed=elapsed;
   observed_frame.tick_before=clock.tick();observed_frame.revision=owner->snapshot()->revision;observed_frame.controlled=config.offscreen_tour_proof;
   observed_frame.minimized=window.minimized();observed_frame.reading=reading();observed_frame.critical=critical.has_value();observed_frame.closing=exit_requested;observed_frame.inspection=player.inspection_mode();
   observed_frame.visible=IsWindowVisible(static_cast<HWND>(window.native_handle()))!=FALSE;observed_frame.foreground=GetForegroundWindow()==static_cast<HWND>(window.native_handle());
   if(config.ordinary_input_trace){const auto focused=GetFocus();const auto native=static_cast<HWND>(window.native_handle());
    observed_frame.ordinary=true;observed_frame.frame_index=++diagnostic_frame_index;observed_frame.focus_game=focused==native;
    observed_frame.focus_owned_child=tour_diagnostic::owned_child_focus(native,focused);}
   if(config.offscreen_tour_proof)require(!observed_frame.visible&&(!opening||!IsWindowVisible(opening->panel().native_handle())),"Offscreen proof presentation became visible; stop instead of claiming headless qualification");
  }
  if(input.save) { if(owner->state().failed) notice=owner->retry_pending().message;else notice=owner->state().saved?"All visible outcomes are saved.":"Waiting for actual storage completion."; }
  const auto previous=player.state().feet;
  try {
   if(critical) { WindowInput paused;paused.active=false;player.update(paused,0);clock.advance(0,false);retry_critical(); }
   else if(reading()) { WindowInput paused;paused.active=false;player.update(paused,0);clock.advance(0,false);if(input.reload&&!exit_requested)reload(); }
   else if(!exit_requested&&!window.minimized()&&input.active) {
    player.update(input,elapsed);if(initial_view)initial_view->apply(player,scene,input);clock.advance(elapsed,!player.inspection_mode());
    if(!player.inspection_mode()) {
     double fall_height=-20;
     for(const auto& record:owner->snapshot()->components) if(record.type_id=="firstboot.Node"&&chapter_number(record,"firstboot.kind")==1) fall_height=chapter_number(record,"y")+chapter_number(record,"half_y")-20;
     if(player.state().feet.y<fall_height) { player.reset(safe_return(*owner->snapshot()));observed_region=region(*owner->snapshot(),player.state().feet);entry_previous.reset();notice="Returned to a supported clear position after the fall."; }
     else observe_body(previous);
    }
    if(!critical&&!recovered_this_frame) { if(input.reload) reload();else if(input.companion_recall) companion_action(CompanionAction::recall);else if(input.companion_wait) companion_action(CompanionAction::wait);else if(input.companion_follow) companion_action(CompanionAction::follow);else if(input.interact||input.build||input.dismantle||input.undo||input.redo) action(input); }
   } else { WindowInput paused;paused.active=false;player.update(paused,0);clock.advance(0,false); }
   if(companion){if(!critical&&!exit_requested&&!window.minimized()&&input.active&&!player.inspection_mode()&&!reading())(void)companion->advance({player.state().feet,player.state().grounded,scene.revision},elapsed);else companion->suspend();}
  } catch(const std::invalid_argument& error) { notice=std::string("Blocked: ")+error.what(); }
  phases.mark(performance_phases::Phase::physics_gameplay);
  if(guide_presentation){
   const auto guide=companion->state();const bool paused=critical||exit_requested||window.minimized()||!input.active||player.inspection_mode()||reading();
   const auto current_hint=hint(*owner->snapshot(),actor(player.state().feet),last_target);
   if(current_hint!=guidance_context){guidance_context=current_hint;request_guidance_gesture();}
   guide_instance=guide_presentation->sample(guide.guide,elapsed,paused,guide.recall_required,guidance_remaining>0);
   if(!paused){const double dt=std::min(elapsed,4./60);guidance_cooldown=std::max(0.,guidance_cooldown-dt);if(guide_presentation->clip()==GuidePresentationClip::guidance)guidance_remaining=std::max(0.,guidance_remaining-dt);}
  }
  if(original_memory){const bool paused=critical||exit_requested||window.minimized()||!input.active||player.inspection_mode()||reading();original_memory->tick(scene,player.camera(),player.state().feet,input,paused,exit_requested);}
  phases.mark(performance_phases::Phase::guide_memory);
  const auto snapshot=owner->snapshot();const auto sample=clock.sample(*snapshot);const auto status=owner->state();
  if(exit_requested&&!reopen_after_registry_change) notice=critical?"Close is retaining the physical outcome until it can publish.":status.failed?"UNSAVED. F5 retries before closing.":"Closing after actual saves finish.";
  const auto current_actor=actor(player.state().feet);
  const auto hint=this->hint(*snapshot,current_actor,last_target);
  auto guide_hint=companion?L"\nF6 Follow | F7 Wait | F8 Recall: "+wide(companion->hint()):std::wstring{};
  const bool prompt_active=status.saved&&!critical&&!exit_requested&&!window.minimized()&&input.active&&!player.inspection_mode()&&!reading();
  const auto focus=prompt_active?focused_prompt():chapter_aim::Prompt{};
  std::wstring locator,workshop_hint;
  if(content){
   const auto& camera=player.camera();
   bool workshop_objective_current=false;
   locator=wide(chapter_aim::workshop_guidance(*snapshot,content.get(),player.state().feet,camera.position,
    camera.yaw,camera.pitch,prompt_active,focus,&workshop_objective_current));
   if(!workshop_objective_current){
    const auto& fault=chapter_record(*snapshot,ids().fault);
    const auto cue=chapter_aim::isolation_guidance(player.state().feet,camera.yaw,content->definition().isolation_switch,
     chapter_number(fault,"capacity"),chapter_flag(fault,"isolated"),prompt_active);
    if(!cue.empty())locator=wide(cue);
   }
   if(!locator.empty())locator+=L"\n";
   if(workshop_hud&&prompt_active){
    const auto direction=ray(camera,0,0,static_cast<float>(window.width())/static_cast<float>(window.height()));
    const auto projected=placement(snapshot,camera.position,direction);
    const auto bypass=chapter_aim::workshop_bypass_guidance(*snapshot,content.get(),current_actor,projected,camera.yaw,prompt_active,assembly(snapshot));
    if(!bypass.empty())locator+=wide(bypass)+L"\n";
   }
   if(!workshop_objective_current){workshop_hint=wide(first_boot_content_workshop_hint(*snapshot,*content));if(!workshop_hint.empty())guide_hint+=L"\n"+workshop_hint;}
  }
  const auto interaction=wide(chapter_aim::line(focus,prompt_active));
  const auto saved=wide(std::string(status.saved&&!critical?"SAVED":status.failed?"UNSAVED / RETRY":"SAVING")+" | visible "+std::to_string(status.visible_revision)+" | durable "+std::to_string(status.durable_revision));
  auto next_hud=L"WASD walk | Right-drag look | Space jump | V camera | F2 inspect | F5 retry | F9 reload\n"+interaction+L" | B relay | Delete dismantle | Ctrl+Y help / Ctrl+Z decline\n"+locator+wide(hint)+guide_hint+L"\nRecorded (acknowledged): "+wide(remembered)+L"\n"+
   (original_memory?L"Original memories: E selects a nearby station; P Play/Resume | O Pause | K Stop. No playback state is saved.\n":L"")+saved+L"\n"+wide(notice);
  std::wstring compact;
  if(workshop_hud){
   compact=L"WASD walk | Right-drag look | F1 controls and details\n"+interaction+L"\n"+locator+L"Adam: "+wide(hint);
   if(!workshop_hint.empty())compact+=L"\n"+workshop_hint;
   if(original_memory)compact+=L"\nP Play/Resume | O Pause | K Stop";
   compact+=L"\n"+saved;
   if(status.failed)compact+=L"\nF5 retry save";
   if(!notice.empty())compact+=L"\n"+wide(notice);
   next_hud+=L"\nF1 back to play view";
  }
  // NativeWindow handles layout on WM_SIZE. Unchanged status must not
  // invalidate its GDI text/layout on every rendered frame.
  if(next_hud!=hud_status||compact!=compact_hud_status){
   if(workshop_hud)window.set_status_views(compact,next_hud);else window.set_status(next_hud);
   hud_status=std::move(next_hud);compact_hud_status=std::move(compact);++hud_text_publications;
  }
  phases.mark(performance_phases::Phase::hud);
  if(draw&&!window.minimized()) {
   auto transient=first_boot_chapter_hazard_mesh(*snapshot,sample);const auto body=avatar(scene,player);
   require(transient.vertices.size()+body.vertices.size()<=Dx12Renderer::transient_vertex_limit,"Chapter transient geometry exceeds fixed frame budget");
   transient.vertices.insert(transient.vertices.end(),body.vertices.begin(),body.vertices.end());render_frame(player.camera(),transient);
   if(recording){recording->tick(renderer,reading()?opening->panel().body_handle():nullptr);if(!recording->failure().empty())notice="Recording stopped; gameplay/save remain active: "+recording->failure();}
  }
  phases.mark(performance_phases::Phase::render);
  if(trace_inputs){observed_frame.after=player.state();observed_frame.tick_after=clock.tick();observed_frame.third_person=player.third_person();
   if(config.ordinary_input_trace){observed_frame.visible_revision=status.visible_revision;observed_frame.durable_revision=status.durable_revision;
    observed_frame.durable_sequence=status.durable_sequence;observed_frame.pending_batches=status.pending_batches;
    observed_frame.saved=status.saved&&!critical;observed_frame.save_failed=status.failed;}
   input_trace.frame(observed_frame);}
  bool keep_running=true;
  if(exit_requested&&!critical&&status.saved) { if(opening)opening->close();if(original_memory)original_memory->close();require(owner->close().ok,"Saved chapter close failed");saved_close_complete=true;keep_running=false; }
  phases.mark(performance_phases::Phase::tail_close);
  if(config.performance_controlled_motion)controlled_frame_stages=phases.stages();
  return keep_running;
 }
};
void chapter_drain(ChapterLive& live) {
 const auto deadline=Clock::now()+std::chrono::seconds(15);
 while(live.critical||!live.owner->state().saved) { require(live.tour_frame(0),"Chapter closed before its outcomes drained");require(!live.owner->state().failed,"Chapter save failed: "+live.owner->state().error);require(Clock::now()<deadline,"Chapter did not drain within its bounded deadline");std::this_thread::sleep_for(std::chrono::milliseconds(1)); }
}
struct ChapterHud { int height=0,needed=0;bool fits=false,captured=false; };
ChapterHud chapter_hud(const NativeWindow& window,const std::filesystem::path& path) {
 const auto parent=static_cast<HWND>(window.native_handle());HWND child=nullptr;std::wstring text;
 while((child=FindWindowExW(parent,child,L"STATIC",nullptr))) {
  const auto length=GetWindowTextLengthW(child);if(length<=0||length>16384) continue;text.assign(static_cast<std::size_t>(length)+1,L'\0');
  text.resize(static_cast<std::size_t>(GetWindowTextW(child,text.data(),static_cast<int>(text.size()))));if(text.find(L"E (centre):")!=std::wstring::npos) break;
 }
 require(child!=nullptr,"Actual chapter HUD control is missing");RECT client{};require(GetClientRect(child,&client)!=0,"Cannot measure actual HUD rectangle");
 HDC display=GetDC(child);require(display!=nullptr,"Cannot measure HUD font");HDC memory=CreateCompatibleDC(display);require(memory!=nullptr,"Cannot stage actual HUD capture");
 auto font=reinterpret_cast<HFONT>(SendMessageW(child,WM_GETFONT,0,0));if(!font) font=static_cast<HFONT>(GetStockObject(DEFAULT_GUI_FONT));
 const auto previous_font=SelectObject(memory,font);RECT measured{0,0,client.right,0};
 DrawTextW(memory,text.c_str(),static_cast<int>(text.size()),&measured,DT_CALCRECT|DT_WORDBREAK|DT_NOPREFIX);
 BITMAPINFO info{};info.bmiHeader.biSize=sizeof(BITMAPINFOHEADER);info.bmiHeader.biWidth=client.right;info.bmiHeader.biHeight=-client.bottom;
 info.bmiHeader.biPlanes=1;info.bmiHeader.biBitCount=32;info.bmiHeader.biCompression=BI_RGB;void* pixels=nullptr;
 HBITMAP bitmap=CreateDIBSection(display,&info,DIB_RGB_COLORS,&pixels,nullptr,0);require(bitmap!=nullptr,"Cannot allocate bounded HUD bitmap");
 const auto previous_bitmap=SelectObject(memory,bitmap);PatBlt(memory,0,0,client.right,client.bottom,BLACKNESS);
 SendMessageW(child,WM_PRINT,reinterpret_cast<WPARAM>(memory),PRF_CLIENT|PRF_ERASEBKGND);GdiFlush();
 const auto* actual=static_cast<const std::uint32_t*>(pixels);std::size_t glyph_pixels=0;
 for(std::size_t n=0;n<static_cast<std::size_t>(client.right)*client.bottom;++n) if((actual[n]&0x00ffffffu)>0x00404040u) ++glyph_pixels;
 const bool captured=glyph_pixels>100;
 if(captured) {
  BITMAPFILEHEADER header{};header.bfType=0x4d42;header.bfOffBits=sizeof(header)+sizeof(BITMAPINFOHEADER);header.bfSize=header.bfOffBits+static_cast<DWORD>(client.right*client.bottom*4);
  std::ofstream file(path,std::ios::binary);file.write(reinterpret_cast<const char*>(&header),sizeof(header));file.write(reinterpret_cast<const char*>(&info.bmiHeader),sizeof(info.bmiHeader));file.write(static_cast<const char*>(pixels),static_cast<std::streamsize>(client.right)*client.bottom*4);require(file.good(),"Cannot save actual HUD capture");
 }
 SelectObject(memory,previous_bitmap);SelectObject(memory,previous_font);DeleteObject(bitmap);DeleteDC(memory);ReleaseDC(child,display);
 return {client.bottom,measured.bottom,measured.bottom<=client.bottom,captured};
}
std::size_t chapter_guide_readback(ChapterLive& live){
 if(!live.guide_instance||!live.companion||!live.companion->state().guide)return 0;
 const auto feet=live.companion->state().guide->character.feet;
 const auto read=[](const std::filesystem::path& path){
  const auto size=std::filesystem::file_size(path);require(size>54&&size<=64u*1024u*1024u,"Character proof capture exceeds its bound");
  std::ifstream file(path,std::ios::binary);std::vector<unsigned char> bytes(static_cast<std::size_t>(size));
  require(static_cast<bool>(file.read(reinterpret_cast<char*>(bytes.data()),static_cast<std::streamsize>(bytes.size()))),"Character proof capture cannot be read");return bytes;
 };
 // These are proof cameras only. Capture every authored cardinal view with and
 // without the same instance; no geometry, doors, lights or world state change.
 std::size_t maximum=0;constexpr float pi=3.14159265358979323846f;
 for(unsigned view=0;view<4;++view){
  const auto yaw=static_cast<float>(view)*pi*.5f;Camera camera;camera.yaw=yaw;camera.pitch=-.08f;
  camera.position={feet.x-2.7f*std::sin(yaw),feet.y+1.15f,feet.z-2.7f*std::cos(yaw)};
  auto without=live.config.capture;without+=L".guide-"+std::to_wstring(view)+L"-without.bmp";
  auto with=live.config.capture;with+=L".guide-"+std::to_wstring(view)+L"-with.bmp";
  live.renderer.render(camera);live.renderer.capture(without);const auto base=read(without);
  live.renderer.render(camera,{},*live.guide_instance);live.renderer.capture(with);const auto character=read(with);
  require(base.size()==character.size(),"Paired character captures changed dimensions");std::size_t changed=0;
  for(std::size_t byte=54;byte<base.size();++byte)changed+=base[byte]!=character[byte];maximum=std::max(maximum,changed);
 }return maximum;
}
void chapter_report(ChapterLive& live) {
 const auto& o=live.config;if(o.capture.empty()||o.report.empty()) return;
 const auto snapshot=live.owner->snapshot();const auto state=live.owner->state();const auto ids=live.ids();
 auto pov=o.capture;pov+=L".pov.bmp";for(int n=0;n<3;++n) live.render_frame(live.player.camera(),first_boot_chapter_hazard_mesh(*snapshot,live.clock.sample(*snapshot)));live.renderer.capture(pov);
 auto hud_path=o.capture;hud_path+=L".hud.bmp";const auto hud=chapter_hud(live.window,hud_path);
 const auto character_pixels=chapter_guide_readback(live);
 Camera overview;for(int n=0;n<3;++n) { live.window.poll();live.renderer.render(overview); }
 const auto pixels=live.renderer.capture(o.capture);live.renderer.wait_idle();const auto stats=live.renderer.stats();require(pixels>10000&&stats.debug_errors==0&&stats.debug_warnings==0,"Chapter GPU readback or debug diagnostics failed");
 std::ofstream file(o.report);require(file.good(),"Cannot create chapter proof report");
 file<<std::setprecision(17)<<"{\"schema_version\":1,\"status\":\"passed\",\"completed_at\":"<<quoted(utc())<<",\"scope\":{\"project_id\":"<<quoted(live.scope.project_id)<<",\"world_id\":"<<quoted(live.scope.world_id)<<",\"branch_id\":"<<quoted(live.scope.branch_id)<<",\"timeline_id\":"<<quoted(live.scope.timeline_id)<<",\"context\":"<<quoted(live.scope.context==GameplayContext::temporary_play?"temporary_play":"player_world")<<"},\"visible_revision\":"<<state.visible_revision<<",\"durable_revision\":"<<state.durable_revision<<",\"durable_sequence\":"<<state.durable_sequence<<",\"saved\":"<<(state.saved&&!live.critical?"true":"false")<<",\"pending_batches\":"<<state.pending_batches<<",\"chapter_ids\":{\"fault\":"<<quoted(ids.fault)<<",\"main_door\":"<<quoted(ids.main_door)<<",\"service_door\":"<<quoted(ids.service_door)<<",\"pencil_door\":"<<quoted(ids.pencil_door)<<",\"progress\":"<<quoted(ids.progress)<<",\"npc_quest\":"<<quoted(ids.npc_quest)<<"},\"components\":[";
 bool first=true;for(const auto& record:snapshot->components) {
  if(!first) file<<',';first=false;file<<"{\"entity_id\":"<<quoted(record.entity_id)<<",\"type\":"<<quoted(record.type_id)<<",\"fields\":{";bool field_first=true;
  for(const auto& [name,value]:record.fields) { if(!field_first) file<<',';field_first=false;file<<quoted(name)<<':';std::visit([&](const auto& typed) { using T=std::decay_t<decltype(typed)>;if constexpr(std::is_same_v<T,std::string>) file<<quoted(typed);else if constexpr(std::is_same_v<T,bool>) file<<(typed?"true":"false");else file<<typed; },value); }file<<"}}";
 }
 file<<"],\"events\":[";first=true;std::uint64_t cursor=0;std::size_t count=0,bytes=0;
 for(;;) {
  const auto page=live.owner->read_batches(cursor);if(page.empty()) break;
  for(const auto& batch:page) { if(batch.revision>state.durable_revision) continue;const auto charge=gameplay_codec::encode_batch(batch).size();require(count<4096&&charge<=16*1024*1024-bytes,"Chapter proof history exceeds its bounds");++count;bytes+=charge;
   for(const auto& event:batch.events) { if(!first) file<<',';first=false;file<<"{\"event_id\":"<<quoted(event.event_id)<<",\"operation_id\":"<<quoted(event.operation_id)<<",\"sequence\":"<<event.sequence<<",\"revision\":"<<batch.revision<<",\"type\":"<<quoted(semantic_event_type(event))<<",\"source\":"<<quoted(event.provenance.source_id)<<",\"subject_id\":"<<quoted(event.subject_ids.front())<<'}'; }
  }cursor=page.back().revision;
 }
 file<<']';
 if(live.content){
  const auto lighting=first_boot_content_lighting(*snapshot,*live.content);
  const auto supply=first_boot_content_supply(*snapshot,*live.content);
  file<<",\"lighting\":{\"enabled\":"<<(lighting.enabled?"true":"false")<<",\"points\":"<<lighting.points.size()<<",\"directional\":"<<(lighting.directional?"true":"false")<<",\"main_power\":"<<(supply.main?"true":"false")<<",\"bypass_power\":"<<(supply.bypass?"true":"false")<<'}';
  if(live.companion){const auto guide=live.companion->state();file<<",\"companion\":{\"entity_id\":"<<quoted(live.content->definition().companions.front().entity_id)<<",\"follow\":"<<(guide.saved.intent==GuideIntent::follow?"true":"false")<<",\"anchor\":["<<guide.saved.waiting_anchor.x<<','<<guide.saved.waiting_anchor.y<<','<<guide.saved.waiting_anchor.z<<"],\"recall_required\":"<<(guide.recall_required?"true":"false")<<",\"scene_revision\":"<<guide.scene_revision<<",\"controls_verified\":"<<(live.proof_companion_controls?"true":"false")<<",\"follow_route_verified\":"<<(live.proof_companion_route?"true":"false")<<",\"character_rendered\":"<<(character_pixels>300?"true":"false")<<",\"character_kind\":"<<quoted(live.placed_assets&&live.placed_assets->companion_model()?"cooked_character":"temporary_articulated")<<",\"character_readback_changed_bytes\":"<<character_pixels<<",\"character_frames\":"<<stats.character_frames<<",\"feet\":";if(guide.guide){const auto feet=guide.guide->character.feet;file<<'['<<feet.x<<','<<feet.y<<','<<feet.z<<']';}else file<<"null";file<<",\"model_reference\":";const auto& model=live.content->definition().companions.front().model;if(model)file<<"{\"asset_id\":"<<quoted(model->asset_id)<<",\"asset_sha256\":"<<quoted(model->asset_sha256)<<",\"pack_sha256\":"<<quoted(model->pack_sha256)<<'}';else file<<"null";file<<'}';}
  file<<",\"content\":{\"definition_id\":"<<quoted(live.content->definition().definition_id)<<",\"revision\":"<<live.content->definition().revision<<",\"fingerprint\":"<<quoted(live.content->fingerprint())<<"},\"scene_objects\":[";bool object_first=true;
  for(const auto& object:live.scene.objects){if(!object_first)file<<',';object_first=false;file<<"{\"persistent_id\":"<<quoted(object.persistent_id)<<",\"name\":"<<quoted(object.name)<<",\"center\":["<<object.center.x<<','<<object.center.y<<','<<object.center.z<<"],\"half_extent\":["<<object.half_extent.x<<','<<object.half_extent.y<<','<<object.half_extent.z<<"]}";}file<<']';
 }
 if(live.opening)file<<",\"opening_inspections_count\":"<<live.opening->count()<<",\"opening_controls_verified\":"<<(live.proof_opening_controls?"true":"false")<<",\"opening_control_checks\":"<<live.proof_opening_checks<<",\"opening_panel_visible\":"<<(live.reading()?"true":"false");
 if(live.guide_presentation)file<<",\"guide_clip\":"<<static_cast<unsigned>(live.guide_presentation->clip())<<",\"guidance_gestures\":"<<live.guidance_gestures;
 if(live.recording)live.recording->write_report(file);
 file<<",\"tour_input_profile\":"<<quoted(live.config.offscreen_tour_proof?"offscreen-controlled-proof":"native-window")
  <<",\"offscreen_controlled_proof\":"<<(live.config.offscreen_tour_proof?"true":"false")<<",\"os_focus_input_verified\":false,\"frame_input_trace\":"<<(live.config.input_trace.empty()?"null":quoted(narrow(live.config.input_trace.native())))
  <<",\"player_camera_mode\":"<<quoted(live.player.third_person()?"third-person":"first-person")
  <<",\"initial_view_applied\":"<<(live.initial_view&&live.initial_view->applied()?"true":"false")<<",\"opening_tour_verified\":"<<(live.proof_opening_tour?"true":"false")<<",\"opening_tour_realtime\":"<<(live.config.walkthrough?"true":"false")<<",\"human_pacing_measured\":false,\"tour_reads\":[";
 bool first_read=true;for(const auto& read:live.tour_reads){if(!first_read)file<<',';first_read=false;file<<"{\"role\":"<<quoted(std::string(opening_tour_role_name(read.role)))<<",\"target_uuid\":"<<quoted(read.id)<<",\"title\":"<<quoted(read.title)<<",\"text\":"<<quoted(read.text)<<",\"source\":"<<quoted(read.source)<<",\"glyph_capture\":"<<quoted(narrow(read.glyph.native()))<<",\"revision_before\":"<<read.revision_before<<",\"revision_after\":"<<read.revision_after<<",\"sequence_before\":"<<read.sequence_before<<",\"sequence_after\":"<<read.sequence_after<<'}';}file<<']';
 if(live.original_memory){file<<",\"memory_playback\":";live.original_memory->write_report(file);file<<",\"memory_controls_verified\":"<<(live.proof_memory_controls?"true":"false")<<",\"memory_control_checks\":"<<live.proof_memory_checks<<",\"memory_paused_frame\":"<<live.proof_memory_paused_frame<<",\"memory_resumed_frame\":"<<live.proof_memory_resumed_frame;}
 file<<",\"remembered\":"<<quoted(live.remembered)<<",\"hint\":"<<quoted(live.hint(*snapshot,live.actor(live.player.state().feet)))<<",\"metrics\":{\"debug_layer\":"<<(stats.debug_layer?"true":"false")<<",\"debug_errors\":"<<stats.debug_errors<<",\"debug_warnings\":"<<stats.debug_warnings<<",\"nonbackground_pixels\":"<<pixels<<",\"hud_readback\":"<<(has_status(live.window,L"E (centre):")?"true":"false")<<",\"hud_fits\":"<<(hud.fits?"true":"false")<<",\"hud_capture\":"<<(hud.captured?"true":"false")<<",\"hud_height\":"<<hud.height<<",\"hud_needed_height\":"<<hud.needed<<",\"walking_ticks\":"<<live.player.state().ticks<<",\"active_tick\":"<<live.clock.tick()<<",\"reload\":"<<(live.reloads?"true":"false")<<",\"repair_route\":"<<(live.proof_repair?"true":"false")<<",\"bypass_route\":"<<(live.proof_bypass?"true":"false")<<",\"door_cycle\":"<<(live.proof_door?"true":"false")<<",\"help\":"<<(live.proof_help?"true":"false")<<",\"decline\":"<<(live.proof_decline?"true":"false")<<",\"depart_return\":"<<(live.proof_return?"true":"false")<<",\"feed_loss\":"<<(live.proof_feed_loss?"true":"false")<<",\"fall_return\":"<<(live.proof_fall?"true":"false")<<",\"relay_rebuild\":"<<(live.proof_rebuild?"true":"false")<<",\"hazard_recovery\":"<<(live.proof_hazard?"true":"false")<<",\"hazard_pause\":"<<(live.proof_pause?"true":"false")<<",\"critical_backpressure\":"<<(live.proof_backpressure?"true":"false")<<",\"empty_socket\":"<<(live.proof_empty_socket?"true":"false")<<",\"remote_nodes\":"<<(live.proof_remote?"true":"false")<<",\"translated_walk\":"<<(live.proof_translated?"true":"false")<<",\"reload_failure\":"<<(live.proof_reload_failure?"true":"false")<<",\"recovery_input_consumed\":"<<(live.proof_consumed?"true":"false")<<",\"stale_intent_rejected\":"<<(live.proof_stale?"true":"false")<<",\"live_retry\":"<<(live.proof_live_retry?"true":"false")<<",\"close_drained\":"<<(live.proof_close_drained?"true":"false")<<"}}\n";require(file.good(),"Cannot finish chapter report");
}
Vec3 chapter_board(const ChapterLive& live) {
 for(const auto& record:live.owner->snapshot()->components) if(record.type_id=="firstboot.Node"&&chapter_number(record,"firstboot.kind")==1)
  return {static_cast<float>(chapter_number(record,"x")),static_cast<float>(chapter_number(record,"y")+chapter_number(record,"half_y")),static_cast<float>(chapter_number(record,"z"))};
 throw std::runtime_error("Chapter proof board missing");
}
void chapter_hint_capture(const ChapterLive& live,const wchar_t* checkpoint) {
 auto path=live.config.capture;path+=checkpoint;const auto hud=chapter_hud(live.window,path);
 require(hud.fits&&hud.captured,"Actual checkpoint hint HUD did not fit or render");
}
Vec3 chapter_target(const ChapterLive& live,const std::string& id,const std::string& name={}) {
 for(const auto& object:live.scene.objects) if(object.persistent_id==id&&(name.empty()||object.name==name)) return object.center;
 throw std::runtime_error("Authored interaction surface is missing: "+name);
}
bool chapter_press(ChapterLive& live,Vec3 target,WPARAM code='E',bool wait=true) {
 aim(live.player,target);live.proof_key(static_cast<unsigned>(code));bool result=false;
 try { result=live.action(live.proof_input()); } catch(const std::invalid_argument& error) { live.notice=std::string("Blocked: ")+error.what(); }
 if(wait&&result) chapter_drain(live);require(live.tour_frame(0),"Native chapter closed during key interaction");return result;
}
void chapter_walk(ChapterLive& live,float relative_x,float relative_z,unsigned limit=800,bool must_arrive=true) {
 const auto board=chapter_board(live);const float x=board.x+relative_x,z=board.z+relative_z;
 const auto until=Clock::now()+std::chrono::seconds(30);const float reach=live.config.walkthrough?.28f:.14f;
 live.input_trace.begin_walk(x,z);live.proof_forward(true);
 for(unsigned tick=0;tick<(live.config.walkthrough?15000u:limit);++tick) {
  const auto feet=live.player.state().feet;if(std::hypot(feet.x-x,feet.z-z)<reach) break;
  if(live.config.walkthrough&&Clock::now()>=until){
   live.input_trace.failed_walk();const auto actual=live.player.state().feet;
   throw std::runtime_error("Real-time walkthrough route blocked; no teleport was substituted. Feet=("+std::to_string(actual.x)+","+std::to_string(actual.y)+","+std::to_string(actual.z)+") target=("+std::to_string(x)+","+std::to_string(z)+"); consumed frame inputs retained in TOUR_INPUT_TRACE");
  }
  aim(live.player,{x,live.player.eye_anchor().y,z});require(live.tour_frame(1.0/60,tick%16==0),"Native walk unexpectedly closed");
  require(live.player.state().feet.y>=board.y-.2f,"Actual capsule lost motherboard support");
 }
 live.proof_forward(false);require(live.tour_frame(0),"Native walk final frame closed");
 if(must_arrive) {
  const float tolerance=live.config.walkthrough?.35f:.2f;
  auto within_waypoint=[&] {const auto feet=live.player.state().feet;return std::hypot(feet.x-x,feet.z-z)<tolerance&&feet.y>=board.y-.2f;};
  // A release frame can end between stepping off a low surface and landing.
  // Keep W released and let normal physics settle only while still at the waypoint.
  if(live.config.walkthrough&&!live.player.state().grounded&&within_waypoint()) {
   const auto deadline=Clock::now()+std::chrono::seconds(1);
   const auto from=live.player.state().feet;
   do {require(live.tour_frame(0),"Native walkthrough closed while landing");}
   while(!live.player.state().grounded&&within_waypoint()&&Clock::now()<deadline);
   const auto to=live.player.state().feet;
   std::cerr<<"WORKSHOP_TOUR_LANDING {\"from\":["<<from.x<<','<<from.y<<','<<from.z<<"],\"to\":["<<to.x<<','<<to.y<<','<<to.z<<"],\"grounded\":"<<(live.player.state().grounded?"true":"false")<<"}\n";
  }
  const auto feet=live.player.state().feet;const bool arrived=within_waypoint()&&live.player.state().grounded;
  if(!arrived)live.input_trace.failed_walk();require(arrived,
   "Actual native walk blocked toward ("+std::to_string(relative_x)+","+std::to_string(relative_z)+") at ("+std::to_string(feet.x-board.x)+","+std::to_string(feet.y-board.y)+","+std::to_string(feet.z-board.z)+")");
 }
 chapter_drain(live);
}
void chapter_choice(ChapterLive& live,bool help) {
 SendMessageW(static_cast<HWND>(live.window.native_handle()),WM_KEYDOWN,VK_CONTROL,0);key(live.window,help?'Y':'Z');SendMessageW(static_cast<HWND>(live.window.native_handle()),WM_KEYUP,VK_CONTROL,0);
 require(live.action(live.window.input()),"Actual Caretaker key choice failed: "+live.notice);chapter_drain(live);require(live.tour_frame(0),"Choice frame closed");
}
void chapter_settle(ChapterLive& live) { if(live.config.walkthrough){const auto deadline=Clock::now()+std::chrono::seconds(5);while(!live.player.state().grounded){require(Clock::now()<deadline,"Real-time capsule did not settle within5wallseconds");require(live.tour_frame(0),"Real-time chapter settle closed");}}else for(unsigned n=0;n<30;++n)require(live.tour_frame(1.0/60,n==29),"Chapter settle frame closed");require(live.player.state().grounded,"Chapter capsule did not settle on actual geometry"); }
// Diagnostic input must approach the same authored switch as the current tour.
// Keep actual movement, collision, reach and occlusion checks in force.
bool chapter_press_isolation(ChapterLive& live) {
 const auto before=live.player.state().feet;const bool workshop=live.content&&first_boot_content_workshop_binding(live.content->definition()).has_value();
 if(workshop){const auto board=chapter_board(live);chapter_walk(live,live.content->definition().isolation_switch.x-1.3f-board.x,before.z-board.z);}
 const bool pressed=chapter_press(live,chapter_target(live,live.ids().fault,"Isolation switch"));
 if(workshop){const auto board=chapter_board(live);chapter_walk(live,before.x-board.x,before.z-board.z);}
 return pressed;
}
void chapter_prepare_fault(ChapterLive& live) {
 const auto ids=live.ids();chapter_walk(live,-37,-25);chapter_walk(live,-37,-6.5f);chapter_walk(live,-35.5f,-6.5f);
 require(chapter_press(live,chapter_target(live,ids.fault,"Downstream power fault")),"Actual E fault inspection failed: "+live.notice);
 chapter_walk(live,-35.5f,-5.2f);require(chapter_press_isolation(live),"Actual E isolation switch failed: "+live.notice);
 require(chapter_flag(chapter_record(*live.owner->snapshot(),ids.fault),"diagnosed")&&chapter_flag(chapter_record(*live.owner->snapshot(),ids.fault),"isolated"),"Native fault diagnosis/isolation did not publish");
}
void chapter_repair_route(ChapterLive& live) {
 const auto ids=live.ids();chapter_prepare_fault(live);chapter_walk(live,-33,-5.2f);
 require(chapter_press(live,chapter_target(live,ids.fault,"Downstream power fault")),"Actual E downstream repair failed: "+live.notice);
 chapter_walk(live,-35.5f,-5.2f);require(chapter_press_isolation(live),"Actual E main reconnection failed: "+live.notice);
 chapter_walk(live,-37,-5.2f);chapter_walk(live,-37,1.9f);chapter_walk(live,-33,1.9f);
 chapter_walk(live,-33,6,100,false);const auto blocked=live.player.state().feet;
 require(blocked.z-chapter_board(live).z>3.1f&&blocked.z-chapter_board(live).z<3.6f,"Closed main door failed to stop actual capsule");
 chapter_walk(live,-33,1.9f);require(chapter_press(live,chapter_target(live,ids.main_door)),"Actual E powered main door failed: "+live.notice);chapter_walk(live,-33,6);
 require(chapter_text(chapter_record(*live.owner->snapshot(),ids.progress),"first_route")=="repair","Continuous native main aperture did not earn repair route");
 chapter_walk(live,-33,8);chapter_walk(live,-37,8);chapter_walk(live,-37,10.7f);
 require(chapter_press(live,chapter_target(live,ids.pencil_door)),"Actual E Pencil Room door failed: "+live.notice);chapter_walk(live,-37,15);
 require(chapter_flag(chapter_record(*live.owner->snapshot(),ids.progress),"pencil_visited"),"Actual body did not enter Pencil Room");
 chapter_walk(live,-37,10.7f);chapter_walk(live,-33,8);chapter_walk(live,-33,6);live.proof_repair=true;
}
namespace workshop_tour {
void station(ChapterLive&,const OpeningWorkshopBinding&,std::size_t,std::size_t expected_delta=1);
void go(ChapterLive&,const std::string&);
}
void chapter_bypass_route(ChapterLive& live) {
 if(live.content)if(const auto binding=first_boot_content_workshop_binding(live.content->definition())){
  const auto& saved=chapter_record(*live.owner->snapshot(),binding->fixtures[4]);
  const bool need_probe=!chapter_flag(saved,"has_probe"),need_path=chapter_text(saved,"path_sample").empty();
  if(need_probe)workshop_tour::station(live,*binding,0);
  if(need_path)workshop_tour::station(live,*binding,2);
  if(first_boot_content_relay_assembly(*live.owner->snapshot(),*live.content).pickup_available)workshop_tour::station(live,*binding,2);
  workshop_tour::go(live,"west");
 }
 const auto ids=live.ids();chapter_prepare_fault(live);chapter_walk(live,-42,-5.2f);
 const auto revision=live.owner->snapshot()->revision;
 require(!chapter_press(live,chapter_target(live,ids.fault,"Service relay socket"))&&live.owner->snapshot()->revision==revision,"Empty socket E must remain a recoverable no-effect interaction");live.proof_empty_socket=true;
 const auto& fault=chapter_record(*live.owner->snapshot(),ids.fault);const auto socket=chapter_point(fault,"socket_");
 require(chapter_press(live,{socket.x,socket.y+1,socket.z},'B'),"Actual B service relay build failed: "+live.notice);
 const auto nodes=chapter_nodes(*live.owner->snapshot());std::string relay;
 for(const auto& node:nodes.components) if(std::get<bool>(node.fields.at("alive"))&&chapter_number(node,"firstboot.kind")==6&&std::hypot(chapter_number(node,"x")-socket.x,chapter_number(node,"z")-socket.z)<.1) relay=node.entity_id;
 require(!relay.empty()&&chapter_press(live,chapter_target(live,relay)),"Actual E healthy relay feed failed: "+live.notice);
 require(has_status(live.window,L"service door")&&has_status(live.window,L"relay feed holds"),
  "Actual connected-bypass HUD must direct the healthy service door before hub entry");
 chapter_hint_capture(live,L".connected-feed.hud.bmp");
 chapter_walk(live,-39.5f,-5.2f);chapter_walk(live,-39.5f,1.9f);chapter_walk(live,-41,1.9f);
 require(chapter_press(live,chapter_target(live,ids.service_door)),"Actual E service door failed: "+live.notice);chapter_walk(live,-41,6);
 require(chapter_text(chapter_record(*live.owner->snapshot(),ids.progress),"first_route")=="bypass"&&chapter_flag(chapter_record(*live.owner->snapshot(),ids.progress),"bypass_used"),"Continuous service aperture did not earn bypass route");
 chapter_walk(live,-41,8);chapter_walk(live,-37,8);chapter_walk(live,-37,10.7f);
 require(chapter_press(live,chapter_target(live,ids.pencil_door)),"Actual bypass-powered Pencil Room door failed: "+live.notice);chapter_walk(live,-37,15);
 require(chapter_flag(chapter_record(*live.owner->snapshot(),ids.progress),"pencil_visited"),"Actual bypass body did not reach Pencil Room");
 chapter_walk(live,-37,10.7f);chapter_walk(live,-37,8);chapter_walk(live,-41,8);chapter_walk(live,-41,6);live.proof_bypass=true;
}
void chapter_door_cycle(ChapterLive& live) {
 const auto ids=live.ids();const bool bypass=chapter_text(chapter_record(*live.owner->snapshot(),ids.progress),"first_route")=="bypass";
 const auto door_id=bypass?ids.service_door:ids.main_door;const auto& door=chapter_record(*live.owner->snapshot(),door_id);
 require(chapter_flag(door,"open"),"Door cycle requires the claimed route to be open");const auto x=static_cast<float>(chapter_number(door,"x"))-chapter_board(live).x;
 chapter_walk(live,-37,8);chapter_walk(live,x,8);chapter_walk(live,x,1.9f);chapter_walk(live,x,4.0f);const auto revision=live.owner->snapshot()->revision;
 require(!chapter_press(live,chapter_target(live,door_id))&&live.owner->snapshot()->revision==revision&&chapter_flag(chapter_record(*live.owner->snapshot(),door_id),"open"),"Actual occupied capsule must block door closure without publication");
 chapter_walk(live,x,1.9f);require(chapter_press(live,chapter_target(live,door_id))&&!chapter_flag(chapter_record(*live.owner->snapshot(),door_id),"open"),"Clear doorway did not close through E");
 require(chapter_press(live,chapter_target(live,door_id))&&chapter_flag(chapter_record(*live.owner->snapshot(),door_id),"open"),"Latched doorway did not reopen through E");chapter_walk(live,x,6);live.proof_door=true;
}
void chapter_caretaker(ChapterLive& live,bool help) {
 const auto ids=live.ids();chapter_walk(live,-36.5f,8);chapter_walk(live,-38,8);chapter_walk(live,-38,6.5f);chapter_choice(live,help);
 const auto state=std::get<std::int64_t>(chapter_record(*live.owner->snapshot(),ids.npc_quest).fields.at("state"));
 require(state==static_cast<std::int64_t>(help?QuestState::active:QuestState::declined),"Actual key choice contradicted Caretaker quest state");
 if(help) {
  chapter_walk(live,-38,10);require(chapter_press(live,chapter_target(live,ids.npc_quest,"Table lamp")),"Actual E table lamp failed: "+live.notice);
  require(chapter_flag(chapter_record(*live.owner->snapshot(),ids.npc_quest),"lamp_connected"),"Lamp connection not published");live.proof_help=true;
 } else live.proof_decline=true;
}
void chapter_return(ChapterLive& live) {
 const auto ids=live.ids();const auto& progress=chapter_record(*live.owner->snapshot(),ids.progress);
 const auto before_departures=std::get<std::int64_t>(progress.fields.at("departures")),before_returns=std::get<std::int64_t>(progress.fields.at("returns"));
 const auto door_id=chapter_text(progress,"first_route")=="bypass"?ids.service_door:ids.main_door;
 const auto x=static_cast<float>(chapter_number(chapter_record(*live.owner->snapshot(),door_id),"x"))-chapter_board(live).x;
 chapter_walk(live,-36.5f,8);chapter_walk(live,x,8);chapter_walk(live,x,1.9f);chapter_walk(live,x,6);
 const auto& after=chapter_record(*live.owner->snapshot(),ids.progress);require(std::get<std::int64_t>(after.fields.at("departures"))==before_departures+1&&std::get<std::int64_t>(after.fields.at("returns"))==before_returns+1,"Actual departure/return did not append one physical loop");live.proof_return=true;
}
void chapter_feed_loss(ChapterLive& live) {
 const auto ids=live.ids();const auto relay=chapter_text(chapter_record(*live.owner->snapshot(),ids.fault),"bypass_relay");require(!relay.empty(),"Feed removal requires actual connected relay");
 chapter_walk(live,-36.5f,8);chapter_walk(live,-41,8);chapter_walk(live,-41,6);chapter_walk(live,-41,1.9f);chapter_walk(live,-39.5f,1.9f);chapter_walk(live,-39.5f,-5.2f);chapter_walk(live,-42,-5.2f);
 require(chapter_press(live,chapter_target(live,relay),VK_DELETE),"Actual Delete relay failed: "+live.notice);require(!chapter_flag(chapter_record(*live.owner->snapshot(),relay),"alive"),"Dismantled relay UUID was not tombstoned");
 require(chapter_flag(chapter_record(*live.owner->snapshot(),ids.progress),"pencil_visited")&&has_status(live.window,L"relay feed is offline"),
  "Actual relay-loss HUD must explain the offline feed even after reaching Pencil Room");
 chapter_hint_capture(live,L".offline-feed.hud.bmp");
 chapter_walk(live,-35.5f,-5.2f);require(chapter_press_isolation(live),"Actual post-Pencil fault reactivation failed: "+live.notice);
 for(unsigned n=0;n<240&&live.clock.sample(*live.owner->snapshot()).phase!=FirstBootArcPhase::arc;++n) require(live.frame(1.0/60,n%16==0),"Post-Pencil warning frame closed");
 require(live.clock.sample(*live.owner->snapshot()).phase==FirstBootArcPhase::arc&&!chapter_flag(chapter_record(*live.owner->snapshot(),ids.fault),"isolated")&&has_status(live.window,L"Watch the arc")&&has_status(live.window,L"isolate"),
  "Actual nearby arc HUD must prioritize danger over completed Pencil Room progress");
 chapter_hint_capture(live,L".nearby-arc.hud.bmp");
 chapter_walk(live,-39.5f,-5.2f);chapter_walk(live,-39.5f,1.9f);chapter_walk(live,-41,1.9f);
 require(chapter_press(live,chapter_target(live,ids.service_door))&&chapter_press(live,chapter_target(live,ids.service_door)),"Unpowered latched door did not close/reopen");chapter_walk(live,-41,6);
 require(chapter_flag(chapter_record(*live.owner->snapshot(),ids.service_door),"unlocked")&&has_status(live.window,L"relay feed is offline"),"Supply removal erased the secured door latch or hid the offline feed after returning to shelter");live.proof_feed_loss=true;
}
// Diagnostic-only traversal probes. These drive the ordinary controller/actions;
// they never synthesize a completion outcome or replace an installed save.
void chapter_fall_return(ChapterLive& live) {
 const auto ids=live.ids();const auto& progress=chapter_record(*live.owner->snapshot(),ids.progress);
 const auto door_id=chapter_text(progress,"first_route")=="bypass"?ids.service_door:ids.main_door;
 const auto board=chapter_board(live);const auto x=static_cast<float>(chapter_number(chapter_record(*live.owner->snapshot(),door_id),"x"))-board.x;
 chapter_walk(live,-37,8);chapter_walk(live,x,8);chapter_walk(live,x,1.9f);chapter_walk(live,-37,1.9f);chapter_walk(live,-37,-25);
 float half_z=0;for(const auto& record:live.owner->snapshot()->components)if(record.type_id=="firstboot.Node"&&chapter_number(record,"firstboot.kind")==1)half_z=static_cast<float>(chapter_number(record,"half_z"));
 require(half_z>25,"Fall probe requires an actual board edge beyond its approach");
 const auto revision=live.owner->snapshot()->revision;const auto expected=live.safe_return(*live.owner->snapshot());
 bool fell=false,recovered=false;SendMessageW(static_cast<HWND>(live.window.native_handle()),WM_KEYDOWN,'W',0);
 for(unsigned tick=0;tick<2400;++tick){
  aim(live.player,{board.x-37,live.player.eye_anchor().y,board.z-half_z-12});
  require(live.frame(1.0/60,tick%16==0),"Fall traversal frame closed");
  fell=fell||live.player.state().feet.y<board.y-1;
  if(live.notice=="Returned to a supported clear position after the fall."){recovered=true;break;}
 }
 SendMessageW(static_cast<HWND>(live.window.native_handle()),WM_KEYUP,'W',0);
 require(fell&&recovered,"Actual walk off the board did not fall and recover");
 for(unsigned tick=0;tick<120&&!live.player.state().grounded;++tick)require(live.frame(1.0/60,tick%16==0),"Fall settling frame closed");
 const auto feet=live.player.state().feet;
 require(live.player.state().grounded&&std::hypot(feet.x-expected.x,feet.z-expected.z)<.3f&&std::abs(feet.y-expected.y)<.3f,"Fall did not return to a supported safe anchor");
 require(live.owner->snapshot()->revision==revision,"Fall fabricated a durable gameplay outcome");
 live.proof_fall=true;
}
void chapter_rebuild_relay(ChapterLive& live) {
 const auto ids=live.ids();const auto before=live.owner->snapshot();const auto& fault=chapter_record(*before,ids.fault);
 require(chapter_text(chapter_record(*before,ids.progress),"first_route")=="bypass","Rebuild probe requires earned bypass progression");
 // Dismantling preserves the old feed binding until an explicit disconnect.
 // Find its tombstone and exercise the same two E actions available to BS.
 const auto socket=chapter_point(fault,"socket_");std::string old_relay;
 for(const auto& node:before->components)if(node.type_id=="firstboot.Node"&&chapter_number(node,"firstboot.kind")==6&&!chapter_flag(node,"alive")&&std::hypot(chapter_number(node,"x")-socket.x,chapter_number(node,"z")-socket.z)<.1)old_relay=node.entity_id;
 require(!old_relay.empty(),"Rebuild probe requires a retained dismantled relay");
 chapter_walk(live,-37,8);chapter_walk(live,-41,8);chapter_walk(live,-41,1.9f);chapter_walk(live,-39.5f,1.9f);chapter_walk(live,-39.5f,-5.2f);chapter_walk(live,-35.5f,-5.2f);
 if(!chapter_flag(chapter_record(*live.owner->snapshot(),ids.fault),"isolated"))require(chapter_press_isolation(live),"Rebuild isolation failed");
 chapter_walk(live,-42,-5.2f);require(chapter_press(live,{socket.x,socket.y+1,socket.z},'B'),"Actual replacement relay build failed: "+live.notice);
 std::string replacement;
 for(const auto& node:live.owner->snapshot()->components)if(node.type_id=="firstboot.Node"&&chapter_number(node,"firstboot.kind")==6&&chapter_flag(node,"alive")&&std::hypot(chapter_number(node,"x")-socket.x,chapter_number(node,"z")-socket.z)<.1)replacement=node.entity_id;
 require(!replacement.empty()&&replacement!=old_relay&&!chapter_flag(chapter_record(*live.owner->snapshot(),old_relay),"alive"),"Rebuild reused or resurrected a tombstoned relay identity");
 if(chapter_flag(chapter_record(*live.owner->snapshot(),ids.fault),"bypass_connected")){
  require(chapter_press(live,chapter_target(live,replacement)),"Actual old-feed disconnect failed: "+live.notice);
  require(!chapter_flag(chapter_record(*live.owner->snapshot(),ids.fault),"bypass_connected"),"Old feed remained connected after explicit E disconnect");
 }
 require(chapter_press(live,chapter_target(live,replacement)),"Actual replacement relay feed failed: "+live.notice);
 require(chapter_flag(chapter_record(*live.owner->snapshot(),ids.fault),"bypass_connected")&&chapter_text(chapter_record(*live.owner->snapshot(),ids.fault),"bypass_relay")==replacement,"Replacement E did not connect the new relay identity");
 require(live.content!=nullptr,"Replacement relay probe requires typed content");
 const auto binding=first_boot_content_workshop_binding(live.content->definition());
 if(binding){
  require(chapter_text(chapter_record(*live.owner->snapshot(),binding->fixtures[4]),"tested_signature")!=opening_workshop_signature(first_boot_content_workshop_circuit(*live.owner->snapshot(),*live.content)),"Replacement relay reused the old load-test signature");
  workshop_tour::station(live,*binding,3);
  require(chapter_text(chapter_record(*live.owner->snapshot(),binding->fixtures[4]),"tested_signature")==opening_workshop_signature(first_boot_content_workshop_circuit(*live.owner->snapshot(),*live.content)),"Replacement load test did not record the current relay identity");
 }
 chapter_walk(live,-39.5f,-5.2f);chapter_walk(live,-39.5f,1.9f);chapter_walk(live,-41,1.9f);chapter_walk(live,-41,6);
 if(binding)workshop_tour::station(live,*binding,4,0); // Permanent claim is idempotent.
 require(first_boot_content_supply(*live.owner->snapshot(),*live.content).bypass,"Retested replacement relay did not restore actual circuit power");
 require(chapter_flag(chapter_record(*live.owner->snapshot(),ids.service_door),"unlocked")&&chapter_flag(chapter_record(*live.owner->snapshot(),ids.progress),"pencil_visited")&&!has_status(live.window,L"relay feed is offline"),"Rebuild lost claimed progression or retained a stale offline hint");
 live.proof_rebuild=true;
}
void chapter_hazard(ChapterLive& live,const std::shared_ptr<ChapterControl>& control) {
 const auto ids=live.ids();const auto initial=live.owner->snapshot()->revision;const auto tick=live.clock.tick();
 key(live.window,VK_F2);require(live.frame(0)&&live.player.inspection_mode(),"Actual F2 inspection failed");const auto paused_tick=live.clock.tick();
 require(live.frame(20)&&live.clock.tick()==paused_tick&&live.owner->snapshot()->revision==initial,"Inspection advanced hazard time or authored progress");
 SendMessageW(static_cast<HWND>(live.window.native_handle()),WM_ACTIVATEAPP,FALSE,0);require(live.frame(20)&&live.clock.tick()==paused_tick,"Focus loss advanced chapter time");SendMessageW(static_cast<HWND>(live.window.native_handle()),WM_ACTIVATEAPP,TRUE,0);
 key(live.window,VK_F2);require(live.frame(0)&&!live.player.inspection_mode()&&live.clock.tick()==tick,"Return from inspection caught up paused hazard time");live.proof_pause=true;
 auto until_arc=[&](std::uint64_t minimum_cycle) { for(unsigned n=0;n<600;++n) { const auto sample=live.clock.sample(*live.owner->snapshot());if(sample.phase==FirstBootArcPhase::arc&&sample.cycle>=minimum_cycle) return;require(live.frame(1.0/60,n%16==0),"Arc clock frame closed"); }throw std::runtime_error("Actual active clock did not reach its arc window"); };
 until_arc(0);const auto board=chapter_board(live);control->hold_next=true;
 require(chapter_press(live,{board.x+30,board.y+1,board.z-20},'B',false),"Hazard backpressure fixture B failed: "+live.notice);control->gate.await();
 const auto nodes_before=chapter_nodes(*live.owner->snapshot()).components.size();const auto& fault=chapter_record(*live.owner->snapshot(),ids.fault);
 const Vec3 contact{static_cast<float>(chapter_number(fault,"x")+1.5),board.y+.2f,static_cast<float>(chapter_number(fault,"z"))};live.player.reset(contact);live.observed_region=live.region(*live.owner->snapshot(),contact);live.entry_previous.reset();
 key(live.window,'B');require(live.frame(0)&&live.critical&&live.critical->recovery&&live.player.state().feet==contact,"Backpressure lost physical recovery intent or teleported before publication");
 const auto stale=*live.critical;control->gate.release();chapter_drain(live);
 require(std::get<std::int64_t>(chapter_record(*live.owner->snapshot(),ids.progress).fields.at("recoveries"))==1&&chapter_nodes(*live.owner->snapshot()).components.size()==nodes_before,"Published recovery did not occur once or stale B input built at return");live.proof_backpressure=true;
 const auto first_head=live.owner->snapshot()->revision;live.player.reset(contact);live.observed_region="jenison";require(live.frame(0)&&live.owner->snapshot()->revision==first_head,"Same arc cycle produced a duplicate recovery");live.player.reset(live.safe_return(*live.owner->snapshot()));live.observed_region="jenison";
 until_arc(1);live.player.reset(contact);live.observed_region="jenison";key(live.window,'B');require(live.frame(0),"Direct arc recovery frame closed");chapter_drain(live);
 require(live.recovered_this_frame||std::get<std::int64_t>(chapter_record(*live.owner->snapshot(),ids.progress).fields.at("recoveries"))==2,"Second actual arc cycle failed recovery");
 require(chapter_nodes(*live.owner->snapshot()).components.size()==nodes_before,"Recovery frame executed the old B press at its new return point");live.proof_consumed=true;
 chapter_walk(live,-37,-25);chapter_walk(live,-37,-5.2f);chapter_walk(live,-35.5f,-5.2f);
 require(chapter_press_isolation(live)&&chapter_press_isolation(live),"Actual fault reactivation failed");
 const auto new_sample=live.clock.sample(*live.owner->snapshot());require(new_sample.activation_id!=stale.actor.hazard.activation_id&&new_sample.phase==FirstBootArcPhase::telegraph,"Reactivation did not begin a new full warning epoch");
 const auto head=live.owner->snapshot()->revision;const auto feet=live.player.state().feet;live.critical=stale;
 require(live.frame(0)&&!live.critical&&live.owner->snapshot()->revision==head&&live.player.state().feet==feet,"Old retained contact survived a newer activation");live.proof_stale=true;live.proof_hazard=true;
}
void chapter_remote_nodes(ChapterLive& live) {
 const auto board=chapter_board(live);const auto before=chapter_nodes(*live.owner->snapshot()).components;std::set<std::string> known;for(const auto& node:before) known.insert(node.entity_id);
 require(chapter_press(live,{board.x-37,board.y+1,board.z-21},'B'),"Native remote-input fixture B failed: "+live.notice);std::string relay;
 for(const auto& node:chapter_nodes(*live.owner->snapshot()).components) if(!known.contains(node.entity_id)) relay=node.entity_id;
 require(!relay.empty(),"Remote-input fixture did not build a real relay");const auto revision=live.owner->snapshot()->revision;
 require(!chapter_press(live,chapter_target(live,relay))&&live.last_target==relay&&live.notice.find("within reach")!=std::string::npos,"Remote E did not enforce actual body reach");
 require(!chapter_press(live,chapter_target(live,relay),VK_DELETE)&&live.last_target==relay&&live.owner->snapshot()->revision==revision&&chapter_flag(chapter_record(*live.owner->snapshot(),relay),"alive"),"Remote Delete changed a real distant relay or terminated the game");live.proof_remote=true;
}
void chapter_reload_failure(ChapterLive& live) {
 require(!live.config.proof_gate.empty(),"Reload-failure verification requires --proof-gate PATH beside the explicit DB");auto ready=live.config.proof_gate;ready+=L".ready";auto go=live.config.proof_gate;go+=L".go";
 require(!std::filesystem::exists(ready)&&!std::filesystem::exists(go),"Reload-failure gate must be fresh");{ std::ofstream file(ready);file<<"ready for external writer";require(file.good(),"Cannot publish reload-failure readiness"); }
 const auto until=Clock::now()+std::chrono::seconds(15);
 while(!std::filesystem::exists(go)) { require(Clock::now()<until,"External reload-failure writer did not release its gate");live.window.poll();std::this_thread::sleep_for(std::chrono::milliseconds(5)); }
 const auto* owner=live.owner.get();const auto snapshot=live.owner->snapshot();const auto feet=live.player.state().feet;const auto camera=live.player.camera().position;
 key(live.window,VK_F9);require(live.frame(0)&&live.owner.get()==owner&&live.owner->snapshot()==snapshot&&live.player.state().feet==feet&&live.player.camera().position==camera&&
  live.notice.find("Reload blocked; current chapter retained")!=std::string::npos,"Actual F9 storage failure did not retain playable owner, scene and body");live.proof_reload_failure=true;
}
void chapter_held_contact(ChapterLive& live,const std::shared_ptr<ChapterControl>& control,bool closing) {
 const auto ids=live.ids();const auto initial=live.owner->state();
 for(unsigned n=0;n<600&&live.clock.sample(*live.owner->snapshot()).phase!=FirstBootArcPhase::arc;++n)
  require(live.frame(1.0/60,n%16==0),"Held-contact clock frame closed");
 require(live.clock.sample(*live.owner->snapshot()).phase==FirstBootArcPhase::arc,"Held-contact fixture missed the actual arc clock");
 const auto board=chapter_board(live);control->hold_next=true;control->fail_next=!closing;
 require(chapter_press(live,{board.x+30,board.y+1,board.z-20},'B',false),"Held-contact fixture could not build its real pending relay");control->gate.await();
 const auto& fault=chapter_record(*live.owner->snapshot(),ids.fault);const Vec3 contact{static_cast<float>(chapter_number(fault,"x")+1.5),board.y+.2f,static_cast<float>(chapter_number(fault,"z"))};
 live.player.reset(contact);live.observed_region="jenison";live.entry_previous.reset();require(live.frame(0)&&live.critical&&live.critical->recovery,"Actual arc contact did not survive full worker credit");
 const auto tick=live.clock.tick();const auto deadline=Clock::now()+std::chrono::seconds(15);
 if(closing) {
  SendMessageW(static_cast<HWND>(live.window.native_handle()),WM_CLOSE,0,0);
  require(live.frame(20)&&live.exit_requested&&live.critical&&live.clock.tick()==tick&&live.player.state().feet==contact&&
   IsWindow(static_cast<HWND>(live.window.native_handle())),"WM_CLOSE discarded held contact, moved its body/clock or destroyed its live HWND");
  control->gate.release();
  while(live.frame(0)) { require(Clock::now()<deadline,"Chapter close did not drain held contact and real save completion");std::this_thread::sleep_for(std::chrono::milliseconds(1)); }
  require(!live.critical&&live.owner->state().saved&&IsWindow(static_cast<HWND>(live.window.native_handle())),"Close returned before contact publication/durable completion");live.proof_close_drained=true;
 } else {
  control->gate.release();while(!live.owner->state().failed) { require(live.frame(0)&&Clock::now()<deadline,"Actual one-shot save failure did not reach its live owner");std::this_thread::sleep_for(std::chrono::milliseconds(1)); }
  require(live.frame(20)&&live.critical&&live.clock.tick()==tick&&live.player.state().feet==contact&&!live.owner->state().saved,
   "Failed save discarded critical evidence, advanced time or pretended to save");
  key(live.window,VK_F5);require(live.frame(0),"Actual F5 retry closed the chapter");
  while(live.critical||!live.owner->state().saved) { require(live.frame(0)&&Clock::now()<deadline,"Actual F5 did not retry pending save then publish held contact");std::this_thread::sleep_for(std::chrono::milliseconds(1)); }
  require(!live.owner->state().failed&&live.player.state().feet!=contact&&has_status(live.window,L"SAVED"),"Live F5 retry did not restore a truthful saved HUD and safe body");live.proof_live_retry=true;
 }
 require(live.owner->state().durable_revision==initial.durable_revision+2&&std::get<std::int64_t>(chapter_record(*live.owner->snapshot(),ids.progress).fields.at("recoveries"))==1,
  "Held-contact retry/close lost a real batch or duplicated recovery");
}
void chapter_companion_controls(ChapterLive& live,const std::shared_ptr<ChapterControl>& control){
 require(live.companion!=nullptr,"Companion controls require an authored Adam binding");const auto revision=live.owner->snapshot()->revision;const auto replacements=live.renderer.stats().scene_replacements;
 require(live.companion->state().saved.intent==GuideIntent::follow,"Control proof starts with authored Follow intent");control->hold_next=true;
 key(live.window,VK_F7);require(live.frame(0)&&live.owner->snapshot()->revision==revision+1&&live.companion->state().saved.intent==GuideIntent::wait,"Actual F7 did not stage/admit/activate Wait: "+live.notice);control->gate.await();
 const auto waiting=live.companion->state();require(live.owner->state().pending_batches==1&&!live.owner->state().saved,"Wait proof requires a real held save credit");
 key(live.window,VK_F6);require(live.frame(0)&&live.owner->snapshot()->revision==revision+1&&live.companion->state().saved.intent==GuideIntent::wait&&live.companion->state().guide->character.feet==waiting.guide->character.feet,"Rejected F6 save admission changed Adam or the visible head");
 control->gate.release();chapter_drain(live);key(live.window,VK_F6);require(live.frame(0)&&live.companion->state().saved.intent==GuideIntent::follow,"Actual F6 did not restore Follow after credit drained: "+live.notice);chapter_drain(live);
 const auto followed=live.owner->snapshot()->revision;PostMessageW(static_cast<HWND>(live.window.native_handle()),WM_ACTIVATEAPP,FALSE,0);key(live.window,VK_F7);require(live.frame(1)&&live.owner->snapshot()->revision==followed,"Inactive native input must not persist Wait");PostMessageW(static_cast<HWND>(live.window.native_handle()),WM_ACTIVATEAPP,TRUE,0);require(live.frame(0),"Reactivate companion proof");
 key(live.window,VK_F2);require(live.frame(0)&&live.player.inspection_mode(),"Enter actual inspection mode");key(live.window,VK_F7);require(live.frame(0)&&live.owner->snapshot()->revision==followed,"Inspection native input must not persist Wait");key(live.window,VK_F2);require(live.frame(0)&&!live.player.inspection_mode(),"Return to grounded BS controls");chapter_settle(live);
 key(live.window,VK_F8);require(live.frame(0)&&live.companion->state().saved.intent==GuideIntent::follow&&!live.companion->state().recall_required,"Actual F8 failed explicit validated Recall: "+live.notice);chapter_drain(live);
 key(live.window,VK_F7);require(live.frame(0)&&live.companion->state().saved.intent==GuideIntent::wait,"Wait after explicit Recall");chapter_drain(live);
 require(live.renderer.stats().scene_replacements==replacements,"Companion movement/choices must not rebuild static scenery");const auto saved=live.companion->state().saved;const auto head=live.owner->snapshot()->revision;
 key(live.window,VK_F9);require(live.frame(0)&&live.reloads==1&&live.companion->state().saved.intent==saved.intent&&live.companion->state().saved.waiting_anchor==saved.waiting_anchor&&live.owner->snapshot()->revision==head,"Actual F9 lost companion intent/anchor or invented history");chapter_settle(live);
 key(live.window,VK_F7);require(live.frame(0)&&live.owner->snapshot()->revision==head,"Repeated F7 invented another outcome");require(head==revision+4,"Only accepted deliberate choices may enter history");live.proof_companion_controls=true;
}
#include "memory_proof.inl"
#include "opening_native_proof.inl"
#include "opening_tour_runtime.inl"
void chapter_prove(ChapterLive& live,const std::shared_ptr<ChapterControl>& control) {
 if(live.config.offscreen_tour_proof){
  if(live.config.offscreen_camera=="third-person"){live.proof_key('V');require(live.tour_frame(0),"Offscreen camera proof unexpectedly closed");}
  require(live.player.third_person()==(live.config.offscreen_camera=="third-person"),"Actual controlled V did not select the requested proof camera");
 }
 chapter_settle(live);const auto& step=live.config.step;
 if(step==L"stop-drain") {
  require(live.content!=nullptr,"Managed Stop proof requires typed content");const auto initial=live.owner->state();const auto board=chapter_board(live);control->hold_next=true;
  require(chapter_press(live,{board.x+30,board.y+1,board.z-20},'B',false),"Managed Stop proof could not publish actual B relay: "+live.notice);control->gate.await();
  require(!live.owner->state().saved&&live.owner->state().pending_batches==1,"Managed Stop proof requires a genuinely pending held commit");
  {std::ofstream marker(live.config.stop_file);marker<<"proof controller requests graceful stop\n";require(marker.good(),"Cannot create actual managed Stop marker");}
  const auto feet=live.player.state().feet;const auto tick=live.clock.tick();
  for(unsigned n=0;n<3;++n)require(live.frame(20)&&live.exit_requested&&!live.owner->state().saved&&live.player.state().feet==feet&&live.clock.tick()==tick&&IsWindow(static_cast<HWND>(live.window.native_handle())),"Marker Stop exited, advanced simulation or discarded the held async save");
  control->gate.release();const auto deadline=Clock::now()+std::chrono::seconds(15);
  while(live.frame(0)){require(Clock::now()<deadline,"Marker Stop did not drain its released commit");std::this_thread::sleep_for(std::chrono::milliseconds(1));}
  require(live.owner->state().saved&&live.owner->state().durable_revision==initial.durable_revision+1&&live.owner->state().pending_batches==0,"Marker Stop returned before exact pending save became durable");live.proof_close_drained=true;
 } else if(step==L"companion-controls") chapter_companion_controls(live,control);
 else if(step==L"memory-controls") chapter_memory_controls(live);
 else if(step==L"opening-controls") chapter_opening_controls(live);
 else if(step==L"opening-tour") chapter_opening_tour(live);
 else if(step==L"content-route") {
  require(live.content!=nullptr,"Typed content route requires an immutable definition");chapter_bypass_route(live);const auto ids=live.ids();const auto board=chapter_board(live);
  const auto door=chapter_point(chapter_record(*live.owner->snapshot(),ids.main_door));
  chapter_walk(live,-41,1.9f);chapter_walk(live,-39.5f,1.9f);chapter_walk(live,-39.5f,-5.2f);chapter_walk(live,-33,-5.2f);
  require(chapter_press(live,chapter_target(live,ids.fault,"Downstream power fault")),"Actual typed fault repair failed: "+live.notice);
  chapter_walk(live,-35.5f,-5.2f);require(chapter_press_isolation(live),"Actual typed feed reconnection failed: "+live.notice);live.proof_repair=true;
  chapter_walk(live,-37,-5.2f);chapter_walk(live,-37,1.9f);chapter_walk(live,door.x-board.x,1.9f);
  chapter_walk(live,door.x-board.x,6,100,false);require(live.player.state().feet.z<board.z+3.6f,"Authored moved closed door did not stop actual capsule");chapter_walk(live,door.x-board.x,1.9f);
  require(chapter_press(live,chapter_target(live,ids.main_door)),"Actual E authored moved main door failed: "+live.notice);
  chapter_walk(live,door.x-board.x,6);chapter_walk(live,door.x-board.x,1.9f);chapter_walk(live,door.x-board.x,6);
  const auto desk=std::find_if(live.content->definition().fixtures.begin(),live.content->definition().fixtures.end(),[](const auto& f){return f.object.name=="Pencil Room writing desk";});require(desk!=live.content->definition().fixtures.end(),"Typed proof requires authored desk fixture");
  const auto& object=desk->object;
  chapter_walk(live,door.x-board.x,8);chapter_walk(live,-37,8);chapter_walk(live,-37,object.center.z-board.z);
  chapter_walk(live,object.center.x-board.x,object.center.z-board.z,100,false);require(live.player.state().feet.x>object.center.x+object.half_extent.x,"Moved authored desk did not participate in actual collision");
  chapter_walk(live,-37,object.center.z-board.z);chapter_walk(live,-37,8);
  const auto npc=chapter_point(chapter_record(*live.owner->snapshot(),ids.npc_quest));chapter_walk(live,door.x-board.x,8);chapter_walk(live,npc.x-board.x,8);chapter_walk(live,npc.x-board.x,npc.z+2.5f-board.z);chapter_choice(live,false);live.proof_decline=true;
 } else if(step==L"repair-route") chapter_repair_route(live);
 else if(step==L"bypass-route") chapter_bypass_route(live);
 else if(step==L"door-cycle") chapter_door_cycle(live);
 else if(step==L"help"||step==L"decline") chapter_caretaker(live,step==L"help");
 else if(step==L"depart-return") chapter_return(live);
 else if(step==L"feed-loss") chapter_feed_loss(live);
 else if(step==L"fall-return") chapter_fall_return(live);
 else if(step==L"relay-rebuild") chapter_rebuild_relay(live);
 else if(step==L"hazard") chapter_hazard(live,control);
 else if(step==L"remote-nodes") chapter_remote_nodes(live);
 else if(step==L"translated-walk") {
  const auto board=chapter_board(live);const auto revision=live.owner->snapshot()->revision;const auto ticks=live.player.state().ticks;
  require(board.y<-20,"Translated proof did not import its negative-height board");chapter_walk(live,-37,-25);chapter_walk(live,-37,-12);chapter_walk(live,-37,-25);
  require(live.player.state().feet.y<-20&&live.player.state().feet.y>=board.y-.2f&&live.player.state().ticks>ticks+100&&live.owner->snapshot()->revision==revision,"Supported translated board repeatedly reset or invented progress");live.proof_translated=true;
 }
 else if(step==L"reload-failure") chapter_reload_failure(live);
 else if(step==L"fail-retry"||step==L"close-drain") chapter_held_contact(live,control,step==L"close-drain");
 else if(step==L"reload") { key(live.window,VK_F9);require(live.frame(0)&&live.reloads==1,"Chapter actual F9 reload failed"); }
 else require(step==L"seed"||step==L"inspect","Chapter proof step is not implemented");
 if(live.companion&&(step==L"repair-route"||step==L"bypass-route")){
  for(unsigned n=0;n<180;++n)require(live.frame(1.0/60,n%30==0),"Companion route catch-up frame closed");const auto guide=live.companion->state();require(guide.guide&&!guide.recall_required&&guide.saved.intent==GuideIntent::follow,"Adam did not retain independent Follow on the route");const auto feet=guide.guide->character.feet,bs=live.player.state().feet;
  require(live.region(*live.owner->snapshot(),feet)==live.region(*live.owner->snapshot(),bs)&&std::hypot(feet.x-bs.x,feet.z-bs.z)<3.5f,"Adam failed to follow the actual gated route without Recall");live.proof_companion_route=true;
 }
 if(!live.proof_close_drained) { chapter_drain(live);require(live.frame(0),"Chapter proof final HUD frame closed"); }
 chapter_report(live);require(live.owner->close().ok,"Chapter proof did not close cleanly");
}
#include "performance_runtime.inl"
int run_chapter(const Options& o) {
 const auto content=o.managed()?load_content(o):nullptr;
 const auto visuals=content?std::make_shared<const PlacedAssetVisuals>(*content,o.asset_root):nullptr;
 auto schemas=first_boot_chapter_schemas();const auto scope=content?initialize_content(o,*content,&schemas):initialize_chapter(o);
 auto archive=std::make_unique<GameplayStore>(o.database,scope,schemas);
 const auto control=std::make_shared<ChapterControl>();GameplayWorkerLimits limits;if(o.step==L"hazard"||o.step==L"fail-retry"||o.step==L"close-drain"||o.step==L"companion-controls") limits.items=1;
 GameplayStoreObserver save_observer=[control](GameplayStoreStage stage) {
  if(stage==GameplayStoreStage::before_commit) { if(control->hold_next.exchange(false)) control->gate.arrive();if(control->fail_next.exchange(false)) throw std::runtime_error("One-shot chapter save failure; held contact must survive F5 retry"); }
 };
 auto owner=std::make_unique<GameplayWorld>(o.database,scope,schemas,limits,save_observer);
 auto scene=content?first_boot_content_scene(*owner->snapshot(),*content):first_boot_chapter_scene(*owner->snapshot());auto player=content?first_boot_content_player(*owner->snapshot(),*content):first_boot_chapter_player(*owner->snapshot());
 SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);
 auto validation=RenderValidationMode::enable_if_available;
#ifdef NDEBUG
 // Normal Release gameplay and its passive profiler share the same policy.
 // Proofs and walkthrough recordings retain development validation.
 if(!o.proof()&&!o.recording()&&!o.walkthrough) validation=RenderValidationMode::do_not_enable;
#endif
 NativeWindow window(o.window_width(),o.window_height(),L"AI-BS First Boot chapter | Jenison to the Pencil Room",!o.offscreen_tour_proof&&(!o.proof()||o.step==L"opening-tour"));Dx12Renderer renderer(window,{},shaders(),validation);
 const TexturedScene empty_textures;
 {
 const auto base_mesh=visuals?visuals->mesh(scene):mesh_from_snapshot(scene);
 const auto lights=content?first_boot_content_lighting(*owner->snapshot(),*content):SceneLighting{};
 if(content&&(!content->definition().memories.empty()||!OpeningInspectionCatalog(content->definition()).entries().empty())){
  constexpr std::size_t ui_and_markers=2u*1024u*1024u+512u*1024u;
  require(visuals&&visuals->resident_bytes()<=memory_playback_maximum_resident_bytes-ui_and_markers,"Memory startup CPU dependencies exceed joint128MiB profile");
  const auto remaining=memory_scene_gpu_remainder(ui_and_markers+visuals->resident_bytes(),base_mesh);
  renderer.set_scene_character_asset_bounded(base_mesh,visuals->textured(),lights,visuals->companion_model(),static_cast<std::uint64_t>(remaining));
 }else renderer.set_scene_character_asset(base_mesh,visuals?visuals->textured():empty_textures,lights,visuals?visuals->companion_model():nullptr);
 } // Release the composed startup CPU copy before the live owner/game loop.
 ChapterLive live(o,scope,std::move(archive),std::move(owner),std::move(scene),std::move(player),window,renderer,content,visuals);
 live.previous_workshop_registry=live.workshop_hud&&std::none_of(schemas.begin(),schemas.end(),[](const auto& s){return s.type_id==opening_workshop_assembly_component_type;});
 live.registered_schemas=std::move(schemas);live.save_limits=limits;live.save_observer=std::move(save_observer);
 if(o.proof()) {
  try { chapter_prove(live,control); } catch(...) { control->gate.release();throw; }
 } else {
  require(live.frame(0),"Managed chapter closed before its first frame");live.lifecycle("aibs.play.ready");
  std::optional<ChapterPerformanceOutcome> performance;
  if(o.performance())performance=measure_chapter_window(live);
  else if(o.walkthrough){if(o.recording())live.recording=std::make_unique<ChapterRecorder>(o,window);chapter_settle(live);chapter_opening_tour(live);chapter_drain(live);if(live.recording)live.recording->finish();chapter_report(live);live.exit_requested=true;while(live.tour_frame(0))std::this_thread::sleep_for(std::chrono::milliseconds(1));}
  else{auto previous=Clock::now();for(;;) { const auto now=Clock::now();const auto elapsed=std::chrono::duration<double>(now-previous).count();previous=now;if(!live.frame(elapsed)) break;if(window.minimized()||live.exit_requested) std::this_thread::sleep_for(std::chrono::milliseconds(10)); }}
  renderer.wait_idle();const auto nonbackground=o.capture.empty()?0:renderer.capture(o.capture);
  if(performance){
   // A failed measurement/report is not a failed save. Acknowledge STOPPED
   // only after the actual owner close succeeded, keeping the failure exit.
   try{write_chapter_performance(live,*performance,nonbackground);}
   catch(...){if(live.saved_close_complete)live.lifecycle("aibs.play.stopped");throw;}
   if(live.saved_close_complete)live.lifecycle("aibs.play.stopped");
   require(performance->measured&&performance->error.empty(),"Performance capture did not produce valid measured statistics");
  }else live.lifecycle("aibs.play.stopped");
 }
 return 0;
}
}

int run_durable_world(int argc,wchar_t** argv) {
 bool proof=false,managed=false;std::shared_ptr<Gate> gate=std::make_shared<Gate>();
 for(int i=1;i<argc;++i){const std::wstring flag(argv[i]);if(flag==L"--durable-step")proof=true;if(flag==L"--content-definition"||flag==L"--persistent-play")managed=true;}
 try {
  const auto o=options(argc,argv);proof=o.proof();
  PersistentSlotLock persistent_owner(o);
  if(!o.database.parent_path().empty()) std::filesystem::create_directories(o.database.parent_path());
  if(o.chapter) return run_chapter(o);
  const auto scope=initialize(o);auto archive=std::make_unique<GameplayStore>(o.database,scope,durable_first_boot_schemas());
  auto owner=std::make_unique<GameplayWorld>(o.database,scope,durable_first_boot_schemas(),GameplayWorkerLimits{},observer(o,gate));
  auto snapshot=durable_first_boot_scene(*owner->snapshot());auto bs=durable_first_boot_player(*owner->snapshot());
  SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);
  NativeWindow window(proof?960u:1440u,proof?640u:900u,L"AI-BS First Boot | Durable world | E repair | B build | Delete dismantle | F5 retry | F9 reload",!proof);
  Dx12Renderer renderer(window,mesh_from_snapshot(snapshot),shaders());
  LiveWorld live(o,scope,std::move(archive),std::move(owner),std::move(snapshot),std::move(bs),window,renderer);
  try {
   if(proof) prove(live,gate);
   else {
   auto previous=Clock::now();
   while(true) {
    const auto now=Clock::now();const double elapsed=std::chrono::duration<double>(now-previous).count();previous=now;
    if(!live.frame(elapsed)) break;
    if(window.minimized()||live.exit_requested) std::this_thread::sleep_for(std::chrono::milliseconds(10));
   }
    renderer.wait_idle();if(!o.capture.empty()) renderer.capture(o.capture);
   }
  } catch(...) { gate->release();throw; }
  return 0;
 } catch(const std::exception& error) {
  gate->release();std::cerr<<"Native durable world failed: "<<error.what()<<'\n';
  if(!proof&&!managed) MessageBoxW(nullptr,wide(error.what()).c_str(),L"AI-BS durable world could not continue",MB_OK|MB_ICONERROR);
  return 1;
 }
}
