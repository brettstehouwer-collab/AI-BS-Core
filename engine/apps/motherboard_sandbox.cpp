#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <aibs/render.hpp>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>
int run_native_world(int argc, wchar_t** argv);
int run_durable_world(int argc, wchar_t** argv);
int run_obstacle_course(int argc, wchar_t** argv);
int run_asset_showcase(int argc, wchar_t** argv);

namespace {
std::string escaped(const std::string& text) {
 std::string result;
 for (const char ch : text) {
  if (ch == '\\' || ch == '"') { result += '\\'; result += ch; }
  else if (ch == '\n') result += "\\n";
  else if (static_cast<unsigned char>(ch) >= 32) result += ch;
 }
 return result;
}
std::string timestamp() {
 SYSTEMTIME time{}; GetSystemTime(&time); std::ostringstream text;
 text << std::setfill('0') << std::setw(4) << time.wYear << '-' << std::setw(2) << time.wMonth << '-' << std::setw(2) << time.wDay
      << 'T' << std::setw(2) << time.wHour << ':' << std::setw(2) << time.wMinute << ':' << std::setw(2) << time.wSecond << "+00:00";
 return text.str();
}
std::filesystem::path executable_directory() {
 std::wstring path(32768,L'\0'); const auto length = GetModuleFileNameW(nullptr,path.data(),static_cast<DWORD>(path.size()));
 if (length == 0 || length == path.size()) throw std::runtime_error("Could not locate native executable directory");
 path.resize(length); return std::filesystem::path(path).parent_path();
}
void report(const std::filesystem::path& path, const aibs::RenderStats& stats, bool success, const std::string& error,
            const std::filesystem::path& capture, std::uint64_t pixels, unsigned resize_checks, bool minimize_check) {
 if (path.empty()) return;
 if (!path.parent_path().empty()) std::filesystem::create_directories(path.parent_path());
 auto temporary = path; temporary += L".tmp";
 std::ofstream out(temporary,std::ios::binary);
 out << "{\n  \"schema_version\": 1,\n  \"status\": \"" << (success ? "passed" : "failed") << "\",\n  \"completed_at\": \"" << timestamp() << "\",\n"
     << "  \"adapter\": \"" << escaped(stats.adapter) << "\",\n  \"vendor_id\": " << stats.vendor_id << ",\n  \"device_id\": " << stats.device_id << ",\n"
     << "  \"feature_level\": \"" << escaped(stats.feature_level) << "\",\n  \"frames\": " << stats.frames << ",\n"
     << "  \"debug_layer\": " << (stats.debug_layer ? "true" : "false") << ",\n  \"debug_errors\": " << stats.debug_errors << ",\n  \"debug_warnings\": " << stats.debug_warnings << ",\n"
     << "  \"resize_checks\": " << resize_checks << ",\n  \"minimize_restore_check\": " << (minimize_check ? "true" : "false") << ",\n  \"nonbackground_pixels\": " << pixels << ",\n"
     << "  \"capture\": \"" << escaped(capture.string()) << "\",\n  \"error\": \"" << escaped(error) << "\",\n  \"checks\": [";
 if (success) out << "\"Hardware DX12 adapter rendered the motherboard geometry\",\"GPU readback contains non-background pixels\",\"Resize/recreate synchronization passed\",\"Minimized rendering suspended and restored\",\"GPU work completed before shutdown\"";
 else out << '"' << escaped(error.empty() ? "Renderer verification incomplete" : error) << '"';
 out << "]\n}\n"; out.close();
 if (!out) throw std::runtime_error("Could not write renderer verification report");
 if (!MoveFileExW(temporary.c_str(),path.c_str(),MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH)) throw std::runtime_error("Could not publish renderer report");
}
}

