#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <aibs/first_boot.hpp>
#include <aibs/persistence.hpp>
#include <aibs/player.hpp>
#include <chrono>
#include <cstdio>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <thread>

namespace {
void require(bool condition, const char* message) { if (!condition) throw std::runtime_error(message); }
std::string quote(const std::string& text) {
 std::string value = "\"";
 for (unsigned char ch : text) {
  if (ch == '\\' || ch == '"') { value += '\\'; value += static_cast<char>(ch); }
  else if (ch >= 32) value += static_cast<char>(ch);
 }
 return value + '"';
}
std::wstring wide(const std::string& text) {
 if (text.empty()) return {};
 const auto length = MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, text.data(), static_cast<int>(text.size()), nullptr, 0);
 if (!length) return L"Text unavailable";
 std::wstring value(static_cast<std::size_t>(length), L'\0');
 MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, text.data(), static_cast<int>(text.size()), value.data(), length);
 return value;
}
std::filesystem::path executable_directory() {
 std::wstring path(32768, L'\0'); const auto length = GetModuleFileNameW(nullptr, path.data(), static_cast<DWORD>(path.size()));
 require(length && length < path.size(), "Cannot locate executable"); path.resize(length);
 return std::filesystem::path(path).parent_path();
}
std::filesystem::path default_checkpoint() {
 std::wstring directory(32768, L'\0'); const auto length = GetEnvironmentVariableW(L"LOCALAPPDATA", directory.data(), static_cast<DWORD>(directory.size()));
 require(length && length < directory.size(), "LOCALAPPDATA is unavailable; use --checkpoint PATH"); directory.resize(length);
 return std::filesystem::path(directory) / "AI-BS/FirstBootWorld/native-world.aibs";
}
std::string utc_time() {
 SYSTEMTIME t{}; GetSystemTime(&t);
 char text[48]{};
 std::snprintf(text, sizeof(text), "%04u-%02u-%02uT%02u:%02u:%02u+00:00", t.wYear, t.wMonth, t.wDay, t.wHour, t.wMinute, t.wSecond);
 return text;
}
void write_report(const std::filesystem::path& path, const aibs::CreatorSession& session,
                  const aibs::SceneSnapshot& scene, const aibs::RenderStats& stats,
                  bool invalid_rejected, bool empty_cleared) {
 if (path.empty()) return;
 if (!path.parent_path().empty()) std::filesystem::create_directories(path.parent_path());
 std::ofstream file(path);
 file << "{\n\"schema_version\":1,\"status\":\"passed\",\"completed_at\":" << quote(utc_time())
      << ",\"world_id\":" << quote(session.world_id()) << ",\"checkpoint_id\":" << quote(session.checkpoint_id())
      << ",\"revision\":" << session.revision() << ",\"entity_count\":" << session.world().size()
      << ",\"object_count\":" << scene.objects.size() << ",\"memory_events\":" << session.memory().events().size()
      << ",\"adapter\":" << quote(stats.adapter) << ",\"entity_ids\":{";
 bool first = true;
 for (const auto& [alias, entity] : session.world()) {
  if (!first) file << ','; first = false;
  file << quote(alias) << ':' << quote(entity.persistent_id);
 }
 file << "},\"metrics\":{\"invalid_mesh_rejected\":" << (invalid_rejected ? "true" : "false")
      << ",\"empty_scene_cleared\":" << (empty_cleared ? "true" : "false")
      << ",\"debug_layer\":" << (stats.debug_layer ? "true" : "false")
      << ",\"debug_errors\":" << stats.debug_errors << "},\"checks\":[\"Persistent world extracted into actual DX12 scene\"]}\n";
 require(file.good(), "Could not write world scene report");
}
aibs::Vec3 ray(const aibs::Camera& camera, float x, float y, float aspect) {
 const float sy = std::sin(camera.yaw), cy = std::cos(camera.yaw), sp = std::sin(camera.pitch), cp = std::cos(camera.pitch);
 const float scale = std::tan(3.14159265f / 8.0f);
 return {sy * cp + x * scale * aspect * cy - y * scale * sy * sp,
         sp + y * scale * cp,
         cy * cp - x * scale * aspect * sy - y * scale * cy * sp};
}
std::string relay_id(const aibs::CreatorSession& session) {
 for (const auto& [alias, entity] : session.world()) {
  (void)alias;
  if (entity.fields.at("firstboot.kind") == static_cast<double>(aibs::FirstBootKind::relay)) return entity.persistent_id;
 }
 throw std::runtime_error("No constructed relay exists");
}
void validate_game(const aibs::CreatorSession& session) { (void)aibs::mesh_from_snapshot(aibs::first_boot_scene(session)); }
constexpr aibs::Vec3 player_spawn{-32, 0.2f, -25};
aibs::SceneMesh player_mesh(const aibs::SceneSnapshot& world, const aibs::PlayerController& player) {
 if (!player.avatar_visible()) return {};
 aibs::SceneSnapshot visible{world.world_id,world.revision,{}};
 const auto p = player.state().feet;
 // Temporary visual proxy, excluded from authoring, collisions and checkpoints.
 visible.objects.push_back({world.world_id, "BS capsule proxy", {p.x,p.y+0.9f,p.z}, {0.3f,0.9f,0.3f}, {0.85f,0.50f,0.16f}, 0, false});
 return aibs::mesh_from_snapshot(visible);
}
int movement_probe(const std::filesystem::path& capture, const std::filesystem::path& report) {
 require(!capture.empty() && !report.empty(), "Movement verification requires explicit --capture and --movement-report paths");
 if (!capture.parent_path().empty()) std::filesystem::create_directories(capture.parent_path());
 if (!report.parent_path().empty()) std::filesystem::create_directories(report.parent_path());
 {
  std::ofstream started(report);
  started << "{\"schema_version\":1,\"status\":\"failed\",\"completed_at\":" << quote(utc_time())
          << ",\"checks\":[\"Movement verification has not completed\"]}";
 }
 aibs::CreatorSession session(aibs::first_boot_schema(), "movement-proof", "main");
 require(aibs::seed_first_boot(session).ok, "Could not seed movement world");
 const auto scene = aibs::first_boot_scene(session);
 aibs::PlayerController player(scene, player_spawn);
 SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);
 aibs::NativeWindow window(960,640,L"AI-BS grounded movement verification",false);
 aibs::Dx12Renderer renderer(window, aibs::mesh_from_snapshot(scene), executable_directory()/"shaders");
 aibs::WindowInput idle;
 for (int i=0; i<120; ++i) player.update(idle,1.0/60);
 require(player.state().grounded,"BS did not settle on the motherboard");
 const auto revision = session.revision();
 auto candidate = session;
 auto feet = player.state().feet;
 require(aibs::build_first_boot_relay(candidate,{feet.x,feet.y+1,feet.z}).ok,"Overlap fixture could not be prepared");
 bool rejected = false;
 try { player.set_scene(aibs::first_boot_scene(candidate)); } catch (const std::invalid_argument&) { rejected=true; }
 require(rejected && session.revision()==revision,"Overlapping construction was not rejected before publication");
 auto handle = static_cast<HWND>(window.native_handle());
 SendMessageW(handle,WM_KEYDOWN,'W',0);
 SendMessageW(handle,WM_KEYDOWN,VK_SPACE,0);
 auto edge=window.input(); require(edge.jump && !window.input().jump,"Jump input repeated without a new press");
 SendMessageW(handle,WM_ACTIVATEAPP,FALSE,0);
 auto unfocused=window.input();
 require(!unfocused.active && unfocused.forward==0 && !unfocused.jump,"Focus loss retained held controls");
 const auto paused=player.state(); player.update(unfocused,20);
 require(player.state().feet==paused.feet && player.state().ticks==paused.ticks,"Focus loss advanced simulation");
 SendMessageW(handle,WM_ACTIVATEAPP,TRUE,0);
 require(window.input().active,"Focus restore did not reactivate input");
 aibs::WindowInput walk; walk.forward=1;
 for(int i=0; i<60; ++i) player.update(walk,1.0/60);
 require(player.state().feet.z>player_spawn.z+2,"BS did not walk through the world");
 aibs::WindowInput third; third.cycle_camera=true; player.update(third,0);
 auto static_capture=capture; static_capture+=L".static.bmp";
 for(int i=0;i<3;++i) { window.poll(); renderer.render(player.camera()); }
 renderer.capture(static_capture);
 auto bytes=[](const std::filesystem::path& file) {
  std::ifstream stream(file,std::ios::binary);
  return std::string(std::istreambuf_iterator<char>(stream),{});
 };
 const auto proxy=player_mesh(scene,player);
 for(int i=0;i<3;++i) renderer.render(player.camera(),proxy);
 const auto pixels=renderer.capture(capture);
 require(pixels>10000,"Grounded camera capture was blank");
 require(bytes(capture)!=bytes(static_capture),"Transient BS proxy did not change GPU pixels");
 const auto before_frames=renderer.stats();
 auto moved_proxy=proxy;
 for(auto& vertex:moved_proxy.vertices) vertex.position.x+=1.5f;
 for(int i=0;i<6;++i) renderer.render(player.camera(),i%2==0?moved_proxy:aibs::SceneMesh{});
 const auto after_frames=renderer.stats();
 require(after_frames.scene_replacements==before_frames.scene_replacements &&
         after_frames.full_idle_calls==before_frames.full_idle_calls && after_frames.transient_buffer_allocations==2,
         "Transient player updates rebuilt static scene, allocated buffers or drained the GPU");
 auto removed_capture=capture; removed_capture+=L".removed.bmp";
 renderer.capture(removed_capture);
 require(bytes(removed_capture)==bytes(static_capture),"Removed transient proxy left stale GPU geometry");
 auto malformed=proxy; malformed.vertices.front().position.x=std::numeric_limits<float>::quiet_NaN();
 auto oversized=proxy; oversized.vertices.resize(4098,proxy.vertices.front());
 unsigned invalid=0; const auto before_invalid=renderer.stats().frames;
 for(const auto* bad:{&malformed,&oversized}) {
  try { renderer.render(player.camera(),*bad); } catch(const std::invalid_argument&) { ++invalid; }
 }
 require(invalid==2 && renderer.stats().frames==before_invalid,"Invalid transient meshes entered GPU submission");
 auto rejected_capture=capture; rejected_capture+=L".rejected.bmp"; renderer.capture(rejected_capture);
 require(bytes(rejected_capture)==bytes(static_capture),"Rejected transient geometry changed the prior GPU frame");
 for(int i=0;i<3;++i) renderer.render(player.camera(),proxy);
 renderer.capture(capture);
 renderer.wait_idle(); const auto stats=renderer.stats();
 require(stats.debug_errors==0,"Grounded render reported GPU validation errors");
 aibs::PlayerController restarted=aibs::first_boot_player(session);
 require(restarted.state().feet==player_spawn && session.revision()==revision,"Transient player restart changed authored world");
 std::ofstream result(report);
 result << "{\"schema_version\":1,\"status\":\"passed\",\"completed_at\":" << quote(utc_time())
        << ",\"engine\":\"Jolt\",\"engine_version\":\"5.6.0\",\"fixed_hz\":60,\"adapter\":" << quote(stats.adapter)
        << ",\"metrics\":{\"ticks\":" << player.state().ticks << ",\"capture_pixels\":" << pixels
        << ",\"debug_errors\":" << stats.debug_errors << ",\"debug_layer\":" << (stats.debug_layer?"true":"false")
        << ",\"static_scene_replacements\":" << stats.scene_replacements << ",\"transient_buffer_allocations\":" << stats.transient_buffer_allocations
        << ",\"transient_frames\":" << stats.transient_frames
        << "},\"checks\":[\"BS capsule walks on saved-world motherboard colliders\",\"Live overlapping build rejected before world publication\","
           "\"Win32 jump edges and focus clearing pause simulation\",\"Third-person BS proxy rendered by native DX12\","
           "\"Transient proxy alternation/removal/rejection preserves static scene without full GPU drain\","
           "\"Restart resets transient player pose without editing world or Adam history\"]}";
 require(result.good(),"Could not write movement report");
 std::cout << "PASS: native grounded movement, focus, build guard and DX12 on " << stats.adapter << '\n';
 return 0;
}
aibs::Result game_history(aibs::CreatorSession& session, bool backwards) {
 auto preview = session;
 auto result = backwards ? preview.undo() : preview.redo();
 if (!result.ok) return result;
 try { validate_game(preview); }
 catch (const std::exception&) { return {false, "The starting motherboard is protected; undo later changes instead.", session.revision()}; }
 return backwards ? session.undo() : session.redo();
}
}

