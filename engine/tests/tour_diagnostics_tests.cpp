#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <aibs/opening_inspections.hpp>
#include <algorithm>
#include <array>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
void require(bool value,const char* why){if(!value)throw std::runtime_error(why);}
#include "tour_diagnostics.hpp"
#include "opening_inspection_panel.inl"
unsigned checks=0;
void check(bool value,const char* why){++checks;require(value,why);}
int main(int argc,char** argv){try{
 require(argc==2,"Supply a new short owned test directory");const std::filesystem::path work(argv[1]);
 require(!std::filesystem::exists(work),"Preserve old diagnostic test evidence");std::filesystem::create_directories(work);
 tour_diagnostic::Controls controls;controls.forward(true);controls.press('E');
 const auto first=controls.take(),second=controls.take();
 check(first.active&&first.forward==1&&first.interact,"Controlled proof input must declare active W/E");
 check(second.active&&second.forward==1&&!second.interact,"Action edge consumed once without releasing held W");
 controls.forward(false);check(controls.take().forward==0,"Explicit release clears controlled W");
 controls.press('V');check(controls.take().cycle_camera&&!controls.take().cycle_camera,"Camera proof uses one actual V edge");
 bool denied=false;try{controls.press(VK_F9);}catch(const std::invalid_argument&){denied=true;}
 check(denied,"Offscreen tour cannot acquire undeclared reset/save keys");
 tour_diagnostic::Frame frame;frame.controlled=true;frame.observed.active=false;frame.effective=first;
 frame.before.ticks=7;frame.after.ticks=8;frame.reading=true;frame.revision=10;
 const auto line=tour_diagnostic::json(frame);
 check(line.find("\"observed_active\":false")!=std::string::npos&&line.find("\"active\":true")!=std::string::npos,"Trace must distinguish native observation from controlled proof input");
 check(line.find("\"reading\":true")!=std::string::npos&&line.find("\"physics_before\":7")!=std::string::npos&&line.find("\"physics_after\":8")!=std::string::npos,"Pause and physical tick evidence retained");
 const auto trace=work/"input.jsonl";{tour_diagnostic::Trace out(trace);out.begin_walk(-37.4f,9.1f);out.frame(frame);}
 std::ifstream file(trace);std::string contents((std::istreambuf_iterator<char>(file)),{});
 check(contents.find(line)!=std::string::npos,"Exact frame evidence written");
 denied=false;try{tour_diagnostic::Trace again(trace);}catch(const std::runtime_error&){denied=true;}
 check(denied,"Existing failed trace must never be truncated");
 check(tour_diagnostic::ordinary_input_trace_allowed(true,false,false,false,false,false),"Managed ordinary Play can explicitly observe its own input");
 check(!tour_diagnostic::ordinary_input_trace_allowed(false,false,false,false,false,false),"Unmanaged/global input observation is not admitted");
 for(unsigned blocked=0;blocked<5;++blocked){std::array<bool,5> modes{};modes[blocked]=true;
  check(!tour_diagnostic::ordinary_input_trace_allowed(true,modes[0],modes[1],modes[2],modes[3],modes[4]),"Proof/walkthrough/recording/performance/controlled modes cannot claim ordinary input");}
 check(!tour_diagnostic::trace_enabled(false,false,false),"Untraced normal Play must not serialize diagnostic frames");
 check(tour_diagnostic::trace_enabled(true,false,false),"Explicit ordinary Play can record actual consumed frames");
 check(tour_diagnostic::trace_enabled(false,true,false)&&tour_diagnostic::trace_enabled(false,false,true),"Existing walkthrough and tour tracing remains admitted");
 tour_diagnostic::Frame ordinary;ordinary.ordinary=true;ordinary.observed.active=false;ordinary.effective=ordinary.observed;
 ordinary.observed.forward=0;ordinary.observed.interact=true;ordinary.observed.cycle_camera=true;ordinary.observed.companion_wait=true;
 ordinary.frame_index=3;ordinary.visible=true;ordinary.foreground=false;ordinary.focus_owned_child=true;ordinary.reading=true;
 ordinary.durable_revision=7;ordinary.visible_revision=8;ordinary.durable_sequence=11;ordinary.pending_batches=1;ordinary.saved=false;
 const auto ordinary_line=tour_diagnostic::json(ordinary);
 check(ordinary_line.find("\"input_source\":\"native-window\"")!=std::string::npos&&ordinary_line.find("ordinary-owned-window-v1")!=std::string::npos,"Ordinary observation is identified without claiming controlled input");
 check(ordinary_line.find("\"consumed_controls\":{\"active\":false")!=std::string::npos&&ordinary_line.find("\"interact\":true")!=std::string::npos&&ordinary_line.find("\"companion_wait\":true")!=std::string::npos,"Only the owned game's consumed controls are retained, including paused action edges");
 check(ordinary_line.find("\"durable_revision\":7")!=std::string::npos&&ordinary_line.find("\"visible_revision\":8")!=std::string::npos&&ordinary_line.find("\"pending_batches\":1")!=std::string::npos&&ordinary_line.find("\"saved\":false")!=std::string::npos,"Trace must not relabel a visible pending outcome durable");
 // Ordinary capture is sampled independently from rendering. Action pulses and
 // semantic transitions are never delayed until the next periodic heartbeat.
 tour_diagnostic::Sampler edge_sampler;tour_diagnostic::Frame edge;
 edge.ordinary=true;edge.elapsed=1.0/360;edge.frame_index=1;
 check(edge_sampler.retain(edge),"Ordinary sampler retains the actual initial frame");
 ++edge.frame_index;check(!edge_sampler.retain(edge),"Unchanged sub-heartbeat render frame is omitted");
 edge.observed.interact=true;++edge.frame_index;
 check(edge_sampler.retain(edge),"One-frame E action survives between heartbeat samples");
 ++edge.frame_index;check(edge_sampler.retain(edge),"Consecutive action pulses remain distinct observations");
 edge.observed.interact=false;edge.effective.companion_wait=true;++edge.frame_index;
 check(edge_sampler.retain(edge),"Effective companion action is retained even without observed action");
 edge.effective.companion_wait=false;edge.observed.forward=edge.effective.forward=1;++edge.frame_index;
 check(edge_sampler.retain(edge),"Held movement begins without waiting for periodic capture");
 edge.observed.forward=edge.effective.forward=0;++edge.frame_index;
 check(edge_sampler.retain(edge),"Held movement release is retained immediately");
 edge.observed.active=edge.effective.active=false;++edge.frame_index;
 check(edge_sampler.retain(edge),"Input deactivation cannot disappear in sampled capture");
 edge.focus_owned_child=true;edge.reading=true;++edge.frame_index;
 check(edge_sampler.retain(edge),"Owned reading focus and pause entry are retained immediately");
 edge.focus_owned_child=false;edge.focus_game=true;edge.reading=false;++edge.frame_index;
 check(edge_sampler.retain(edge),"Reading close and game-focus restoration are retained immediately");
 edge.inspection=true;++edge.frame_index;
 check(edge_sampler.retain(edge),"Inspection-mode transition is retained immediately");
 edge.inspection=false;edge.third_person=true;++edge.frame_index;
 check(edge_sampler.retain(edge),"Ordinary camera-mode transition is retained immediately");
 edge.visible_revision=8;edge.durable_revision=7;edge.pending_batches=1;edge.saved=false;++edge.frame_index;
 check(edge_sampler.retain(edge),"Pending visible revision remains distinct from durable save");
 edge.durable_revision=8;edge.durable_sequence=12;edge.pending_batches=0;edge.saved=true;++edge.frame_index;
 check(edge_sampler.retain(edge),"Actual durable-save acknowledgement is retained immediately");
 edge.save_failed=true;++edge.frame_index;
 check(edge_sampler.retain(edge),"Save failure cannot be sampled away");
 edge.closing=true;++edge.frame_index;
 check(edge_sampler.retain(edge),"Close/drain transition is retained immediately");
 check(edge_sampler.observed()==edge_sampler.retained()+edge_sampler.skipped(),"Sampler reports exact observed/retained/omitted accounting");

 // Twelve simulated minutes at 360 render frames/s, with fixed 60Hz physics,
 // includes an idle minute followed by sustained movement and continuous look.
 // The trace must remain useful for movement evidence without recording every
 // raw mouse delta or duplicate no-physics render frame.
 const auto long_path=work/"ordinary-twelve-minutes.jsonl";
 std::uint64_t sampled_motion=0,sampled_nonstep_motion=0;
 tour_diagnostic::Sampler duration_sampler;
 {tour_diagnostic::Trace long_trace(long_path,true);
  long_trace.ordinary_lifecycle(true,true,0,0);
  for(std::uint64_t index=1;index<=720u*360u;++index){
   tour_diagnostic::Frame sample;sample.ordinary=true;sample.frame_index=index;sample.elapsed=1.0/360;
   sample.visible=sample.foreground=sample.focus_game=true;sample.saved=true;
   const bool moving=index>60u*360u;
   sample.observed.forward=sample.effective.forward=moving?1.f:0.f;
   sample.observed.yaw_delta=sample.effective.yaw_delta=static_cast<float>((index%7)+1)*.0001f;
   sample.camera.yaw=static_cast<float>(index)*.00001f;
   sample.before.ticks=(index-1)/6;sample.after.ticks=index/6;
   sample.before.grounded=sample.after.grounded=true;
   sample.before.feet.x=moving?static_cast<float>(sample.before.ticks-3600)*.01f:0.f;
   sample.after.feet.x=moving?static_cast<float>(sample.after.ticks-3600)*.01f:0.f;
   sample.tick_before=sample.before.ticks;sample.tick_after=sample.after.ticks;
   const bool retained=duration_sampler.retain(sample);
   if(retained&&moving){
    if(sample.before.ticks!=sample.after.ticks)++sampled_motion;
    else ++sampled_nonstep_motion;
   }
   long_trace.frame(sample);
  }
  long_trace.ordinary_lifecycle(false,true,0,0);
  check(long_trace.complete(),"Twelve-minute high-render-rate ordinary session closes with COMPLETE capture");
 }
 check(duration_sampler.observed()==720u*360u,"Sampling counts every supplied native render observation");
 check(duration_sampler.retained()<10000&&duration_sampler.skipped()>240000,"Continuous mouse motion and high render rate do not defeat heartbeat sampling");
 check(sampled_motion>5000&&sampled_nonstep_motion<=2,"Moving periodic observations carry actual physics steps, apart from immediate state edges");
 check(std::filesystem::file_size(long_path)<16u*1024u*1024u,"Twelve-minute ordinary input trace stays below half the fixed byte budget");

 const auto final_path=work/"ordinary-final-suppressed.jsonl";
 {tour_diagnostic::Trace final_trace(final_path,true);tour_diagnostic::Frame final_frame;
  final_frame.ordinary=true;final_frame.frame_index=1;final_frame.elapsed=.001;
  final_trace.ordinary_lifecycle(true,true,0,0);final_trace.frame(final_frame);
  final_frame.frame_index=2;final_frame.camera.yaw=.123f;
  final_trace.frame(final_frame);
  final_frame.frame_index=3;final_frame.camera.yaw=.456f;
  final_trace.frame(final_frame);final_trace.ordinary_lifecycle(false,true,0,0);
  check(final_trace.complete(),"Graceful stop flushes the final suppressed observation before capture completion");
 }
 std::ifstream final_file(final_path);std::string final_contents((std::istreambuf_iterator<char>(final_file)),{});
 const auto final_frame_position=final_contents.find("\"frame_index\":3");
 const auto final_stop_position=final_contents.find("ordinary-play-stopped");
 check(final_frame_position!=std::string::npos&&final_stop_position!=std::string::npos&&final_frame_position<final_stop_position,"Final actual frame precedes terminal lifecycle even when it was below heartbeat interval");
 check(final_contents.find("\"frame_index\":2")==std::string::npos,"A suppressed middle render frame is not falsely reported as retained");
 check(final_contents.find("\"capture_policy\":\"sampled-10hz-plus-input-state-edges-v1\"")!=std::string::npos&&final_contents.find("\"nominal_sample_interval_seconds\":0.1")!=std::string::npos,"Ordinary lifecycle declares the actual sampling policy and nominal interval");
 check(final_contents.find("\"observed_frames\":3,\"retained_frames\":2,\"omitted_frames\":1")!=std::string::npos,"Terminal accounting includes the flushed final frame and only the still-omitted middle frame");
 const auto passive_path=work/"ordinary.jsonl";{tour_diagnostic::Trace passive(passive_path,true);
  passive.ordinary_lifecycle(true,true,7,11);passive.frame(ordinary);check(!passive.complete(),"No complete trace claim before actual stopped lifecycle");
  passive.ordinary_lifecycle(false,true,8,12);check(passive.complete(),"Graceful ordinary trace records its terminal lifecycle");}
 std::ifstream passive_file(passive_path);std::string passive_contents((std::istreambuf_iterator<char>(passive_file)),{});
 check(passive_contents.find(ordinary_line)!=std::string::npos&&passive_contents.find("ordinary-play-ready")!=std::string::npos&&passive_contents.find("ordinary-play-stopped")!=std::string::npos,"Exact observed frame and both lifecycle records survive close");
 const auto unsaved_path=work/"ordinary-unsaved.jsonl";{tour_diagnostic::Trace unsaved(unsaved_path,true);
  unsaved.ordinary_lifecycle(true,false,7,11);unsaved.ordinary_lifecycle(false,false,7,11);
  check(unsaved.complete(),"Complete retained capture is independent of the recorded saved=false outcome");}
 std::ifstream unsaved_file(unsaved_path);std::string unsaved_contents((std::istreambuf_iterator<char>(unsaved_file)),{});
 check(unsaved_contents.find("\"saved\":false")!=std::string::npos,"Complete diagnostic capture must preserve an unsaved outcome honestly");
 const auto bounded_path=work/"ordinary-bounded.jsonl";{tour_diagnostic::Trace bounded(bounded_path,true);
  for(unsigned frame_index=0;frame_index<65537;++frame_index)bounded.frame(ordinary);
  check(!bounded.active()&&!bounded.complete(),"Observational budget exhaustion disables tracing without throwing or claiming completion");
  bounded.ordinary_lifecycle(false,true,8,12);check(!bounded.complete(),"A later saved stop cannot relabel an incomplete trace complete");}
 check(std::filesystem::file_size(bounded_path)<=32u*1024u*1024u,"Ordinary retained trace never exceeds its existing byte budget");
 denied=false;try{tour_diagnostic::Trace strict(work/"strict-bounded.jsonl");for(unsigned frame_index=0;frame_index<65537;++frame_index)strict.frame(ordinary);}catch(const std::runtime_error&){denied=true;}
 check(denied,"Legacy proof budget exhaustion must remain a strict diagnostic failure");
 aibs::NativeWindow native(960,640,L"Hidden controlled diagnostic",false);const auto owner=static_cast<HWND>(native.native_handle());
 SendMessageW(owner,WM_KEYDOWN,'W',0);check(native.input().forward==1,"Owned native W remains actual platform input");
 SendMessageW(owner,WM_ACTIVATEAPP,FALSE,0);const auto inactive=native.input();
 check(!inactive.active&&inactive.forward==0,"Ordinary focus loss must still pause and clear native held keys");
 controls.forward(true);check(controls.take().active&&controls.take().forward==1,"Controlled fixture stays distinct from inactive native window");
 OpeningInspectionPanel panel(owner,false);aibs::OpeningInspection entry;entry.title="Synthetic proof";entry.text="This text tests a hidden native reading control.";entry.source="Synthetic diagnostic fixture.";
 panel.show(entry);
 check(panel.visible(),"Hidden proof reading still pauses simulation logically");
 check(tour_diagnostic::owned_child_focus(owner,panel.body_handle())&&!tour_diagnostic::owned_child_focus(owner,owner)&&!tour_diagnostic::owned_child_focus(owner,nullptr),"Observation recognizes the owned reading popup without moving focus or mistaking the game root for a child");
 check(!IsWindowVisible(owner)&&!IsWindowVisible(panel.native_handle()),"Offscreen owner and reading panel stay hidden");
 check(GetForegroundWindow()!=owner&&GetForegroundWindow()!=panel.native_handle(),"Proof must not acquire foreground focus");
 check(panel.body_text().find(L"hidden native reading")!=std::wstring::npos,"Hidden reading uses same real control text");
 check(panel.capture_body(work/"reading.bmp"),"Hidden reading still produces real glyph readback");
 SendMessageW(panel.continue_handle(),BM_CLICK,0,0);
 check(!panel.visible()&&!IsWindowVisible(panel.native_handle())&&!IsWindowVisible(owner),"Actual Continue resumes logical proof without showing UI");
 std::cout<<checks<<" tour diagnostic checks passed; hidden owned HWNDs, no desktop input/focus\n";return 0;
}catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}}