int wmain(int argc, wchar_t** argv) {
 for (int i=1;i<argc;++i) if (std::wstring(argv[i])==L"--asset-showcase") return run_asset_showcase(argc,argv);
 for (int i=1;i<argc;++i) if (std::wstring(argv[i])==L"--durable-world") return run_durable_world(argc,argv);
 for (int i=1;i<argc;++i) if (std::wstring(argv[i])==L"--obstacle-course" || std::wstring(argv[i])==L"--course-test") return run_obstacle_course(argc,argv);
 bool renderer_test = false;
 for (int i = 1; i < argc; ++i) if (std::wstring(argv[i]) == L"--self-test") renderer_test = true;
 if (!renderer_test) return run_native_world(argc, argv);
 bool self_test = false;
 std::filesystem::path capture_path, report_path;
 aibs::RenderStats stats;
 std::uint64_t captured_pixels = 0;
 unsigned resized = 0;
 bool minimized = false;
 try {
  for (int i = 1; i < argc; ++i) {
   const std::wstring argument(argv[i]);
   if (argument == L"--self-test") self_test = true;
   else if ((argument == L"--capture" || argument == L"--report") && i + 1 < argc) {
    auto value = std::filesystem::path(argv[++i]); if (argument == L"--capture") capture_path = std::move(value); else report_path = std::move(value);
   } else throw std::invalid_argument("Usage: aibs_motherboard [--self-test --capture BMP_PATH --report JSON_PATH]");
  }
  if (self_test && (capture_path.empty() || report_path.empty())) throw std::invalid_argument("Self-test requires --capture and --report");
  if (!capture_path.empty() && !capture_path.parent_path().empty()) std::filesystem::create_directories(capture_path.parent_path());
  SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);
  aibs::NativeWindow window(self_test ? 960u : 1440u,self_test ? 600u : 900u,
   L"AI-BS Motherboard World | WASD / arrows move | Right-mouse look | Space/Ctrl rise/lower | Shift fast | Esc close",!self_test);
  const auto scene = aibs::make_motherboard_scene();
  aibs::Dx12Renderer renderer(window,scene,executable_directory()/"shaders");
  aibs::Camera camera;
  if (self_test) {
   for (int frame = 0; frame < 6; ++frame) { if (!window.poll()) throw std::runtime_error("Window closed during startup self-test"); renderer.render(camera); }
   for (const auto size : {std::pair{800u,500u},std::pair{1200u,720u},std::pair{960u,640u}}) {
    window.set_size(size.first,size.second); window.poll();
    if (window.width() != size.first || window.height() != size.second) throw std::runtime_error("Native window resize did not apply");
    renderer.render(camera); ++resized;
   }
   const auto before = renderer.stats().frames;
   window.minimize(); window.poll();
   if (!window.minimized()) throw std::runtime_error("Native minimize state missing");
   renderer.render(camera);
   if (renderer.stats().frames != before) throw std::runtime_error("Renderer submitted work while minimized");
   window.restore(false); window.poll();
   if (window.minimized()) throw std::runtime_error("Native restore state missing");
   for (int frame = 0; frame < 6; ++frame) renderer.render(camera);
   minimized = true;
   captured_pixels = renderer.capture(capture_path);
   if (captured_pixels < 10000) throw std::runtime_error("GPU capture did not contain visible motherboard geometry");
   renderer.wait_idle(); stats = renderer.stats();
   if (stats.debug_errors) throw std::runtime_error("DX12 debug layer reported errors");
   report(report_path,stats,true,"",capture_path,captured_pixels,resized,minimized);
   std::cout << "PASS: DX12 motherboard rendered on " << stats.adapter << "; frames=" << stats.frames << "; capture pixels=" << captured_pixels
             << "; debug layer=" << stats.debug_layer << "; debug warnings=" << stats.debug_warnings << '\n';
  } else {
   std::cout << "AI-BS native motherboard world on " << renderer.stats().adapter << '\n';
   auto previous = std::chrono::steady_clock::now();
   while (window.poll()) {
    const auto now = std::chrono::steady_clock::now(); const float elapsed = std::chrono::duration<float>(now-previous).count(); previous = now;
    if (window.minimized()) { std::this_thread::sleep_for(std::chrono::milliseconds(20)); continue; }
    camera.update(window.input(),elapsed); renderer.render(camera);
   }
   renderer.wait_idle();
   if (!capture_path.empty()) captured_pixels = renderer.capture(capture_path);
   stats = renderer.stats();
   if (stats.debug_errors) throw std::runtime_error("DX12 debug layer reported errors");
  }
  return 0;
 } catch (const std::exception& error) {
  std::cerr << "Native renderer failed: " << error.what() << '\n';
  try { report(report_path,stats,false,error.what(),capture_path,captured_pixels,resized,minimized); } catch (const std::exception& reporting) { std::cerr << reporting.what() << '\n'; }
  return 1;
 }
}
