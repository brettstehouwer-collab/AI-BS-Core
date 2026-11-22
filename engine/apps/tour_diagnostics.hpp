#pragma once
// Private observational/proof support. No public SDK or player input policy changes.
#include <aibs/player.hpp>
#include <array>
#include <cmath>
#include <filesystem>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>

namespace tour_diagnostic {
inline bool ordinary_input_trace_allowed(bool managed,bool proof,bool walkthrough,bool recording,bool performance,bool controlled) noexcept {
 return managed&&!proof&&!walkthrough&&!recording&&!performance&&!controlled;
}
inline bool trace_enabled(bool ordinary,bool walkthrough,bool opening_tour) noexcept {
 return ordinary||walkthrough||opening_tour;
}
inline bool owned_child_focus(HWND owner,HWND focused) noexcept {
 if(!focused||focused==owner)return false;
 if(IsChild(owner,focused))return true;
 auto root=GetAncestor(focused,GA_ROOT);
 for(unsigned depth=0;root&&depth<8;++depth){if(root==owner)return true;root=GetWindow(root,GW_OWNER);}
 return false;
}
// This is explicitly controlled test input, never evidence of OS focus/input.
class Controls {
 bool forward_=false;
 aibs::WindowInput edges_;
public:
 void forward(bool held) noexcept { forward_=held; }
 void press(unsigned code) {
  if(code=='E')edges_.interact=true;
  else if(code=='B')edges_.build=true;
  else if(code=='V')edges_.cycle_camera=true;
  else throw std::invalid_argument("Offscreen tour admits only its declared E/B/V proof keys");
 }
 aibs::WindowInput take() noexcept {
  auto result=edges_;edges_={};result.forward=forward_?1.f:0.f;result.active=true;return result;
 }
};
struct Frame {
 aibs::WindowInput observed,effective;
 aibs::CharacterState before,after;
 aibs::Camera camera;
 double elapsed=0;
 std::uint64_t tick_before=0,tick_after=0,revision=0;
 bool controlled=false,minimized=false,reading=false,critical=false,closing=false;
 bool inspection=false,visible=false,foreground=false,third_person=false;
 bool ordinary=false,focus_game=false,focus_owned_child=false,saved=false,save_failed=false;
 std::uint64_t frame_index=0,visible_revision=0,durable_revision=0,durable_sequence=0,pending_batches=0;
};
// Ordinary traces sample actual frames; action/state edges are never rate-limited.
// Rendering may run much faster than physics. Sampling must not claim omitted
// frames were recorded or fabricate motion by combining different frames.
class Sampler {
 Frame previous_{};
 bool have_previous_=false;
 double elapsed_=0;
 std::uint64_t observed_=0,skipped_=0,retained_=0;
 static bool pulse(const aibs::WindowInput& i) noexcept {
  return i.interact||i.pointer_interact||i.build||i.dismantle||i.redo||i.undo||i.save||i.reload||i.jump
   ||i.cycle_camera||i.toggle_flight||i.companion_follow||i.companion_wait||i.companion_recall;
 }
 static bool held_changed(const aibs::WindowInput& a,const aibs::WindowInput& b) noexcept {
  return a.active!=b.active||a.forward!=b.forward||a.right!=b.right||a.up!=b.up||a.sprint!=b.sprint;
 }
 static bool state_changed(const Frame& a,const Frame& b) noexcept {
  return held_changed(a.observed,b.observed)||held_changed(a.effective,b.effective)
   ||a.controlled!=b.controlled||a.minimized!=b.minimized||a.reading!=b.reading||a.critical!=b.critical
   ||a.closing!=b.closing||a.inspection!=b.inspection||a.visible!=b.visible||a.foreground!=b.foreground
   ||a.third_person!=b.third_person||a.focus_game!=b.focus_game||a.focus_owned_child!=b.focus_owned_child
   ||a.revision!=b.revision||a.visible_revision!=b.visible_revision||a.durable_revision!=b.durable_revision
   ||a.durable_sequence!=b.durable_sequence||a.pending_batches!=b.pending_batches
   ||a.saved!=b.saved||a.save_failed!=b.save_failed||a.after.grounded!=b.after.grounded;
 }
public:
 bool retain(const Frame& f) noexcept {
  ++observed_;
  if(std::isfinite(f.elapsed)&&f.elapsed>0)elapsed_+=f.elapsed;
  const bool moving=f.effective.active&&!f.reading&&!f.critical&&!f.closing&&!f.minimized&&!f.inspection
   &&(f.effective.forward!=0||f.effective.right!=0||f.effective.up!=0);
  const bool keep=!have_previous_||pulse(f.observed)||pulse(f.effective)||state_changed(previous_,f)
   ||(elapsed_>=.1&&(!moving||f.after.ticks!=f.before.ticks));
  previous_=f;have_previous_=true;
  if(keep){++retained_;elapsed_=0;}else ++skipped_;
  return keep;
 }
 std::uint64_t observed()const noexcept{return observed_;}
 std::uint64_t skipped()const noexcept{return skipped_;}
 std::uint64_t retained()const noexcept{return retained_;}
};
inline std::string controls_json(const aibs::WindowInput& input) {
 std::ostringstream out;out<<std::setprecision(17)<<std::boolalpha;
 out<<"{\"active\":"<<input.active<<",\"forward\":"<<input.forward<<",\"right\":"<<input.right<<",\"up\":"<<input.up
  <<",\"yaw_delta\":"<<input.yaw_delta<<",\"pitch_delta\":"<<input.pitch_delta<<",\"sprint\":"<<input.sprint
  <<",\"interact\":"<<input.interact<<",\"pointer_interact\":"<<input.pointer_interact
  <<",\"pointer_x\":"<<input.pointer_x<<",\"pointer_y\":"<<input.pointer_y<<",\"build\":"<<input.build
  <<",\"dismantle\":"<<input.dismantle<<",\"help\":"<<input.redo<<",\"decline\":"<<input.undo
  <<",\"retry_save\":"<<input.save<<",\"reload\":"<<input.reload<<",\"jump\":"<<input.jump
  <<",\"cycle_camera\":"<<input.cycle_camera<<",\"toggle_inspection\":"<<input.toggle_flight
  <<",\"companion_follow\":"<<input.companion_follow<<",\"companion_wait\":"<<input.companion_wait
  <<",\"companion_recall\":"<<input.companion_recall<<"}";return out.str();
}
inline std::string json(const Frame& f) {
 std::ostringstream out;out<<std::setprecision(17)<<std::boolalpha;
 out<<"{\"kind\":\"frame\",\"input_source\":\""<<(f.controlled?"controlled-proof-keys":"native-window")
  <<"\",\"observed_active\":"<<f.observed.active<<",\"observed_forward\":"<<f.observed.forward
  <<",\"active\":"<<f.effective.active<<",\"forward\":"<<f.effective.forward
  <<",\"right\":"<<f.effective.right<<",\"elapsed\":"<<f.elapsed
  <<",\"minimized\":"<<f.minimized<<",\"reading\":"<<f.reading<<",\"critical\":"<<f.critical
  <<",\"closing\":"<<f.closing<<",\"inspection\":"<<f.inspection
  <<",\"window_visible\":"<<f.visible<<",\"foreground\":"<<f.foreground<<",\"third_person\":"<<f.third_person
  <<",\"revision\":"<<f.revision<<",\"clock_before\":"<<f.tick_before<<",\"clock_after\":"<<f.tick_after
  <<",\"physics_before\":"<<f.before.ticks<<",\"physics_after\":"<<f.after.ticks
  <<",\"feet_before\":["<<f.before.feet.x<<','<<f.before.feet.y<<','<<f.before.feet.z
  <<"],\"feet_after\":["<<f.after.feet.x<<','<<f.after.feet.y<<','<<f.after.feet.z
  <<"],\"velocity_after\":["<<f.after.velocity.x<<','<<f.after.velocity.y<<','<<f.after.velocity.z
  <<"],\"grounded\":"<<f.after.grounded<<",\"dropped_seconds\":"<<f.after.dropped_seconds
  <<",\"camera_yaw\":"<<f.camera.yaw<<",\"camera_pitch\":"<<f.camera.pitch;
 if(f.ordinary)out<<",\"trace_profile\":\"ordinary-owned-window-v1\",\"frame_index\":"<<f.frame_index
  <<",\"focus_game\":"<<f.focus_game<<",\"focus_owned_child\":"<<f.focus_owned_child
  <<",\"consumed_controls\":"<<controls_json(f.observed)
  <<",\"visible_revision\":"<<f.visible_revision<<",\"durable_revision\":"<<f.durable_revision
  <<",\"durable_sequence\":"<<f.durable_sequence<<",\"pending_batches\":"<<f.pending_batches
  <<",\"saved\":"<<f.saved<<",\"save_failed\":"<<f.save_failed;
 out<<"}";
 return out.str();
}
class Trace {
 HANDLE file_=INVALID_HANDLE_VALUE;
 std::array<std::string,32> recent_{};
 std::size_t cursor_=0,count_=0,records_=0,bytes_=0;
 bool observational_=false,incomplete_=false,ended_=false;
 Sampler sampler_;
 Frame pending_{};
 bool pending_frame_=false;
 std::uint64_t frame_records_=0;
 void incomplete(const char* code) noexcept {
  incomplete_=true;
  std::cerr<<"ORDINARY_INPUT_TRACE_INCOMPLETE {\"error_code\":\""<<code<<"\",\"complete\":false}\n";
  if(file_!=INVALID_HANDLE_VALUE){FlushFileBuffers(file_);CloseHandle(file_);file_=INVALID_HANDLE_VALUE;}
 }
 void write(const std::string& line) {
  if(file_==INVALID_HANDLE_VALUE)return;
  if(records_>=65536||line.size()>4096||bytes_>32u*1024u*1024u-line.size()-1){
   if(observational_){incomplete("trace_budget_exceeded");return;}
   throw std::runtime_error("Diagnostic input trace reached its retained 65536-record/32MiB bound");
  }
  const auto data=line+'\n';DWORD written=0;
  if(!WriteFile(file_,data.data(),static_cast<DWORD>(data.size()),&written,nullptr)||written!=data.size()){
   if(observational_){incomplete("trace_write_failed");return;}
   throw std::runtime_error("Cannot retain diagnostic input trace");
  }
  ++records_;bytes_+=data.size();
 }
public:
 explicit Trace(const std::filesystem::path& path={},bool observational=false):observational_(observational) {
  if(path.empty())return;
  file_=CreateFileW(path.c_str(),GENERIC_WRITE,FILE_SHARE_READ,nullptr,CREATE_NEW,FILE_ATTRIBUTE_NORMAL,nullptr);
  if(file_==INVALID_HANDLE_VALUE)throw std::runtime_error("Diagnostic trace must be a new writable owned file");
 }
 ~Trace(){if(observational_&&!ended_&&!incomplete_)incomplete("session_ended_without_stop_receipt");if(file_!=INVALID_HANDLE_VALUE){FlushFileBuffers(file_);CloseHandle(file_);}}
 Trace(const Trace&)=delete;Trace& operator=(const Trace&)=delete;
 void frame(const Frame& sample) {
  if(observational_&&incomplete_)return;
  if(observational_){
   pending_=sample;
   if(!sampler_.retain(sample)){pending_frame_=true;return;}
   pending_frame_=false;write(json(sample));if(!incomplete_)++frame_records_;return;
  }
  auto line=json(sample);write(line);if(observational_)return;
  recent_[cursor_]=std::move(line);cursor_=(cursor_+1)%recent_.size();count_=std::min(count_+1,recent_.size());
 }
 bool complete()const noexcept{return observational_&&ended_&&!incomplete_;}
 bool active()const noexcept{return file_!=INVALID_HANDLE_VALUE;}
 void ordinary_lifecycle(bool ready,bool saved,std::uint64_t revision,std::uint64_t sequence) {
  if(!observational_||incomplete_)return;
  if(!ready&&pending_frame_){write(json(pending_));pending_frame_=false;if(incomplete_)return;++frame_records_;}
  std::ostringstream out;out<<std::boolalpha<<"{\"kind\":\""<<(ready?"ordinary-play-ready":"ordinary-play-stopped")
   <<"\",\"trace_profile\":\"ordinary-owned-window-v1\",\"saved\":"<<saved
   <<",\"durable_revision\":"<<revision<<",\"durable_sequence\":"<<sequence
   <<",\"capture_policy\":\"sampled-10hz-plus-input-state-edges-v1\",\"nominal_sample_interval_seconds\":0.1"
   <<",\"observed_frames\":"<<sampler_.observed()<<",\"retained_frames\":"<<frame_records_
   <<",\"omitted_frames\":"<<(sampler_.observed()-frame_records_);
  if(!ready)out<<",\"stop_observed\":true";
  out<<"}";write(out.str());
  if(!ready&&!incomplete_){ended_=true;if(!FlushFileBuffers(file_))incomplete("trace_flush_failed");
   else std::cerr<<"ORDINARY_INPUT_TRACE_COMPLETE {\"complete\":true,\"completion_scope\":\"retained_capture_only\",\"records\":"<<records_<<",\"bytes\":"<<bytes_<<"}\n";}
 }
 void begin_walk(float x,float z) {
  std::ostringstream out;out<<std::setprecision(17)<<"{\"kind\":\"walk-begin\",\"target\":["<<x<<','<<z<<"]}";
  write(out.str());cursor_=count_=0;
 }
 void failed_walk() {
  write("{\"kind\":\"walk-failed\"}");
  std::cerr<<"TOUR_INPUT_TRACE_BEGIN\n";
  for(std::size_t i=0;i<count_;++i)std::cerr<<recent_[(cursor_+recent_.size()-count_+i)%recent_.size()]<<'\n';
  std::cerr<<"TOUR_INPUT_TRACE_END\n";
  if(file_!=INVALID_HANDLE_VALUE)FlushFileBuffers(file_);
 }
};
} // namespace tour_diagnostic
