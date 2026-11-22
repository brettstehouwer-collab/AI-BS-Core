#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <aibs/platform.hpp>
#include <algorithm>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {
void require(bool value,const char* message){if(!value)throw std::runtime_error(message);}
std::wstring text(HWND window){const int length=GetWindowTextLengthW(window);std::wstring result(static_cast<std::size_t>(length)+1,L'\0');GetWindowTextW(window,result.data(),length+1);result.resize(static_cast<std::size_t>(length));return result;}
struct Children{HWND status=nullptr,crosshair=nullptr;};
BOOL CALLBACK find_children(HWND child,LPARAM data){
 auto& result=*reinterpret_cast<Children*>(data);wchar_t name[32]{};GetClassNameW(child,name,32);
 if(_wcsicmp(name,L"STATIC")==0){if(text(child)==L"+")result.crosshair=child;else result.status=child;}return TRUE;
}
RECT bounds(HWND child,HWND parent){RECT result{};require(GetWindowRect(child,&result)!=0,"Child bounds");MapWindowPoints(nullptr,parent,reinterpret_cast<POINT*>(&result),2);return result;}
int required_height(HWND status,const std::wstring& value,int width){
 HDC dc=GetDC(status);require(dc!=nullptr,"Real status device context");
 const auto font=reinterpret_cast<HFONT>(SendMessageW(status,WM_GETFONT,0,0));require(font!=nullptr,"Actual status font");
 const auto old=SelectObject(dc,font);RECT needed{0,0,width,0};
 auto copy=value;const auto measured=DrawTextW(dc,copy.data(),static_cast<int>(copy.size()),&needed,DT_CALCRECT|DT_WORDBREAK|DT_EXPANDTABS);
 SelectObject(dc,old);ReleaseDC(status,dc);require(measured>0,"Actual HUD text measurement");return needed.bottom-needed.top;
}
void check(aibs::NativeWindow& window,const std::wstring& expected,const char* label){
 require(window.poll(),"Window remains usable");const auto parent=static_cast<HWND>(window.native_handle());Children children;EnumChildWindows(parent,find_children,reinterpret_cast<LPARAM>(&children));
 require(children.status&&children.crosshair,"Existing status and crosshair STATIC controls remain available");
 require(text(children.status)==expected,"Complete status text remains readable through native control");
 RECT client{};GetClientRect(parent,&client);const auto panel=bounds(children.status,parent),crosshair=bounds(children.crosshair,parent);
 const int needed=required_height(children.status,expected,panel.right-panel.left);
 std::cout<<label<<" client="<<client.right<<'x'<<client.bottom<<" panel="<<panel.left<<','<<panel.top<<' '<<panel.right-panel.left<<'x'<<panel.bottom-panel.top<<" needed="<<needed<<'\n';
 require(panel.left>=0&&panel.top>=0&&panel.right<=client.right&&panel.bottom<=client.bottom,"Status panel must fit actual client bounds after creation/resize");
 require(panel.left==12&&panel.top>=0&&panel.top<=12,"HUD keeps its horizontal anchor and bounded vertical inset");
 if(needed+4<=client.bottom-24)require(panel.top==12,"Normal fitting HUD retains twelve-pixel inset");
 require(panel.bottom-panel.top>=needed,"Actual font/wrapped HUD text must fit visible panel height");
 require(crosshair.left==client.right/2-8&&crosshair.top==client.bottom/2-8&&crosshair.right-crosshair.left==16&&crosshair.bottom-crosshair.top==16,"Crosshair remains centered on actual resized client");
}
const std::wstring chapter=
 L"WASD walk | Right-drag look | Space jump | V camera | F2 inspection\n"
 L"E: aimed mechanism | B relay | Delete dismantle | Ctrl+Y help / Ctrl+Z decline | F5 retry | F9 reload\n"
 L"Authored Adam hint: The bypass relay is offline. A latched door remains usable; disconnect the old feed, build another relay, or repair the main line.\n"
 L"Recorded (acknowledged): Physical arc contact and a safe return were recorded.\n"
 L"UNSAVED / RETRY | visible 123 | durable 122\n"
 L"Blocked: Action would leave no supported safe BS spawn; choose another placement.";
