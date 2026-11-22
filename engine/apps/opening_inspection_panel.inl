// Private owned Win32 presentation. No world/player/store reference is retained.
// The caller includes visible() in every game/animation/media pause condition.
class OpeningInspectionPanel {
 HWND parent_=nullptr,window_=nullptr,body_=nullptr,continue_=nullptr,source_button_=nullptr;
 WNDPROC body_previous_=nullptr,continue_previous_=nullptr,source_previous_=nullptr;
 HFONT reading_font_=nullptr,button_font_=nullptr;HBRUSH background_=nullptr;
 UINT dpi_=96;bool source_visible_=false,presentation_=true,proof_open_=false;std::wstring story_,source_;
 static constexpr wchar_t class_name[]=L"AIBS.OpeningInspectionPanel.2";
 static constexpr int continue_id=0x7b10,source_id=0x7b11;
 static constexpr COLORREF background_color=RGB(28,29,33),text_color=RGB(239,232,216);
 int scaled(int value)const noexcept{return MulDiv(value,static_cast<int>(dpi_),96);}
 static std::wstring wide_text(const std::string& text){
  if(text.empty())return {};const int n=MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,text.data(),static_cast<int>(text.size()),nullptr,0);if(n<=0)throw std::invalid_argument("Opening panel UTF8 conversion failed");std::wstring out(static_cast<std::size_t>(n),L'\0');if(MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,text.data(),static_cast<int>(text.size()),out.data(),n)!=n)throw std::invalid_argument("Opening panel UTF8 conversion changed");return out;
 }
 bool fonts()noexcept{
  const auto reading=CreateFontW(-scaled(20),0,0,0,FW_NORMAL,FALSE,FALSE,FALSE,DEFAULT_CHARSET,OUT_DEFAULT_PRECIS,CLIP_DEFAULT_PRECIS,CLEARTYPE_QUALITY,DEFAULT_PITCH|FF_DONTCARE,L"Segoe UI");
  const auto button=CreateFontW(-scaled(18),0,0,0,FW_NORMAL,FALSE,FALSE,FALSE,DEFAULT_CHARSET,OUT_DEFAULT_PRECIS,CLIP_DEFAULT_PRECIS,CLEARTYPE_QUALITY,DEFAULT_PITCH|FF_DONTCARE,L"Segoe UI");
  if(!reading||!button){if(reading)DeleteObject(reading);if(button)DeleteObject(button);return false;}
  SendMessageW(body_,WM_SETFONT,reinterpret_cast<WPARAM>(reading),TRUE);SendMessageW(continue_,WM_SETFONT,reinterpret_cast<WPARAM>(button),TRUE);SendMessageW(source_button_,WM_SETFONT,reinterpret_cast<WPARAM>(button),TRUE);
  if(reading_font_)DeleteObject(reading_font_);if(button_font_)DeleteObject(button_font_);reading_font_=reading;button_font_=button;return true;
 }
 void layout()noexcept{
  if(!body_)return;RECT bounds{};if(!GetClientRect(window_,&bounds))return;
  const int width=static_cast<int>(bounds.right),height=static_cast<int>(bounds.bottom);
  const int pad=scaled(20),gap=scaled(12),button_height=scaled(36),available=std::max(1,width-2*pad);
  const int continue_width=std::max(1,std::min(scaled(132),(available-gap)/2));const int source_width=std::max(1,std::min(scaled(180),available-continue_width-gap));
  MoveWindow(body_,pad,pad,available,std::max(1,height-3*pad-button_height),TRUE);
  const int bottom=std::max(pad,height-pad-button_height);
  MoveWindow(source_button_,pad,bottom,source_width,button_height,TRUE);MoveWindow(continue_,std::max(pad,width-pad-continue_width),bottom,continue_width,button_height,TRUE);
 }
 void toggle_source(){
  source_visible_=!source_visible_;
  const auto text=source_visible_?L"Memory source\r\n\r\n"+source_+L"\r\n\r\nReturn to memory to continue reading.":story_;
  SetWindowTextW(body_,text.c_str());SetWindowTextW(source_button_,source_visible_?L"Back to memory":L"Memory source");SendMessageW(body_,EM_SETSEL,0,0);SendMessageW(body_,EM_SCROLLCARET,0,0);
 }
 static LRESULT CALLBACK child_proc(HWND window,UINT message,WPARAM wp,LPARAM lp){
  auto* self=reinterpret_cast<OpeningInspectionPanel*>(GetWindowLongPtrW(GetParent(window),GWLP_USERDATA));if(!self)return DefWindowProcW(window,message,wp,lp);
  // EDIT does not reliably erase its unused client area when WM_PRINTCLIENT
  // targets an offscreen recorder. Fill the complete owned surface first.
  if((message==WM_PRINTCLIENT||message==WM_ERASEBKGND)&&window==self->body_){RECT bounds{};GetClientRect(window,&bounds);FillRect(reinterpret_cast<HDC>(wp),&bounds,self->background_);if(message==WM_ERASEBKGND)return 1;}
  // Real releases from every child must reach the game's held-key state.
  // F9 is the only forwarded keydown. Reading never admits game actions.
  if(message==WM_KEYUP||message==WM_SYSKEYUP)SendMessageW(self->parent_,message,wp,lp);
  if(message==WM_KEYDOWN&&wp==VK_F9){SendMessageW(self->parent_,message,wp,lp);return 0;}
  if(message==WM_KEYDOWN&&wp==VK_ESCAPE){self->hide();return 0;}
  if(message==WM_KEYDOWN&&wp==VK_TAB){
   const std::array<HWND,3> order{self->body_,self->source_button_,self->continue_};std::size_t at=0;while(at<order.size()&&order[at]!=window)++at;
   const bool reverse=(GetKeyState(VK_SHIFT)&0x8000)!=0;if(self->presentation_)SetFocus(order[(at+(reverse?2u:1u))%order.size()]);return 0;
  }
  if(message==WM_KEYDOWN&&wp==VK_RETURN){if(window==self->continue_){self->hide();return 0;}if(window==self->source_button_){self->toggle_source();return 0;}}
  const auto previous=window==self->body_?self->body_previous_:window==self->source_button_?self->source_previous_:self->continue_previous_;
  return CallWindowProcW(previous,window,message,wp,lp);
 }
 static LRESULT CALLBACK procedure(HWND window,UINT message,WPARAM wp,LPARAM lp){
  auto* self=reinterpret_cast<OpeningInspectionPanel*>(GetWindowLongPtrW(window,GWLP_USERDATA));
  if(message==WM_NCCREATE){const auto* create=reinterpret_cast<CREATESTRUCTW*>(lp);self=static_cast<OpeningInspectionPanel*>(create->lpCreateParams);SetWindowLongPtrW(window,GWLP_USERDATA,reinterpret_cast<LONG_PTR>(self));}
  if(!self)return DefWindowProcW(window,message,wp,lp);
  if(message==WM_KEYUP||message==WM_SYSKEYUP)SendMessageW(self->parent_,message,wp,lp);
  if(message==WM_KEYDOWN&&wp==VK_F9){SendMessageW(self->parent_,message,wp,lp);return 0;}
  if(message==WM_CLOSE||(message==WM_KEYDOWN&&wp==VK_ESCAPE)){self->hide();return 0;}
  if(message==WM_COMMAND&&HIWORD(wp)==BN_CLICKED){
   if(LOWORD(wp)==continue_id&&reinterpret_cast<HWND>(lp)==self->continue_){self->hide();return 0;}
   if(LOWORD(wp)==source_id&&reinterpret_cast<HWND>(lp)==self->source_button_){self->toggle_source();return 0;}
  }
  if((message==WM_CTLCOLORSTATIC||message==WM_CTLCOLOREDIT)&&reinterpret_cast<HWND>(lp)==self->body_){const auto dc=reinterpret_cast<HDC>(wp);SetTextColor(dc,text_color);SetBkColor(dc,background_color);return reinterpret_cast<LRESULT>(self->background_);}
  if(message==WM_ERASEBKGND&&self->background_){RECT rect{};GetClientRect(window,&rect);FillRect(reinterpret_cast<HDC>(wp),&rect,self->background_);return 1;}
  if(message==WM_SIZE){self->layout();return 0;}
  if(message==WM_GETMINMAXINFO){auto* limits=reinterpret_cast<MINMAXINFO*>(lp);limits->ptMinTrackSize={560,360};limits->ptMaxTrackSize={1100,760};return 0;}
  if(message==WM_DPICHANGED){self->dpi_=std::max(96u,static_cast<UINT>(HIWORD(wp)));(void)self->fonts();const auto* rect=reinterpret_cast<RECT*>(lp);if(rect)SetWindowPos(window,nullptr,rect->left,rect->top,std::min(1100,static_cast<int>(rect->right-rect->left)),std::min(760,static_cast<int>(rect->bottom-rect->top)),SWP_NOZORDER|SWP_NOACTIVATE);self->layout();return 0;}
  return DefWindowProcW(window,message,wp,lp);
 }
 void create(){
  if(window_)return;background_=CreateSolidBrush(background_color);if(!background_)throw std::runtime_error("Cannot create reading background");
  dpi_=std::max(96u,GetDpiForWindow(parent_));WNDCLASSEXW cls{};cls.cbSize=sizeof(cls);cls.lpfnWndProc=procedure;cls.hInstance=GetModuleHandleW(nullptr);cls.hCursor=LoadCursorW(nullptr,MAKEINTRESOURCEW(32512));cls.hbrBackground=reinterpret_cast<HBRUSH>(GetStockObject(BLACK_BRUSH));cls.lpszClassName=class_name;
  if(!RegisterClassExW(&cls)&&GetLastError()!=ERROR_CLASS_ALREADY_EXISTS)throw std::runtime_error("Cannot register opening inspection panel");
  RECT owner{};GetWindowRect(parent_,&owner);int width=std::min(1100,scaled(820)),height=std::min(760,scaled(520));
  int x=owner.left+((owner.right-owner.left)-width)/2,y=owner.top+((owner.bottom-owner.top)-height)/2;MONITORINFO monitor{};monitor.cbSize=sizeof(monitor);
  if(GetMonitorInfoW(MonitorFromWindow(parent_,MONITOR_DEFAULTTONEAREST),&monitor)){width=std::min(width,std::max(320,static_cast<int>(monitor.rcWork.right-monitor.rcWork.left)-16));height=std::min(height,std::max(240,static_cast<int>(monitor.rcWork.bottom-monitor.rcWork.top)-16));x=std::max(static_cast<int>(monitor.rcWork.left)+8,std::min(x,static_cast<int>(monitor.rcWork.right)-width-8));y=std::max(static_cast<int>(monitor.rcWork.top)+8,std::min(y,static_cast<int>(monitor.rcWork.bottom)-height-8));}
  window_=CreateWindowExW(WS_EX_TOOLWINDOW,class_name,L"First Boot",WS_OVERLAPPED|WS_CAPTION|WS_SYSMENU|WS_THICKFRAME,x,y,width,height,parent_,nullptr,cls.hInstance,this);if(!window_)throw std::runtime_error("Cannot create opening inspection panel");
  body_=CreateWindowExW(0,L"EDIT",L"",WS_CHILD|WS_VISIBLE|WS_VSCROLL|ES_MULTILINE|ES_AUTOVSCROLL|ES_READONLY,0,0,1,1,window_,nullptr,cls.hInstance,nullptr);
  source_button_=CreateWindowExW(0,L"BUTTON",L"Memory source",WS_CHILD|WS_VISIBLE|WS_TABSTOP,0,0,1,1,window_,reinterpret_cast<HMENU>(static_cast<INT_PTR>(source_id)),cls.hInstance,nullptr);
  continue_=CreateWindowExW(0,L"BUTTON",L"Continue",WS_CHILD|WS_VISIBLE|WS_TABSTOP|BS_DEFPUSHBUTTON,0,0,1,1,window_,reinterpret_cast<HMENU>(static_cast<INT_PTR>(continue_id)),cls.hInstance,nullptr);
  if(!body_||!continue_||!source_button_){DestroyWindow(window_);window_=body_=continue_=source_button_=nullptr;throw std::runtime_error("Cannot create opening inspection controls");}
  SendMessageW(body_,EM_SETLIMITTEXT,8192,0);if(!fonts())throw std::runtime_error("Cannot create readable inspection fonts");
  body_previous_=reinterpret_cast<WNDPROC>(SetWindowLongPtrW(body_,GWLP_WNDPROC,reinterpret_cast<LONG_PTR>(child_proc)));
  source_previous_=reinterpret_cast<WNDPROC>(SetWindowLongPtrW(source_button_,GWLP_WNDPROC,reinterpret_cast<LONG_PTR>(child_proc)));
  continue_previous_=reinterpret_cast<WNDPROC>(SetWindowLongPtrW(continue_,GWLP_WNDPROC,reinterpret_cast<LONG_PTR>(child_proc)));layout();
 }
