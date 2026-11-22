#pragma once
// Internal live-HUD raster. Only direct STATIC children of this process's
// NativeWindow are admitted. Pixels come from WM_PRINTCLIENT into private DIBs,
// never a window/desktop DC. Opaque RGBA regions are copied into the DX12 target.
#include <windows.h>
#include <algorithm>
#include <array>
#include <atomic>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <limits>
#include <stdexcept>
#include <string_view>
#include <vector>
namespace aibs::owned_hud {
inline std::atomic<std::uint64_t> rasterizations{0},upload_allocations{0};
inline constexpr std::size_t maximum_bytes=16u*1024u*1024u;
inline constexpr std::size_t maximum_text=16384;
struct Region {UINT x=0,y=0,width=0,height=0,pitch=0,source_x=0,source_y=0;UINT64 offset=0;};
struct Control {
 HWND window=nullptr;HFONT font=nullptr;RECT rect{};LONG_PTR style=0;
 int length=0;std::array<wchar_t,maximum_text+1> text{};
 bool same(const Control& other)const noexcept{
  return window==other.window&&font==other.font&&style==other.style&&
   EqualRect(&rect,&other.rect)&&length==other.length&&
   std::equal(text.begin(),text.begin()+length,other.text.begin());
 }
};
class Snapshot {
 HWND owner_=nullptr;
 std::array<Control,2> controls_{};
 std::array<Region,2> regions_{};
 std::size_t count_=0;
 std::uint64_t version_=0;
 UINT width_=0,height_=0;
 std::vector<std::byte> bytes_;
 static void render(const Control& control,const Region& region,std::vector<std::byte>& destination){
  HDC dc=CreateCompatibleDC(nullptr);
  if(!dc)throw std::runtime_error("Cannot create private live HUD DC");
  BITMAPINFO info{};info.bmiHeader.biSize=sizeof(BITMAPINFOHEADER);
  info.bmiHeader.biWidth=static_cast<LONG>(region.width);info.bmiHeader.biHeight=-static_cast<LONG>(region.height);
  info.bmiHeader.biPlanes=1;info.bmiHeader.biBitCount=32;info.bmiHeader.biCompression=BI_RGB;
  void* pixels=nullptr;HBITMAP bitmap=CreateDIBSection(nullptr,&info,DIB_RGB_COLORS,&pixels,nullptr,0);
  if(!bitmap||!pixels){if(bitmap)DeleteObject(bitmap);DeleteDC(dc);throw std::runtime_error("Cannot create bounded live HUD DIB");}
  const auto old=SelectObject(dc,bitmap);
  if(!old||old==HGDI_ERROR){DeleteObject(bitmap);DeleteDC(dc);throw std::runtime_error("Cannot select live HUD DIB");}
  PatBlt(dc,0,0,static_cast<int>(region.width),static_cast<int>(region.height),BLACKNESS);
  SetViewportOrgEx(dc,-static_cast<int>(region.source_x),-static_cast<int>(region.source_y),nullptr);
  SendMessageW(control.window,WM_PRINTCLIENT,reinterpret_cast<WPARAM>(dc),PRF_CLIENT|PRF_ERASEBKGND);GdiFlush();
  const auto* source=static_cast<const unsigned char*>(pixels);
  for(UINT y=0;y<region.height;++y)for(UINT x=0;x<region.width;++x){
   const auto from=(static_cast<std::size_t>(y)*region.width+x)*4;
   const auto to=static_cast<std::size_t>(region.offset)+static_cast<std::size_t>(y)*region.pitch+x*4u;
   destination[to]=static_cast<std::byte>(source[from+2]);destination[to+1]=static_cast<std::byte>(source[from+1]);
   destination[to+2]=static_cast<std::byte>(source[from]);destination[to+3]=std::byte{255};
  }
  SelectObject(dc,old);DeleteObject(bitmap);DeleteDC(dc);++rasterizations;
 }
public:
 explicit Snapshot(HWND owner):owner_(owner){
  DWORD pid=0;wchar_t name[64]{};
  if(!owner||GetWindowThreadProcessId(owner,&pid)!=GetCurrentThreadId()||pid!=GetCurrentProcessId()||
   !GetClassNameW(owner,name,64)||std::wstring_view(name)!=L"AIBS.NativeGameWindow.1")
   throw std::invalid_argument("Live HUD requires this process's NativeWindow");
 }
 bool refresh(UINT width,UINT height){
  if(!width||!height||width>8192||height>8192)throw std::invalid_argument("Live HUD target dimensions exceed bound");
  std::array<Control,2> next{};std::size_t count=0;HWND child=nullptr;
  while((child=FindWindowExW(owner_,child,L"STATIC",nullptr))){
   // WS_VISIBLE, rather than IsWindowVisible, also admits hidden native proof
   // windows. No other process/owned popup or nested control is enumerated.
   const auto style=GetWindowLongPtrW(child,GWL_STYLE);if(!(style&WS_VISIBLE))continue;
   DWORD pid=0;if(GetParent(child)!=owner_||!GetWindowThreadProcessId(child,&pid)||pid!=GetCurrentProcessId())
    throw std::invalid_argument("Live HUD rejected a foreign control");
   if(count==next.size())throw std::invalid_argument("Live HUD exceeds two owned STATIC controls");
   auto& item=next[count++];item.window=child;item.style=style;
   item.font=reinterpret_cast<HFONT>(SendMessageW(child,WM_GETFONT,0,0));
   if(!GetWindowRect(child,&item.rect))throw std::runtime_error("Cannot locate live HUD control");
   SetLastError(ERROR_SUCCESS);
   if(!MapWindowPoints(nullptr,owner_,reinterpret_cast<POINT*>(&item.rect),2)&&GetLastError()!=ERROR_SUCCESS)
    throw std::runtime_error("Cannot locate live HUD client");
   const auto length=GetWindowTextLengthW(child);
   if(length<0||static_cast<std::size_t>(length)>maximum_text)throw std::invalid_argument("Live HUD text exceeds bound");
   item.length=GetWindowTextW(child,item.text.data(),static_cast<int>(item.text.size()));
   if(item.length!=length)throw std::runtime_error("Live HUD text changed during bounded snapshot");
  }
  bool same=count==count_&&width==width_&&height==height_;for(std::size_t n=0;same&&n<count;++n)same=controls_[n].same(next[n]);
  if(same)return false;
  std::array<Region,2> regions{};std::size_t total=0;
  for(std::size_t n=0;n<count;++n){
   const auto& r=next[n].rect;
   if(r.right<=r.left||r.bottom<=r.top||static_cast<std::int64_t>(r.right)-r.left>8192||static_cast<std::int64_t>(r.bottom)-r.top>8192)
    throw std::invalid_argument("Live HUD control dimensions exceed bound");
   const auto left=std::clamp<LONG>(r.left,0,static_cast<LONG>(width)),top=std::clamp<LONG>(r.top,0,static_cast<LONG>(height));
   const auto right=std::clamp<LONG>(r.right,0,static_cast<LONG>(width)),bottom=std::clamp<LONG>(r.bottom,0,static_cast<LONG>(height));
   if(right<=left||bottom<=top)continue;
   auto& region=regions[n];region.x=static_cast<UINT>(left);region.y=static_cast<UINT>(top);
   region.width=static_cast<UINT>(right-left);region.height=static_cast<UINT>(bottom-top);
   region.source_x=static_cast<UINT>(left-r.left);region.source_y=static_cast<UINT>(top-r.top);
   region.pitch=(region.width*4u+255u)&~255u;total=(total+511u)&~std::size_t{511u};region.offset=total;
   const auto size=static_cast<std::size_t>(region.pitch)*region.height;
   if(total>maximum_bytes||size>maximum_bytes-total)throw std::invalid_argument("Live HUD exceeds its16MiB upload slot");total+=size;
  }
  std::vector<std::byte> bytes(total);
  for(std::size_t n=0;n<count;++n)if(regions[n].width)render(next[n],regions[n],bytes);
  if(version_==std::numeric_limits<std::uint64_t>::max())throw std::overflow_error("Live HUD version exhausted");
  controls_=std::move(next);regions_=regions;count_=count;width_=width;height_=height;bytes_.swap(bytes);++version_;return true;
 }
 std::size_t count()const noexcept{return count_;}std::uint64_t version()const noexcept{return version_;}
 const Region& region(std::size_t index)const{return regions_.at(index);}
 const std::vector<std::byte>& bytes()const noexcept{return bytes_;}
};
}
