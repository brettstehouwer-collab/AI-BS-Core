#pragma once
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
namespace aibs::performance {
// Callers provide actual foreground HWND and game state; no focus is changed.
inline bool context_ready(HWND game,HWND foreground,bool gameplay,bool minimized,
 bool reading,bool inspecting,bool saving,bool exiting)noexcept{
 if(!game||!foreground||minimized)return false;
 if(gameplay)return foreground==game||GetAncestor(foreground,GA_ROOTOWNER)==game;
 return foreground==game&&!reading&&!inspecting&&!saving&&!exiting;
}
}