int run_native_world(int argc, wchar_t** argv) {
 std::filesystem::path slot, capture, report;
 std::wstring step;
 bool movement_test = false;
 try {
  for (int i = 1; i < argc; ++i) {
   const std::wstring option(argv[i]);
   if (option == L"--movement-test") { movement_test=true; continue; }
   require(i + 1 < argc, "Usage: aibs_motherboard [--checkpoint PATH] [--world-step seed|edit|verify|undo|redo|delete --capture BMP --world-report JSON]");
   if (option == L"--checkpoint") slot = argv[++i];
   else if (option == L"--capture") capture = argv[++i];
   else if (option == L"--world-report") report = argv[++i];
   else if (option == L"--movement-report") report = argv[++i];
   else if (option == L"--world-step") step = argv[++i];
   else throw std::invalid_argument("Unknown native world option");
  }
  if (movement_test) return movement_probe(capture,report);
  if (!step.empty()) {
   require(!slot.empty() && !capture.empty() && !report.empty(), "World test requires explicit checkpoint, capture and report paths");
   require(step == L"seed" || step == L"edit" || step == L"verify" || step == L"undo" || step == L"redo" || step == L"delete", "Unknown world verification step");
  }
  if (slot.empty()) slot = default_checkpoint();
  if (!slot.parent_path().empty()) std::filesystem::create_directories(slot.parent_path());
  aibs::CreatorSession session(aibs::first_boot_schema(), "first-boot-world", "main");
  const bool exists = std::filesystem::exists(slot);
  if (exists) {
   const auto loaded = aibs::CheckpointStore::load(slot, session, validate_game); require(loaded.ok, loaded.message.c_str());
  } else {
   require(step.empty() || step == L"seed", "Checkpoint does not exist for this verification step");
   const auto seeded = aibs::seed_first_boot(session); require(seeded.ok, seeded.message.c_str());
   const auto saved = aibs::CheckpointStore::save(slot, session); require(saved.ok, saved.message.c_str());
  }
  auto snapshot = aibs::first_boot_scene(session);
  auto mesh = aibs::mesh_from_snapshot(snapshot);
  SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);
  aibs::NativeWindow window(step.empty() ? 1440u : 960u, step.empty() ? 900u : 640u,
    L"AI-BS First Boot | E/click interact | B build | Delete dismantle | Ctrl+Z/Y undo/redo | F5 save | F9 reload", step.empty());
  aibs::Dx12Renderer renderer(window, mesh, executable_directory() / "shaders");
  aibs::Camera camera;
  bool invalid_rejected = false, empty_cleared = false;
  auto draw = [&] { for (int i = 0; i < 3; ++i) { window.poll(); renderer.render(camera); } };
  auto update = [&] {
   auto next = aibs::first_boot_scene(session);
   renderer.set_scene(aibs::mesh_from_snapshot(next)); snapshot = std::move(next);
  };
  draw();
  if (!step.empty()) {
   // Exercise real Win32 edge consumption independently of action routines.
   SendMessageW(static_cast<HWND>(window.native_handle()), WM_KEYDOWN, 'E', 0);
   require(window.input().interact && !window.input().interact, "Interaction key is not edge-triggered");
   SendMessageW(static_cast<HWND>(window.native_handle()), WM_KEYUP, 'E', 0);
   if (step == L"edit") {
    const auto repaired = aibs::repair_first_boot(session, session.world().at("core-01").persistent_id);
    require(repaired.ok, repaired.message.c_str());
    const auto built = aibs::build_first_boot_relay(session, {30, 2, -20}); require(built.ok, built.message.c_str());
    update(); draw();
    auto prior_capture = capture; prior_capture += L".before.bmp";
    renderer.capture(prior_capture);
    auto bad = aibs::mesh_from_snapshot(snapshot); bad.vertices.front().position.x = std::numeric_limits<float>::quiet_NaN();
    try { renderer.set_scene(bad); } catch (const std::invalid_argument&) { invalid_rejected = true; }
    require(invalid_rejected, "Invalid mesh replacement was accepted");
    draw();
    auto rejected_capture = capture; rejected_capture += L".rejected.bmp";
    renderer.capture(rejected_capture);
    std::ifstream before_pixels(prior_capture, std::ios::binary), after_pixels(rejected_capture, std::ios::binary);
    require(std::string(std::istreambuf_iterator<char>(before_pixels), {}) == std::string(std::istreambuf_iterator<char>(after_pixels), {}),
            "Rejected mesh replacement changed rendered pixels");
    renderer.set_scene({}); draw();
    auto empty_capture = capture; empty_capture += L".empty.bmp";
    empty_cleared = renderer.capture(empty_capture) == 0;
    require(empty_cleared, "Empty scene did not clear the frame");
    update();
   } else if (step == L"undo") require(game_history(session, true).ok, "Undo failed or starting world is protected");
   else if (step == L"redo") require(game_history(session, false).ok, "Redo failed");
   else if (step == L"delete") require(aibs::dismantle_first_boot(session, relay_id(session)).ok, "Dismantle failed");
   else require(step == L"seed" || step == L"verify", "Unknown world verification step");
   if (step != L"verify") {
    validate_game(session);
    const auto saved = aibs::CheckpointStore::save(slot, session); require(saved.ok, saved.message.c_str());
   }
   update(); draw();
   require(!capture.empty() && !report.empty(), "World test requires capture and report");
   if (!capture.parent_path().empty()) std::filesystem::create_directories(capture.parent_path());
   require(renderer.capture(capture) > 10000, "Visible world capture was blank");
   renderer.wait_idle(); const auto stats = renderer.stats();
   require(stats.debug_errors == 0, "GPU validation failed");
   write_report(report, session, snapshot, stats, invalid_rejected, empty_cleared);
   std::cout << "PASS: visible world " << session.world_id() << " revision " << session.revision() << '\n';
   return 0;
  }
  auto player=aibs::first_boot_player(session);
  camera = player.camera();
  std::string notice = "Checkpoint restored. World changes save after each action; player pose starts at the board entrance.";
  auto saved_revision = session.revision();
  auto previous = std::chrono::steady_clock::now();
  while (window.poll()) {
   const auto now = std::chrono::steady_clock::now(); const float seconds = std::chrono::duration<float>(now - previous).count(); previous = now;
   if (window.minimized()) {
    aibs::WindowInput paused; paused.active=false; player.update(paused,0);
    std::this_thread::sleep_for(std::chrono::milliseconds(20)); continue;
   }
   const auto input = window.input();
   if (!input.active) { player.update(input,0); std::this_thread::sleep_for(std::chrono::milliseconds(20)); continue; }
   player.update(input,seconds);
   if (player.state().feet.y < -20) { player=aibs::first_boot_player(session); notice="BS returned to a clear board entrance after falling."; }
   camera=player.camera();
   const auto direction = ray(camera, input.pointer_interact ? input.pointer_x : 0, input.pointer_interact ? input.pointer_y : 0,
                              static_cast<float>(window.width()) / static_cast<float>(window.height()));
   const auto hit = aibs::pick_scene(snapshot, camera.position, direction);
   const auto old_revision = session.revision();
   if (input.reload || input.undo || input.redo || input.interact || input.build || input.dismantle) {
   auto candidate=session;
   bool reload_ok=false;
   if (input.reload) {
    const auto loaded = aibs::CheckpointStore::load(slot, candidate, validate_game); notice = loaded.message;
    reload_ok=loaded.ok;
   } else if (input.undo) notice = game_history(candidate, true).message;
   else if (input.redo) notice = game_history(candidate, false).message;
   else if (input.interact) {
    if (hit) {
     const auto* target = aibs::first_boot_entity(session, hit->persistent_id);
     notice = target ? "Inspecting " + target->name : "Target no longer exists";
     if (target && (target->fields.at("firstboot.kind") == 2 || target->fields.at("firstboot.kind") == 6))
      notice = aibs::repair_first_boot(candidate, hit->persistent_id).message;
    } else notice = "Aim at the CPU core or a relay, or click its visible surface.";
   } else if (input.build) {
    const auto center = ray(camera, 0, 0, static_cast<float>(window.width()) / static_cast<float>(window.height()));
    const float distance = center.y < -0.0001f ? (1.0f - camera.position.y) / center.y : -1;
    if (distance > 0 && distance < 200)
     notice = aibs::build_first_boot_relay(candidate, {camera.position.x + center.x * distance, 1.2f, camera.position.z + center.z * distance}).message;
    else notice = "Look toward the board surface to place a relay.";
   } else if (input.dismantle) notice = hit ? aibs::dismantle_first_boot(candidate, hit->persistent_id).message : "Aim at a constructed relay.";
   if (candidate.revision()!=old_revision || reload_ok) {
    auto next=aibs::first_boot_scene(candidate);
    try {
     if (reload_ok) {
      // Reload begins at the same secured prototype entrance; the eventual
      // saved checkpoint/respawn component belongs to the durable gameplay slice.
      auto replacement=[&] {
       try { return aibs::first_boot_player(candidate); }
       catch (const std::runtime_error& error) {
        // A saved board with no clear sampled entrance must reject reload
        // while retaining the currently playable world and unsaved changes.
        throw std::invalid_argument(error.what());
       }
      }();
      renderer.set_scene(aibs::mesh_from_snapshot(next));
      player=std::move(replacement);
     } else {
      player.set_scene(next);
      try { renderer.set_scene(aibs::mesh_from_snapshot(next)); }
      catch (...) { player.set_scene(snapshot); throw; }
     }
     session=std::move(candidate); snapshot=std::move(next);
     if (reload_ok) saved_revision=session.revision();
    } catch (const std::invalid_argument& error) { notice=std::string("Change blocked: ")+error.what(); }
   }
   }
   if (session.revision() != old_revision && !input.reload) {
    const auto saved = aibs::CheckpointStore::save(slot, session);
    notice = saved.ok ? "Change recorded and checkpoint saved." : "UNSAVED: " + saved.message;
    if (saved.ok) saved_revision = session.revision();
   } else if (input.save) {
    const auto saved = aibs::CheckpointStore::save(slot, session); notice = saved.ok ? "Checkpoint saved." : "UNSAVED: " + saved.message;
    if (saved.ok) saved_revision = session.revision();
   }
   camera=player.camera();
   const auto center_hit = aibs::pick_scene(snapshot, camera.position, ray(camera, 0, 0, static_cast<float>(window.width()) / static_cast<float>(window.height())));
   const auto* target = center_hit ? aibs::first_boot_entity(session, center_hit->persistent_id) : nullptr;
   const std::string target_text = target ? target->name : "Look at a component or click to select";
   window.set_status(L"WASD walk | Right-drag look | Space jump | Shift sprint | V camera | F2 inspect\nE/click interact | B build | Delete dismantle | Ctrl+Z/Y history | F5 save | F9 reload\nTarget: "
     + wide(target_text) + L"\nAdam: " + wide(aibs::first_boot_guidance(session)) + L"\n"
     + (saved_revision == session.revision() ? L"SAVED | " : L"UNSAVED | ")
     + (player.inspection_mode()?L"INSPECTION | ":player.third_person()?L"THIRD PERSON | ":L"FIRST PERSON | ") + wide(notice));
   renderer.render(camera,player_mesh(snapshot,player));
  }
  renderer.wait_idle();
  if (!capture.empty()) renderer.capture(capture);
  return 0;
 } catch (const std::exception& error) {
  std::cerr << "Native world failed: " << error.what() << '\n';
  if (step.empty() && !movement_test) MessageBoxW(nullptr, wide(error.what()).c_str(), L"AI-BS world could not continue", MB_OK | MB_ICONERROR);
  return 1;
 }
}
