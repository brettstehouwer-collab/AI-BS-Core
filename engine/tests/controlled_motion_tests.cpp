#include "controlled_motion.hpp"
#include "performance_phases.hpp"
#include <aibs/engine.hpp>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
using namespace aibs;
namespace {unsigned checks=0;void check(bool ok,const char* why){++checks;if(!ok)throw std::runtime_error(why);}}
int main(){try{
 using namespace controlled_motion;
 check(allowed(true,false,true,true,false,false,false,false),"Fresh controlled profile rejected");
 for(unsigned i=0;i<8;++i){bool p=true,g=false,m=true,f=true,s=false,t=false,r=false,o=false;
  switch(i){case 0:p=false;break;case 1:g=true;break;case 2:m=false;break;case 3:f=false;break;case 4:s=true;break;case 5:t=true;break;case 6:r=true;break;default:o=true;break;}
  check(!allowed(p,g,m,f,s,t,r,o),"Controlled policy admitted an incompatible/retained mode");}
 Shuttle shuttle({0,0,0},{5,0,0});const auto command=shuttle.input({0,0,0},0);
 check(command.active&&command.forward==1&&!command.interact&&!command.build&&!command.reload&&!command.jump&&!command.sprint,"Motion generated undeclared actions");
 check(std::abs(command.yaw_delta-1.5707963f)<1e-5f,"Shuttle did not turn through normal yaw input");
 (void)shuttle.input({5,0,0},0);check(shuttle.arrivals()==1,"Shuttle endpoint not observed");
 for(const float length:{0.f,2.f,9.f}){bool refused=false;try{Shuttle bad({0,0,0},{length,0,0});}catch(const std::invalid_argument&){refused=true;}check(refused,"Invalid shuttle geometry accepted");}
 const SceneSnapshot scene{new_uuid(),0,{{new_uuid(),"floor",{0,-1,0},{20,1,20},{.2f,.3f,.2f}}}};
 // Actual Jolt/Player movement at360Hz rendering cadence. These are CPU
 // simulation checks, not real hardware FPS or wall-clock performance claims.
 PlayerController player(scene,{0,.2f,0});WindowInput idle;
 for(unsigned n=0;n<120;++n)player.update(idle,1./60);
 check(player.state().grounded,"CPU capsule failed to settle");
 const auto start=player.state().feet;Shuttle actual(start,{start.x+5,start.y,start.z});Coverage moving;
 for(unsigned n=0;n<20*360;++n){const auto before=player.state();const auto input=actual.input(before.feet,player.camera().yaw);player.update(input,1./360);moving.observe(before,player.state(),1./360,true);}
 check(moving.physical_steps==1200,"Render cadence changed actual60Hz physics step accounting");
 check(moving.moving_physical_seconds>19.9,"Motion time was undercounted as sparse render displacement frames");
 check(moving.horizontal_metres>130&&actual.arrivals()>20,"Actual capsule movement was not sustained");
 check(moving.qualifies(20,actual.arrivals()),"Actual moving simulation failed coverage policy");
 Coverage still;
 for(unsigned n=0;n<20*360;++n){const auto before=player.state();player.update(idle,1./360);still.observe(before,player.state(),1./360,true);}
 check(!still.qualifies(20,50)&&still.moving_physical_seconds<.1,"Idle held-clock fixture passed moving coverage");
 check(!moving.qualifies(14,actual.arrivals())&&!moving.qualifies(20,1),"Short or untraversed run passed");
 auto before=player.state(),after=before;after.feet.x+=5;Coverage teleported;teleported.observe(before,after,.01,true);
 check(teleported.invalid&&!teleported.qualifies(20,50),"Zero-tick teleport passed coverage");
 after=before;after.ticks+=1;after.dropped_seconds+=.1;Coverage dropped;dropped.observe(before,after,.15,true);
 check(dropped.invalid,"Dropped physics time was hidden");
 check(dropped.first_invalid==Coverage::Invalid::dropped_physics&&dropped.invalid_observations==1,"Dropped physics reason missing");
 check(dropped.first_ticks_before==before.ticks&&dropped.first_ticks_after==after.ticks&&dropped.first_dropped_after>dropped.first_dropped_before,"First rejected physical interval lost");
 check(dropped.physical_steps==0&&dropped.moving_steps==0,"Invalid interval was credited as actual movement");
 check(std::abs(dropped.commanded_wall_seconds-.15)<1e-8&&std::abs(dropped.rejected_elapsed_seconds-.15)<1e-8,"Rejected command interval disappeared from diagnostic wall accounting");
 const auto first_fault=dropped.first_invalid_observation;auto valid_after=after;valid_after.ticks+=1;dropped.observe(after,valid_after,1./60,true);
 check(dropped.invalid&&dropped.first_invalid_observation==first_fault&&!dropped.qualifies(20,50),"A later valid interval cleared sticky failure");
 auto jump=valid_after;jump.feet.x+=5;dropped.observe(valid_after,jump,.1,true);
 check(dropped.invalid_observations==2&&dropped.first_invalid==Coverage::Invalid::dropped_physics,"Later failure replaced first cause");
 after=before;after.ticks-=1;Coverage reset;reset.observe(before,after,.01,true);check(reset.invalid,"Reset tick counter passed");
 // Genuine collision with a wall must not count commanded time as motion.
 const SceneSnapshot blocked{new_uuid(),0,{{new_uuid(),"floor",{0,-1,0},{20,1,20},{.2f,.3f,.2f}},
  {new_uuid(),"wall",{0,2,2},{10,2,.5f},{.3f,.3f,.3f}}}};
 PlayerController against(blocked,{0,.1f,0});for(unsigned n=0;n<120;++n)against.update(idle,1./60);
 WindowInput forward;forward.forward=1;Coverage obstruction;
 for(unsigned n=0;n<20*360;++n){const auto old=against.state();against.update(forward,1./360);obstruction.observe(old,against.state(),1./360,true);}
 check(!obstruction.qualifies(20,50)&&obstruction.horizontal_metres<2,"Blocked actual capsule passed moving coverage");
 // Synthetic phase-algorithm fixtures, not actual CPU/hardware timing. A
 // slow completed frame N and its next iteration's long physics dt must stay
 // separately identifiable, including the context before the first fault.
 using namespace performance_phases;
 Collector causal;Sample stall;stall.frame_index=10;stall.measuring=true;stall.loop_started_seconds=18;
 stall.seconds[at(Phase::render)]=5.76;stall.seconds[at(Phase::loop_gap)]=.004;stall.frame_finished_seconds=23.76;
 causal.observe(stall);Sample following;following.frame_index=11;following.measuring=true;following.loop_started_seconds=23.764;
 following.seconds[at(Phase::render)]=.004;following.seconds[at(Phase::loop_gap)]=5.764;causal.observe(following,true);
 check(causal.have_motion_fault&&causal.first_motion_fault.current.frame_index==11&&causal.first_motion_fault.preceding.frame_index==10,"FrameN stall was incorrectly attached only to frameN+1");
 check(causal.first_motion_fault.preceding.seconds[at(Phase::render)]==5.76&&causal.first_motion_fault.current.seconds[at(Phase::loop_gap)]==5.764,"Causal phase context lost the measured intervals");
 check(causal.outlier_count==2&&causal.retained==2&&causal.maxima[at(Phase::render)]==5.76,"Outlier maxima/count incorrect");
 causal.observe(stall,true);check(causal.first_motion_fault.current.frame_index==11,"Later fault replaced first causal context");
 Collector bounded;
 for(unsigned n=0;n<42;++n){Sample sample;sample.frame_index=n+1;sample.seconds[at(Phase::hud)]=.06+n*.01;bounded.observe(sample);}
 check(bounded.retained==Collector::capacity&&bounded.outlier_count==42,"Outlier storage unbounded or total omitted");
 double minimum=100;for(std::size_t n=0;n<bounded.retained;++n)minimum=std::min(minimum,bounded.outliers[n].current.maximum());
 check(minimum>=.32-1e-8&&bounded.maxima[at(Phase::hud)]>=.47-1e-8,"Largest outliers were discarded on capacity overflow");
 Sample malformed;malformed.seconds[at(Phase::window_poll)]=-1;bounded.observe(malformed);
 check(bounded.invalid_samples==1&&bounded.retained==Collector::capacity,"Malformed phase duration corrupted retained records");
 check(sizeof(Collector)<16384,"Private fixed diagnostic storage exceeds16KiB");
 Coverage nonfinite_time;nonfinite_time.observe(before,before,std::numeric_limits<double>::infinity(),true);
 check(nonfinite_time.invalid&&nonfinite_time.first_invalid==Coverage::Invalid::bad_elapsed&&!nonfinite_time.qualifies(20,50),"Nonfinite elapsed input was accepted");
 auto nonfinite_position=before;nonfinite_position.feet.x=std::numeric_limits<float>::quiet_NaN();Coverage bad_position;bad_position.observe(before,nonfinite_position,.1,true);
 check(bad_position.invalid&&bad_position.first_invalid==Coverage::Invalid::bad_position,"Nonfinite physical position was accepted");
 std::ostringstream failure_json;failure_json<<'[';write_diagnostic_real(failure_json,nonfinite_time.first_invalid_elapsed);failure_json<<',';write_diagnostic_real(failure_json,bad_position.first_invalid_distance);failure_json<<',';write_diagnostic_real(failure_json,1.5);failure_json<<']';
 check(failure_json.str()=="[null,null,1.5]","Rejected nonfinite diagnostic corrupted JSON instead of remaining null and failed");
 std::cout<<checks<<" controlled-motion CPU checks passed; no hardware performance measured\n";return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