public:
 explicit OpeningInspectionPanel(HWND parent,bool presentation=true):parent_(parent),presentation_(presentation){}
 ~OpeningInspectionPanel(){if(window_)DestroyWindow(window_);if(reading_font_)DeleteObject(reading_font_);if(button_font_)DeleteObject(button_font_);if(background_)DeleteObject(background_);}
 OpeningInspectionPanel(const OpeningInspectionPanel&)=delete;OpeningInspectionPanel& operator=(const OpeningInspectionPanel&)=delete;
 void show(const aibs::OpeningInspection& inspection){
  require(inspection.title.size()<=256&&inspection.text.size()<=2048&&inspection.source.size()<=512,"Reading presentation exceeds bounded inspection fields");
  const auto title=wide_text(inspection.title);const auto text=wide_text(inspection.text);const auto source=wide_text(inspection.source);create();
  story_=title+L"\r\n\r\n"+text+L"\r\n\r\nTake your time. Continue when you are ready.";
  if(inspection.source.find("Echos Within")!=std::string::npos)story_+=L"\r\n\r\nInspired by Echos Within. Memory source has the reference and adaptation notes.";
  source_=source;source_visible_=false;SetWindowTextW(window_,title.c_str());SetWindowTextW(body_,story_.c_str());SetWindowTextW(source_button_,L"Memory source");SendMessageW(body_,EM_SETSEL,0,0);SendMessageW(body_,EM_SCROLLCARET,0,0);
  proof_open_=true;if(presentation_){ShowWindow(window_,SW_SHOW);SetFocus(body_);}
 }
 void hide()noexcept{source_visible_=proof_open_=false;if(window_)ShowWindow(window_,SW_HIDE);if(presentation_&&parent_&&IsWindow(parent_))SetFocus(parent_);}
 // In the explicit offscreen proof, reading is logically open while its
 // actual Win32 presentation remains hidden. Ordinary UI uses actual visibility.
 bool visible()const noexcept{return window_&&(presentation_?IsWindowVisible(window_)!=FALSE:proof_open_);}
 bool source_visible()const noexcept{return visible()&&source_visible_;}
 HWND native_handle()const noexcept{return window_;}HWND body_handle()const noexcept{return body_;}HWND continue_handle()const noexcept{return continue_;}HWND source_handle()const noexcept{return source_button_;}
 const std::wstring& source_attribution()const noexcept{return source_;}
 std::wstring body_text()const{
  const int size=GetWindowTextLengthW(body_);require(size>=0&&size<=8192,"Opening text readback exceeds its bound");std::wstring out(static_cast<std::size_t>(size)+1,L'\0');out.resize(static_cast<std::size_t>(GetWindowTextW(body_,out.data(),static_cast<int>(out.size()))));return out;
 }
 bool capture_body(const std::filesystem::path& path)const{
  RECT bounds{};require(GetClientRect(body_,&bounds)&&bounds.right>0&&bounds.bottom>0&&bounds.right<=2048&&bounds.bottom<=1024,"Opening glyph capture outside its bound");
  const auto source=GetDC(body_);const auto target=source?CreateCompatibleDC(source):nullptr;require(source&&target,"Opening glyph readback DC unavailable");
  BITMAPINFO info{};info.bmiHeader.biSize=sizeof(BITMAPINFOHEADER);info.bmiHeader.biWidth=bounds.right;info.bmiHeader.biHeight=-bounds.bottom;info.bmiHeader.biPlanes=1;info.bmiHeader.biBitCount=32;info.bmiHeader.biCompression=BI_RGB;
  void* pixels=nullptr;const auto bitmap=CreateDIBSection(source,&info,DIB_RGB_COLORS,&pixels,nullptr,0);require(bitmap&&pixels,"Cannot create opening glyph readback bitmap");
  const auto old=SelectObject(target,bitmap);PatBlt(target,0,0,bounds.right,bounds.bottom,BLACKNESS);SendMessageW(body_,WM_PRINTCLIENT,reinterpret_cast<WPARAM>(target),PRF_CLIENT|PRF_ERASEBKGND);
  const auto* rgba=static_cast<const unsigned char*>(pixels);std::size_t ink=0;
  for(int y=5;y<bounds.bottom-5;++y)for(int x=5;x<bounds.right-20;++x){const auto i=(static_cast<std::size_t>(y)*static_cast<std::size_t>(bounds.right)+static_cast<std::size_t>(x))*4;ink+=rgba[i]>150&&rgba[i+1]>150&&rgba[i+2]>150;}
  BITMAPFILEHEADER header{};header.bfType=0x4d42;header.bfOffBits=sizeof(header)+sizeof(BITMAPINFOHEADER);header.bfSize=header.bfOffBits+static_cast<DWORD>(bounds.right*bounds.bottom*4);
  std::ofstream file(path,std::ios::binary);file.write(reinterpret_cast<const char*>(&header),sizeof(header));file.write(reinterpret_cast<const char*>(&info.bmiHeader),sizeof(info.bmiHeader));file.write(static_cast<const char*>(pixels),static_cast<std::streamsize>(bounds.right)*bounds.bottom*4);const bool good=file.good();
  SelectObject(target,old);DeleteObject(bitmap);DeleteDC(target);ReleaseDC(body_,source);return good&&ink>100;
 }
};
