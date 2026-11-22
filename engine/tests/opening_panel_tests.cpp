#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <aibs/render.hpp>
#include <aibs/opening_inspections.hpp>
#include <algorithm>
#include <array>
#include <filesystem>
#include <fstream>
#include <iostream>
void require(bool value,const char* message){if(!value)throw std::runtime_error(message);}
#include "opening_inspection_panel.inl"
unsigned checks=0;
void check(bool value,const char* message){++checks;require(value,message);}
int main(){try{
 using namespace aibs;
 NativeWindow native(1280,800,L"Owned reading presentation test",false);
 const auto owner=static_cast<HWND>(native.native_handle());
 OpeningInspection entry;entry.fixture_id=new_uuid();entry.title="A small beginning";
 entry.text="Adam's memory gives BS room to look around. This is authored test text.";
 entry.source="Echos Within, XML paragraph 682. Authored adaptation, not an Adam quotation.";
 OpeningInspectionPanel panel(owner);panel.show(entry);
 check(panel.visible()&&!panel.source_visible(),"Story view must open first");
 const auto initial=panel.body_text();
 check(initial.find(L"Adam's memory")!=std::wstring::npos,"Story wording preserved");
 check(initial.find(L"XML paragraph")==std::wstring::npos,"Technical provenance must not dominate story view");
 check(panel.source_attribution()==L"Echos Within, XML paragraph 682. Authored adaptation, not an Adam quotation.","Exact source retained");
 const auto body=panel.body_handle();const auto source=panel.source_handle();
 check(IsWindow(source)&&GetParent(source)==panel.native_handle(),"Source control belongs to same reading panel");
 check(GetWindow(panel.native_handle(),GW_OWNER)==owner,"Exact native game owns reading window");
 LOGFONTW font{};const auto handle=reinterpret_cast<HFONT>(SendMessageW(body,WM_GETFONT,0,0));
 check(GetObjectW(handle,static_cast<int>(sizeof(font)),&font)==static_cast<int>(sizeof(font))&&-font.lfHeight>=20,"Actual edit uses larger reading font");
 check((GetWindowLongPtrW(body,GWL_STYLE)&ES_READONLY)!=0,"Story stays read only");
 SendMessageW(body,WM_CHAR,'X',0);check(panel.body_text()==initial,"Typing cannot edit memory");
 SendMessageW(body,WM_KEYDOWN,VK_TAB,0);check(GetFocus()==source,"Tab reaches source control");
 SendMessageW(source,WM_KEYDOWN,VK_TAB,0);check(GetFocus()==panel.continue_handle(),"Tab reaches Continue");
 SendMessageW(panel.continue_handle(),WM_KEYDOWN,VK_TAB,0);check(GetFocus()==body,"Tab cycles back to story");
 SendMessageW(source,BM_CLICK,0,0);
 check(panel.visible()&&panel.source_visible(),"Source disclosure does not close reading");
 check(panel.body_text().find(panel.source_attribution())!=std::wstring::npos,"Actual source view displays exact attribution");
 SendMessageW(source,WM_KEYDOWN,VK_RETURN,0);
 check(!panel.source_visible()&&panel.body_text()==initial,"Return restores same story");
 const auto file=std::filesystem::temp_directory_path()/("aibs-reading-"+new_uuid()+".bmp");
 check(panel.capture_body(file),"Actual bright glyphs rendered on dark reading surface");
 std::ifstream input(file,std::ios::binary);BITMAPFILEHEADER header{};BITMAPINFOHEADER info{};
 input.read(reinterpret_cast<char*>(&header),sizeof(header));input.read(reinterpret_cast<char*>(&info),sizeof(info));
 check(input.good()&&header.bfType==0x4d42&&info.biWidth>400&&info.biHeight<0,"Actual reading image has bounded valid dimensions");
 std::vector<unsigned char> pixels(static_cast<std::size_t>(info.biWidth)*static_cast<std::size_t>(-info.biHeight)*4);
 input.read(reinterpret_cast<char*>(pixels.data()),static_cast<std::streamsize>(pixels.size()));check(input.good(),"Complete actual GDI pixels retained");
 std::size_t dark=0,light=0;for(std::size_t i=0;i<pixels.size();i+=4){dark+=pixels[i]<60&&pixels[i+1]<60&&pixels[i+2]<60;light+=pixels[i]>150&&pixels[i+1]>150&&pixels[i+2]>150;}
 check(dark>pixels.size()/8&&light>100,"Reading background and visible light glyphs are distinct");
 const auto bottom=(static_cast<std::size_t>(-info.biHeight-10)*static_cast<std::size_t>(info.biWidth)+static_cast<std::size_t>(info.biWidth/2))*4;
 check(pixels[bottom]==33&&pixels[bottom+1]==29&&pixels[bottom+2]==28,"Unused recorded area keeps the same charcoal background");
 RECT suggested{100,100,1100,800};SendMessageW(panel.native_handle(),WM_DPICHANGED,MAKELONG(144,144),reinterpret_cast<LPARAM>(&suggested));
 const auto scaled_font=reinterpret_cast<HFONT>(SendMessageW(body,WM_GETFONT,0,0));
 check(GetObjectW(scaled_font,static_cast<int>(sizeof(font)),&font)==static_cast<int>(sizeof(font))&&font.lfHeight==-30,"Owned DPI-change message scales reading text");
 check(panel.body_text()==initial,"DPI layout never changes story wording");
 SendMessageW(source,BM_CLICK,0,0);SendMessageW(source,WM_KEYDOWN,VK_ESCAPE,0);
 check(!panel.visible()&&IsWindow(owner),"Escape from source closes only optional reading");
 panel.show(entry);check(!panel.source_visible()&&panel.body_text()==initial,"Reopen resets ephemeral source view");
 auto next=entry;next.fixture_id=new_uuid();next.text="A different authored memory.";next.source="Independent test provenance.";panel.show(next);
 check(panel.body_text().find(L"different authored memory")!=std::wstring::npos&&panel.source_attribution()==L"Independent test provenance.","A new selection never retains old story/source");
 SendMessageW(panel.continue_handle(),BM_CLICK,0,0);check(!panel.visible(),"Continue still closes reading");
 std::cout<<"Opening reading presentation "<<checks<<" checks passed; actual owned Win32 controls and GDI pixels\n";return 0;
}catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}}
