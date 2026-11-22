#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include "performance_readiness.hpp"
#include <iostream>
#include <stdexcept>
namespace {int checks=0;void check(bool v,const char* s){++checks;if(!v)throw std::runtime_error(s);}}
int main(){
 const auto foreground_before=GetForegroundWindow();
 HWND game=nullptr,panel=nullptr,foreign=nullptr;
 try{
  game=CreateWindowExW(0,L"STATIC",L"Owned readiness test",WS_OVERLAPPED,0,0,64,64,nullptr,nullptr,GetModuleHandleW(nullptr),nullptr);
  panel=CreateWindowExW(0,L"STATIC",L"Owned panel test",WS_POPUP,0,0,32,32,game,nullptr,GetModuleHandleW(nullptr),nullptr);
  foreign=CreateWindowExW(0,L"STATIC",L"Separate test window",WS_OVERLAPPED,0,0,64,64,nullptr,nullptr,GetModuleHandleW(nullptr),nullptr);
  check(game&&panel&&foreign,"Could not create hidden owned test windows");
  check(!IsWindowVisible(game)&&!IsWindowVisible(panel)&&!IsWindowVisible(foreign),"Readiness tests must not show or activate windows");
  for(unsigned bits=0;bits<16;++bits){
   const bool reading=(bits&1)!=0,inspecting=(bits&2)!=0,saving=(bits&4)!=0,exiting=(bits&8)!=0;
   check(aibs::performance::context_ready(game,game,true,false,reading,inspecting,saving,exiting),"Gameplay rejected normal own UI/save state");
   check(aibs::performance::context_ready(game,panel,true,false,reading,inspecting,saving,exiting),"Gameplay rejected actual owned-root panel");
   check(aibs::performance::context_ready(game,game,false,false,reading,inspecting,saving,exiting)==(bits==0),"Stationary diagnostic contract changed");
   check(!aibs::performance::context_ready(game,foreign,true,false,reading,inspecting,saving,exiting),"Unrelated window passed gameplay readiness");
   check(!aibs::performance::context_ready(game,game,true,true,reading,inspecting,saving,exiting),"Minimized game passed readiness");
  }
  check(!aibs::performance::context_ready(game,panel,false,false,false,false,false,false),"Stationary sample accepted panel focus");
  check(!aibs::performance::context_ready(game,nullptr,true,false,false,false,false,false),"Absent foreground passed");
  check(!aibs::performance::context_ready(nullptr,foreign,true,false,false,false,false,false),"Absent game HWND passed");
  check(GetForegroundWindow()==foreground_before,"Hidden readiness tests changed actual desktop focus");
  DestroyWindow(panel);DestroyWindow(foreign);DestroyWindow(game);
  std::cout<<checks<<" actual hidden-HWND readiness checks passed; no game performance measured\n";return 0;
 }catch(const std::exception& e){if(panel)DestroyWindow(panel);if(foreign)DestroyWindow(foreign);if(game)DestroyWindow(game);std::cerr<<e.what()<<'\n';return 1;}
}