// Retained real chapter HUD that exceeded the old 960x640 panel (629 > 616).
const std::wstring retained_chapter=
 L"WASD walk | Right-drag look | Space jump | V camera | F2 inspect | F5 retry | F9 reload\n"
 L"E (centre): Move closer to read: Controller and turning | B relay | Delete dismantle | Ctrl+Y help / Ctrl+Z decline\n"
 L"Find isolation switch: 23 m, behind-right (direction only; use a clear path).\n"
 L"I'm here. This nook has reserve light, but we are still inside Jenison. Start with what still responds. "
 L"Follow the west signal path to the supply, or look around before we go.\n"
 L"F6 Follow | F7 Wait | F8 Recall: Adam is following. F7: Wait | F8: Recall.\n"
 L"Authored Adam hint: The diagnostic probe is in the reserve nook. You choose when to pick it up.\n"
 L"Recorded (acknowledged): No acknowledged chapter outcomes yet.\n"
 L"SAVED | visible 0 | durable 0\n"
 L"Jenison is not home. Follow what still responds.";
}
int main(){
 SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);
 unsigned failures=0;
 for(const auto dimensions:{std::pair{960u,640u},std::pair{1440u,900u},std::pair{800u,600u}}){
  try{aibs::NativeWindow window(dimensions.first,dimensions.second,L"AI-BS status panel measurement",false);window.set_status(chapter);check(window,chapter,"chapter");}
  catch(const std::exception& error){++failures;std::cerr<<"FAIL initial "<<dimensions.first<<'x'<<dimensions.second<<": "<<error.what()<<'\n';}
 }
 try{
  aibs::NativeWindow window(1440,900,L"AI-BS status panel resize measurement",false);
  window.set_status(chapter);window.set_size(800,600);check(window,chapter,"same text resized800");
  window.set_size(640,480);check(window,chapter,"same text resized640");
  window.set_size(480,360);check(window,chapter,"same text resized480");
  window.set_size(960,640);check(window,chapter,"same text resized960");
  const std::wstring original=L"WASD walk | Right-drag look | Space jump | V camera\nE repair | B build | Delete dismantle\nSAVED | visible 3 | durable 3";
  window.set_status(original);check(window,original,"original mode shorter text");
  window.set_status(chapter);check(window,chapter,"chapter longer text");
 }catch(const std::exception& error){++failures;std::cerr<<"FAIL resize/text changes: "<<error.what()<<'\n';}
 // Warm the measured-font path before lifetime accounting. An isolated
 // diagnostic confirmed every owned HFONT deletes successfully and becomes
 // invalid; the first GDI font-measurement path retains two process resources.
 const auto resources_before_retained=GetGuiResources(GetCurrentProcess(),GR_GDIOBJECTS);
 try{
  aibs::NativeWindow window(960,640,L"AI-BS retained chapter HUD fit",false);
  window.set_status(retained_chapter);check(window,retained_chapter,"retained960");
  Children initial;EnumChildWindows(static_cast<HWND>(window.native_handle()),find_children,reinterpret_cast<LPARAM>(&initial));
  // The stock font is DPI-dependent. Compare its real wrapped extent with
  // the same four-pixel padding/full client height used by legacy fitting.
  RECT retained_client{};GetClientRect(static_cast<HWND>(window.native_handle()),&retained_client);
  HDC stock_dc=GetDC(initial.status);require(stock_dc!=nullptr,"Stock fit measurement context");
  const auto stock_font=static_cast<HFONT>(GetStockObject(DEFAULT_GUI_FONT));const auto previous=SelectObject(stock_dc,stock_font);
  RECT stock_extent{0,0,std::max(1,static_cast<int>(retained_client.right)-24),0};auto stock_text=retained_chapter;
  const auto measured=DrawTextW(stock_dc,stock_text.data(),static_cast<int>(stock_text.size()),&stock_extent,DT_CALCRECT|DT_WORDBREAK|DT_EXPANDTABS);
  SelectObject(stock_dc,previous);ReleaseDC(initial.status,stock_dc);require(measured>0,"Stock wrapped extent measured");
  const bool stock_fits=stock_extent.bottom-stock_extent.top+4<=retained_client.bottom;
  require((reinterpret_cast<HFONT>(SendMessageW(initial.status,WM_GETFONT,0,0))==stock_font)==stock_fits,"Legacy stock font selected exactly when its actual DPI-dependent text fits");
  window.set_size(640,480);check(window,retained_chapter,"retained640");
  window.set_size(1440,900);check(window,retained_chapter,"retained1440");
  Children children;EnumChildWindows(static_cast<HWND>(window.native_handle()),find_children,reinterpret_cast<LPARAM>(&children));
  require(reinterpret_cast<HFONT>(SendMessageW(children.status,WM_GETFONT,0,0))==GetStockObject(DEFAULT_GUI_FONT),"Large window restores original stock font");
  window.set_size(640,480);window.set_status(L"SAVED");check(window,L"SAVED","short text restores stock");
  require(reinterpret_cast<HFONT>(SendMessageW(children.status,WM_GETFONT,0,0))==GetStockObject(DEFAULT_GUI_FONT),"Short text restores original stock font");
  window.set_status(retained_chapter);check(window,retained_chapter,"long text refits");
  LOGFONTW font{};const auto active=reinterpret_cast<HFONT>(SendMessageW(children.status,WM_GETFONT,0,0));
  require(GetObjectW(active,sizeof(font),&font)==sizeof(font),"Actual fitted font is inspectable");
  require(active==GetStockObject(DEFAULT_GUI_FONT)||std::abs(font.lfHeight)>=12,"Fitted font retains readable twelve-pixel floor");
  const auto resources=GetGuiResources(GetCurrentProcess(),GR_GDIOBJECTS);
  for(int n=0;n<20;++n){window.set_size(1440,900);window.set_status(L"SAVED");window.set_size(640,480);window.set_status(retained_chapter);check(window,retained_chapter,"repeated fit");}
  require(GetGuiResources(GetCurrentProcess(),GR_GDIOBJECTS)==resources,"Repeated known resize/text cycle does not leak GDI fonts");
 }catch(const std::exception& error){++failures;std::cerr<<"FAIL retained long chapter: "<<error.what()<<'\n';}
 try{
  for(int n=0;n<5;++n){aibs::NativeWindow window(640,480,L"AI-BS fitted font lifetime cycle",false);window.set_status(retained_chapter);check(window,retained_chapter,"fresh fitted window");window.set_size(1440,900);check(window,retained_chapter,"fresh stock restore");}
 }catch(const std::exception& error){++failures;std::cerr<<"FAIL fresh font lifetime: "<<error.what()<<'\n';}
 const auto resources_after_retained=GetGuiResources(GetCurrentProcess(),GR_GDIOBJECTS);
 std::cout<<"GDI lifetime before="<<resources_before_retained<<" after="<<resources_after_retained<<'\n';
 if(resources_after_retained!=resources_before_retained){++failures;std::cerr<<"FAIL owned HUD font destruction leaked GDI resources\n";}
 try{
  HFONT owned_compact_font=nullptr;
  {
   aibs::NativeWindow window(1920,1080,L"AI-BS compact/details HUD",false);
   const std::wstring compact=L"E: collect diagnostic probe\nSAVED | F1 details";
   window.set_status_views(compact,chapter);check(window,compact,"compact1080");
   const auto parent=static_cast<HWND>(window.native_handle());Children children;
   EnumChildWindows(parent,find_children,reinterpret_cast<LPARAM>(&children));
   const auto panel=bounds(children.status,parent);RECT client{};GetClientRect(parent,&client);
   require(panel.right-panel.left<client.right/2,"Short compact view does not cover the whole game width");
   owned_compact_font=reinterpret_cast<HFONT>(SendMessageW(children.status,WM_GETFONT,0,0));LOGFONTW font{};
   require(GetObjectW(owned_compact_font,sizeof(font),&font)==sizeof(font)&&std::abs(font.lfHeight)==24,"1080 compact font is capped at24client pixels regardless of DPI");
   window.set_status_views(compact,chapter+L"\nNew detail only");
   require(text(children.status)==compact,"Updating hidden details changes the visible compact view");
   SendMessageW(parent,WM_KEYDOWN,VK_F1,1);check(window,chapter+L"\nNew detail only","F1 details");
   SendMessageW(parent,WM_KEYDOWN,VK_F1,static_cast<LPARAM>((1LL<<30)|1));
   require(text(children.status)==chapter+L"\nNew detail only","Held F1 auto-repeat toggles repeatedly");
   const std::wstring next=L"E: sample supply contact\nSAVED | F1 details";
   window.set_status_views(next,chapter);require(text(children.status)==chapter,"Live content refresh unexpectedly collapses selected details");
   SendMessageW(parent,WM_KEYUP,VK_F1,1);SendMessageW(parent,WM_KEYDOWN,VK_F1,1);
   check(window,next,"F1 compact");
   const auto actions=window.input();
   require(!actions.interact&&!actions.build&&!actions.reload&&!actions.save&&!actions.toggle_flight&&!actions.companion_follow&&!actions.companion_wait&&!actions.companion_recall,"F1 leaked a gameplay action");
   window.set_size(640,480);check(window,next,"compact480");
   const auto small_font=reinterpret_cast<HFONT>(SendMessageW(children.status,WM_GETFONT,0,0));
   require(GetObjectW(small_font,sizeof(font),&font)==sizeof(font)&&std::abs(font.lfHeight)==16,"Compact smaller client preserves16pixel readability floor");
   window.set_size(1920,1080);check(window,next,"compact1080 cached");
   require(reinterpret_cast<HFONT>(SendMessageW(children.status,WM_GETFONT,0,0))==owned_compact_font,"Known compact size churns owned font handles");
   const auto authored=next+L"\nAdam: Follow the west signal path to the supply, or look around before we go. The reserve light still responds, and you can choose when to collect the diagnostic probe and return.";
   window.set_status_views(authored,chapter);check(window,authored,"compact long authored hint");
   const auto wrapped=bounds(children.status,parent);
   require(wrapped.right-wrapped.left<=static_cast<LONG>(window.width()*3/4),"Long compact authored hint expands beyond three-quarters of client");
   window.set_status(next);check(window,next,"legacy after compact");
   require(reinterpret_cast<HFONT>(SendMessageW(children.status,WM_GETFONT,0,0))==GetStockObject(DEFAULT_GUI_FONT),"Legacy API did not restore its prior stock fitting");
   SendMessageW(parent,WM_KEYUP,VK_F1,1);SendMessageW(parent,WM_KEYDOWN,VK_F1,1);
   require(text(children.status)==next,"F1 changed a legacy single-view caller");
  }
  LOGFONTW destroyed{};require(GetObjectW(owned_compact_font,sizeof(destroyed),&destroyed)==0,"Compact owned font survives its window lifetime");
 }catch(const std::exception& error){++failures;std::cerr<<"FAIL compact/details status: "<<error.what()<<'\n';}
 if(!failures)std::cout<<"PASS: native STATIC font/wrap measurement, resize and crosshair layout\n";
 return failures?1:0;
}
