#pragma once
// Recorder-only composition. WM_PRINTCLIENT renders ONLY current-process child
// controls into a private DIB. No desktop/window DC, screen BitBlt or foreign HWND.
#include <aibs/render.hpp>
#include <algorithm>
#include <cstdint>
#include <stdexcept>
namespace aibs::recording {
class OwnedHudComposer {
 HWND owner_=nullptr;HDC dc_=nullptr;HBITMAP bitmap_=nullptr;HGDIOBJ previous_=nullptr;unsigned char* pixels_=nullptr;
 int width_=0,height_=0;std::uint64_t controls_=0,glyph_pixels_=0;
 void reset()noexcept{if(dc_&&previous_)SelectObject(dc_,previous_);if(bitmap_)DeleteObject(bitmap_);if(dc_)DeleteDC(dc_);dc_=nullptr;bitmap_=nullptr;previous_=nullptr;pixels_=nullptr;width_=height_=0;}
 void ensure(int width,int height){if(width_==width&&height_==height)return;reset();if(width<=0||height<=0||width>3840||height>640||static_cast<std::size_t>(width)*height*4>4u*1024u*1024u)throw std::invalid_argument("Owned recording HUD exceeds its4MiB diagnostic bound");dc_=CreateCompatibleDC(nullptr);BITMAPINFO info{};info.bmiHeader.biSize=sizeof(BITMAPINFOHEADER);info.bmiHeader.biWidth=width;info.bmiHeader.biHeight=-height;info.bmiHeader.biPlanes=1;info.bmiHeader.biBitCount=32;void* ptr=nullptr;bitmap_=CreateDIBSection(nullptr,&info,DIB_RGB_COLORS,&ptr,nullptr,0);if(!dc_||!bitmap_||!ptr){reset();throw std::runtime_error("Cannot allocate private recording HUD");}previous_=SelectObject(dc_,bitmap_);pixels_=static_cast<unsigned char*>(ptr);width_=width;height_=height;}
 bool owns_control(HWND control)const noexcept{
  // GA_ROOTOWNER follows GetParent, which omits an owned OVERLAPPED
  // top-level window's owner. Follow explicit GW_OWNER links instead.
  if(!control||(GetWindowLongPtrW(control,GWL_STYLE)&WS_CHILD)==0)return false;
  HWND root=GetAncestor(control,GA_ROOT);
  for(unsigned hops=0;root&&hops<16;++hops){DWORD pid=0;if(!GetWindowThreadProcessId(root,&pid)||pid!=GetCurrentProcessId())return false;if(root==owner_)return true;root=GetWindow(root,GW_OWNER);}
  return false;
 }
public:
 explicit OwnedHudComposer(HWND owner):owner_(owner){DWORD pid=0;if(!owner||!GetWindowThreadProcessId(owner,&pid)||pid!=GetCurrentProcessId())throw std::invalid_argument("Recording HUD owner must belong to this process");}
 ~OwnedHudComposer(){reset();}OwnedHudComposer(const OwnedHudComposer&)=delete;OwnedHudComposer& operator=(const OwnedHudComposer&)=delete;
 void composite(CapturedFrame& frame,HWND control,int x,int y){DWORD pid=0;wchar_t cls[32]{};if(!control||!GetWindowThreadProcessId(control,&pid)||pid!=GetCurrentProcessId()||!owns_control(control)||!GetClassNameW(control,cls,32)||(std::wstring_view(cls)!=L"Static"&&std::wstring_view(cls)!=L"Edit"))throw std::invalid_argument("Recorder rejected a foreign or unsupported control");RECT bounds{};if(!GetClientRect(control,&bounds)||bounds.left||bounds.top||bounds.right<=0||bounds.bottom<=0)throw std::invalid_argument("Recording HUD control has no bounded client area");if(frame.width==0||frame.height==0||frame.width>3840||frame.height>2160||frame.bgra.size()!=static_cast<std::size_t>(frame.width)*frame.height*4||x<0||y<0||static_cast<std::uint64_t>(x)+bounds.right>frame.width||static_cast<std::uint64_t>(y)+bounds.bottom>frame.height)throw std::invalid_argument("Recording HUD rectangle escapes owned frame");ensure(bounds.right,bounds.bottom);PatBlt(dc_,0,0,width_,height_,WHITENESS);SendMessageW(control,WM_PRINTCLIENT,reinterpret_cast<WPARAM>(dc_),PRF_CLIENT|PRF_ERASEBKGND);GdiFlush();std::uint64_t ink=0;for(int row=0;row<height_;++row)for(int column=0;column<width_;++column){const auto src=(static_cast<std::size_t>(row)*width_+column)*4;const auto dst=((static_cast<std::size_t>(row)+y)*frame.width+column+x)*4;for(std::size_t c=0;c<3;++c)frame.bgra[dst+c]=static_cast<std::byte>(pixels_[src+c]);frame.bgra[dst+3]=std::byte{255};ink+=pixels_[src]<180&&pixels_[src+1]<180&&pixels_[src+2]<180;}++controls_;glyph_pixels_+=ink;}
 void release()noexcept{reset();}
 std::size_t resident_bytes()const noexcept{return static_cast<std::size_t>(width_)*height_*4;}
 std::uint64_t controls_composed()const noexcept{return controls_;}std::uint64_t glyph_pixels()const noexcept{return glyph_pixels_;}
};
}
