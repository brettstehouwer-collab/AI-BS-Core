#pragma once
#include <cstdint>
#include <memory>
#include <string>

namespace aibs {
struct WindowInput {
 float forward = 0, right = 0, up = 0;
 float yaw_delta = 0, pitch_delta = 0;
 bool sprint = false;
 bool interact = false, build = false, dismantle = false;
 bool undo = false, redo = false, save = false, reload = false;
 bool pointer_interact = false;
 float pointer_x = 0, pointer_y = 0;
 bool jump = false, cycle_camera = false, toggle_flight = false;
 bool companion_follow=false,companion_wait=false,companion_recall=false;
 bool active = true;
};
class NativeWindow {
public:
 NativeWindow(std::uint32_t width, std::uint32_t height, const std::wstring& title, bool visible = true);
 ~NativeWindow();
 NativeWindow(const NativeWindow&) = delete;
 NativeWindow& operator=(const NativeWindow&) = delete;
 bool poll();
 WindowInput input();
 std::uint32_t width() const noexcept;
 std::uint32_t height() const noexcept;
 bool minimized() const noexcept;
 void* native_handle() const noexcept;
 void set_size(std::uint32_t width, std::uint32_t height);
 void minimize();
 void restore(bool visible = true);
 void set_status(const std::wstring& text);
 // Compact by default; F1 switches between these views without gameplay input.
 // The original set_status API remains a single, fitted full-text view.
 void set_status_views(const std::wstring& compact,const std::wstring& details);
private:
 struct Impl;
 std::unique_ptr<Impl> impl_;
};
}
