#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <windowsx.h>
#include <aibs/platform.hpp>
#include <algorithm>
#include <array>
#include <mutex>
#include <stdexcept>

namespace aibs {
struct NativeWindow::Impl {
 HWND handle = nullptr;
 HWND status = nullptr;
 HWND crosshair = nullptr;
 std::wstring status_text;
 std::wstring compact_status_text,detail_status_text;
 bool status_views=false,details_visible=false;
 // Own fitted fonts for the window lifetime. Stable handles also keep the
 // renderer's HUD raster cache from confusing a recycled GDI font identity.
 std::array<HFONT,257> fitted_status_fonts{};
 std::array<HFONT,25> compact_status_fonts{};
 WindowInput actions;
 std::uint32_t width = 0, height = 0;
 bool closing = false, minimized = false, rotating = false, active = true;
 int mouse_x = 0, mouse_y = 0;
 float yaw_delta = 0, pitch_delta = 0;
 std::array<bool, 256> keys{};
 void layout_status() noexcept {
  if (!status || !handle) return;
  RECT client{};
  if (!GetClientRect(handle, &client) || client.right <= 0 || client.bottom <= 0) return;
  const int left = std::min(12, static_cast<int>(client.right) - 1);
  const int available_width = std::max(1, static_cast<int>(client.right) - left - 12);
  HDC dc = GetDC(status);
  if (!dc) return;
  const auto stock = static_cast<HFONT>(GetStockObject(DEFAULT_GUI_FONT));
  const auto previous_font = SelectObject(dc, stock);
  int panel_width=available_width;
  const auto measure = [&](HFONT font) {
   SelectObject(dc,font);RECT measured{0,0,panel_width,0};
   DrawTextW(dc,status_text.c_str(),-1,&measured,DT_CALCRECT|DT_WORDBREAK|DT_EXPANDTABS);
   return static_cast<int>(measured.bottom-measured.top)+4;
  };
  auto selected = stock;
  const bool compact=status_views&&!details_visible;
  if(compact){
   // These are client pixels, not point sizes scaled again by monitor DPI.
   // Keep the short gameplay view legible without making a giant text overlay.
   const int pixels=std::clamp(16+std::max(0,static_cast<int>(client.bottom)-480)/75,16,24);
   auto& font=compact_status_fonts[static_cast<std::size_t>(pixels)];
   if(!font){LOGFONTW description{};if(GetObjectW(stock,sizeof(description),&description)==sizeof(description)){
    description.lfHeight=-pixels;description.lfWidth=0;font=CreateFontIndirectW(&description);
   }}
   if(font)selected=font;
   SelectObject(dc,selected);RECT natural{0,0,available_width,0};
   DrawTextW(dc,status_text.c_str(),-1,&natural,DT_CALCRECT|DT_EXPANDTABS);
   const int compact_limit=client.right>=960?std::min(available_width,static_cast<int>(client.right)*3/4):available_width;
   panel_width=std::clamp(static_cast<int>(natural.right-natural.left)+12,1,compact_limit);
  }
  int needed = measure(selected);
  // Preserve the normal font first, relieving vertical padding if necessary.
  // Only smaller viewports need fitted fonts; never shrink below 12 pixels.
  LOGFONTW description{};
  if(!compact&&needed>client.bottom&&GetObjectW(stock,sizeof(description),&description)==sizeof(description)) {
   const int maximum = std::min(256,static_cast<int>(std::abs(description.lfHeight))-1);
   for(int font_height=maximum;font_height>=12;--font_height) {
    auto& font=fitted_status_fonts[static_cast<std::size_t>(font_height)];
    if(!font){description.lfHeight=description.lfHeight<0?-font_height:font_height;font=CreateFontIndirectW(&description);}
    if(!font)continue;
    selected=font;needed=measure(font);
    if(needed<=client.bottom)break;
   }
  }
  SelectObject(dc, previous_font);
  ReleaseDC(status, dc);
  const auto old_font=reinterpret_cast<HFONT>(SendMessageW(status,WM_GETFONT,0,0));
  if(old_font!=selected)SendMessageW(status,WM_SETFONT,reinterpret_cast<WPARAM>(selected),FALSE);
  const int top = std::min(12,std::max(0,(static_cast<int>(client.bottom)-needed)/2));
  const int available_height = std::max(1,static_cast<int>(client.bottom)-2*top);
  const int panel_height = std::clamp(needed,1,available_height);
  SetWindowPos(status, nullptr, left, top, panel_width, panel_height, SWP_NOZORDER | SWP_NOACTIVATE);
  if(old_font!=selected)InvalidateRect(status,nullptr,TRUE);
 }
 void publish_status(const std::wstring& text,bool force_layout=false){
  if(status&&status_text==text){if(force_layout)layout_status();return;}
  if(!status){
   status=CreateWindowExW(0,L"STATIC",L"",WS_CHILD|WS_VISIBLE|SS_LEFT,12,12,650,120,handle,nullptr,GetModuleHandleW(nullptr),nullptr);
   if(!status)throw std::runtime_error("Could not create native status panel");
   SendMessageW(status,WM_SETFONT,reinterpret_cast<WPARAM>(GetStockObject(DEFAULT_GUI_FONT)),TRUE);
   crosshair=CreateWindowExW(0,L"STATIC",L"+",WS_CHILD|WS_VISIBLE|SS_CENTER,
    static_cast<int>(width/2)-8,static_cast<int>(height/2)-8,16,16,handle,nullptr,GetModuleHandleW(nullptr),nullptr);
  }
  SetWindowTextW(status,text.c_str());status_text=text;layout_status();
 }
 static LRESULT CALLBACK procedure(HWND window, UINT message, WPARAM wp, LPARAM lp) {
  auto* state = reinterpret_cast<Impl*>(GetWindowLongPtrW(window, GWLP_USERDATA));
  if (message == WM_NCCREATE) {
   state = static_cast<Impl*>(reinterpret_cast<CREATESTRUCTW*>(lp)->lpCreateParams);
   SetWindowLongPtrW(window, GWLP_USERDATA, reinterpret_cast<LONG_PTR>(state));
  }
  if (!state) return DefWindowProcW(window, message, wp, lp);
  switch (message) {
  case WM_CLOSE: state->closing = true; return 0;
  case WM_SIZE:
   state->minimized = wp == SIZE_MINIMIZED;
   if (!state->minimized) {
    state->width = LOWORD(lp); state->height = HIWORD(lp);
    if (state->crosshair) SetWindowPos(state->crosshair, nullptr, static_cast<int>(state->width / 2) - 8,
     static_cast<int>(state->height / 2) - 8, 16, 16, SWP_NOZORDER | SWP_NOACTIVATE);
    state->layout_status();
   }
   return 0;
  case WM_KEYDOWN:
   if ((lp & (1LL << 30)) == 0) {
    if(wp==VK_F1&&state->status_views){
     state->details_visible=!state->details_visible;
     state->publish_status(state->details_visible?state->detail_status_text:state->compact_status_text,true);
    }
    if (wp == 'E') { state->actions.interact = true; state->actions.pointer_interact = false; }
    if (wp == 'B') state->actions.build = true;
    if (wp == VK_DELETE) state->actions.dismantle = true;
    if (wp == VK_F5) state->actions.save = true;
    if (wp == VK_F9) state->actions.reload = true;
    if (wp == VK_F6) state->actions.companion_follow = true;
    if (wp == VK_F7) state->actions.companion_wait = true;
    if (wp == VK_F8) state->actions.companion_recall = true;
    if (wp == VK_SPACE) state->actions.jump = true;
    if (wp == 'V') state->actions.cycle_camera = true;
    if (wp == VK_F2) state->actions.toggle_flight = true;
    if (wp == 'Z' && state->keys[VK_CONTROL]) state->actions.undo = true;
    if (wp == 'Y' && state->keys[VK_CONTROL]) state->actions.redo = true;
   }
   if (wp < state->keys.size()) state->keys[wp] = true;
   if (wp == VK_ESCAPE) state->closing = true;
   return 0;
  case WM_KEYUP:
   if (wp < state->keys.size()) state->keys[wp] = false;
   return 0;
  case WM_ACTIVATEAPP:
   state->active = wp != 0;
   if (!wp) {
    state->keys.fill(false); state->actions = {}; state->rotating = false;
    state->yaw_delta = 0; state->pitch_delta = 0; ReleaseCapture();
   }
   return 0;
  case WM_LBUTTONDOWN:
   state->actions.interact = true; state->actions.pointer_interact = true;
   if (state->width && state->height) {
    state->actions.pointer_x = 2.0f * static_cast<float>(GET_X_LPARAM(lp)) / static_cast<float>(state->width) - 1.0f;
    state->actions.pointer_y = 1.0f - 2.0f * static_cast<float>(GET_Y_LPARAM(lp)) / static_cast<float>(state->height);
   }
   return 0;
  case WM_CTLCOLORSTATIC:
   SetTextColor(reinterpret_cast<HDC>(wp), RGB(245, 225, 190));
   SetBkColor(reinterpret_cast<HDC>(wp), RGB(8, 10, 16));
   return reinterpret_cast<LRESULT>(GetStockObject(BLACK_BRUSH));
  case WM_RBUTTONDOWN:
   state->rotating = true; state->mouse_x = GET_X_LPARAM(lp); state->mouse_y = GET_Y_LPARAM(lp); SetCapture(window); return 0;
  case WM_RBUTTONUP: state->rotating = false; ReleaseCapture(); return 0;
  case WM_CAPTURECHANGED: state->rotating = false; return 0;
  case WM_MOUSEMOVE:
   if (state->rotating) {
    const int x = GET_X_LPARAM(lp), y = GET_Y_LPARAM(lp);
    state->yaw_delta += static_cast<float>(x - state->mouse_x) * 0.004f;
    state->pitch_delta -= static_cast<float>(y - state->mouse_y) * 0.004f;
    state->mouse_x = x; state->mouse_y = y;
   }
   return 0;
  default: return DefWindowProcW(window, message, wp, lp);
  }
 }
};

NativeWindow::NativeWindow(std::uint32_t width, std::uint32_t height, const std::wstring& title, bool visible)
 : impl_(std::make_unique<Impl>()) {
 if (width == 0 || height == 0 || width > 8192 || height > 8192) throw std::invalid_argument("Window dimensions must be 1..8192");
 static std::once_flag registration;
 std::call_once(registration, [] {
  WNDCLASSEXW type{}; type.cbSize = sizeof(type); type.lpfnWndProc = Impl::procedure;
  type.hInstance = GetModuleHandleW(nullptr); type.hCursor = LoadCursorW(nullptr, MAKEINTRESOURCEW(32512)); type.lpszClassName = L"AIBS.NativeGameWindow.1";
  if (!RegisterClassExW(&type) && GetLastError() != ERROR_CLASS_ALREADY_EXISTS) throw std::runtime_error("Could not register native window class");
 });
 impl_->width = width; impl_->height = height;
 RECT rectangle{0, 0, static_cast<LONG>(width), static_cast<LONG>(height)};
 if (!AdjustWindowRect(&rectangle, WS_OVERLAPPEDWINDOW, FALSE)) throw std::runtime_error("Could not size native window");
 impl_->handle = CreateWindowExW(0, L"AIBS.NativeGameWindow.1", title.c_str(), WS_OVERLAPPEDWINDOW,
  CW_USEDEFAULT, CW_USEDEFAULT, rectangle.right - rectangle.left, rectangle.bottom - rectangle.top,
  nullptr, nullptr, GetModuleHandleW(nullptr), impl_.get());
 if (!impl_->handle) throw std::runtime_error("Could not create native PC window");
 if (visible) { ShowWindow(impl_->handle, SW_SHOW); UpdateWindow(impl_->handle); }
}
NativeWindow::~NativeWindow() {
 if (impl_->handle) DestroyWindow(impl_->handle);
 // Destroy STATIC children before releasing their owned fonts.
 for(const auto font:impl_->fitted_status_fonts)if(font)DeleteObject(font);
 for(const auto font:impl_->compact_status_fonts)if(font)DeleteObject(font);
}
bool NativeWindow::poll() {
 MSG message{};
 while (PeekMessageW(&message, nullptr, 0, 0, PM_REMOVE)) {
  if (message.message == WM_QUIT) impl_->closing = true;
  TranslateMessage(&message); DispatchMessageW(&message);
 }
 return !impl_->closing;
}
WindowInput NativeWindow::input() {
 const auto& keys = impl_->keys;
 WindowInput input = impl_->actions;
 impl_->actions = {};
 input.active = impl_->active;
 input.forward = static_cast<float>(keys['W'] || keys[VK_UP]) - static_cast<float>(keys['S'] || keys[VK_DOWN]);
 input.right = static_cast<float>(keys['D'] || keys[VK_RIGHT]) - static_cast<float>(keys['A'] || keys[VK_LEFT]);
 input.up = static_cast<float>(keys[VK_SPACE]) - static_cast<float>(keys[VK_CONTROL]);
 if (keys[VK_CONTROL] && (keys['Z'] || keys['Y'])) input.up = 0;
 input.sprint = keys[VK_SHIFT]; input.yaw_delta = impl_->yaw_delta; input.pitch_delta = impl_->pitch_delta;
 impl_->yaw_delta = 0; impl_->pitch_delta = 0;
 return input;
}
std::uint32_t NativeWindow::width() const noexcept { return impl_->width; }
std::uint32_t NativeWindow::height() const noexcept { return impl_->height; }
bool NativeWindow::minimized() const noexcept { return impl_->minimized; }
void* NativeWindow::native_handle() const noexcept { return impl_->handle; }
void NativeWindow::set_size(std::uint32_t width, std::uint32_t height) {
 if (!width || !height || width > 8192 || height > 8192) throw std::invalid_argument("Invalid window resize dimensions");
 RECT rectangle{0, 0, static_cast<LONG>(width), static_cast<LONG>(height)};
 AdjustWindowRect(&rectangle, WS_OVERLAPPEDWINDOW, FALSE);
 if (!SetWindowPos(impl_->handle, nullptr, 0, 0, rectangle.right - rectangle.left, rectangle.bottom - rectangle.top, SWP_NOMOVE | SWP_NOZORDER | SWP_NOACTIVATE))
  throw std::runtime_error("Could not resize native window");
}
void NativeWindow::minimize() { ShowWindow(impl_->handle, SW_MINIMIZE); }
void NativeWindow::restore(bool visible) { ShowWindow(impl_->handle, SW_RESTORE); if (!visible) ShowWindow(impl_->handle, SW_HIDE); }
void NativeWindow::set_status(const std::wstring& text) {
 const bool changed_mode=impl_->status_views;
 impl_->status_views=false;impl_->details_visible=false;
 impl_->publish_status(text,changed_mode);
}
void NativeWindow::set_status_views(const std::wstring& compact,const std::wstring& details){
 const bool changed_mode=!impl_->status_views;
 if(changed_mode)impl_->details_visible=false;
 impl_->compact_status_text=compact;impl_->detail_status_text=details;impl_->status_views=true;
 impl_->publish_status(impl_->details_visible?impl_->detail_status_text:impl_->compact_status_text,changed_mode);
}
}
