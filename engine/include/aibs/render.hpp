#pragma once
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <d3dcommon.h>
#include <aibs/platform.hpp>
#include <array>
#include <cstdint>
#include <cstddef>
#include <filesystem>
#include <memory>
#include <string>
#include <vector>

namespace aibs {
enum class GraphicsBackend {
    directx_12,
    directx_11_on_12,
    feature_level_10_0,
    feature_level_9_3,
    warp_software,
    translation_bridge
};

struct RendererConfig {
    GraphicsBackend backend = GraphicsBackend::directx_12;
    D3D_FEATURE_LEVEL target_feature_level = D3D_FEATURE_LEVEL_11_0;
    D3D_FEATURE_LEVEL minimum_feature_level = D3D_FEATURE_LEVEL_9_3;
    bool allow_warp_fallback = true;
    std::string config_path;
    std::vector<std::string> fallback_chain;
    bool dxvk_enabled = false;
    bool d8vk_enabled = false;
    std::vector<std::string> bridge_search_paths;
};

RendererConfig load_graphics_pipeline_config(const std::filesystem::path& config_path = {});

std::string to_string(GraphicsBackend backend);
std::string to_string(D3D_FEATURE_LEVEL level);
GraphicsBackend parse_graphics_backend(const std::string& str);
D3D_FEATURE_LEVEL parse_feature_level(const std::string& str);
bool query_feature_level_support(D3D_FEATURE_LEVEL level, bool use_warp = false);

struct TexturedScene;
struct SceneLighting;
struct CharacterMesh;
struct CharacterInstance;
struct CharacterAsset;
struct Vec3 { float x = 0, y = 0, z = 0; bool operator==(const Vec3&) const = default; };
struct Camera {
 Vec3 position{53, 43, -66};
 float yaw = -0.67f, pitch = -0.47f;
 void update(const WindowInput& input, float seconds);
 std::array<float, 16> view_projection(float aspect) const;
};
struct SceneVertex { Vec3 position; Vec3 normal; Vec3 color; float emission = 0; };
struct SceneMesh { std::vector<SceneVertex> vertices; std::vector<std::string> landmarks; };
SceneMesh make_motherboard_scene();
struct RenderStats {
 std::string adapter;
 std::string feature_level;
 std::string backend;
 const std::string& active_backend() const noexcept { return backend; }
 const std::string& selected_adapter() const noexcept { return adapter; }
 std::uint32_t vendor_id = 0, device_id = 0;
 std::uint64_t frames = 0, debug_errors = 0, debug_warnings = 0;
 std::uint64_t scene_replacements = 0, transient_buffer_allocations = 0, transient_frames = 0, full_idle_calls = 0;
 // Owned capture overhead, outside chapter-content GPU admission.
 std::uint64_t capture_frames=0,capture_buffer_allocations=0,capture_active_readback_bytes=0;
 std::uint64_t character_replacements = 0, character_buffer_allocations = 0, character_frames = 0;
 // Actual committed allocation bytes for active chapter content resources; excludes swapchain/depth/driver heaps.
 std::uint64_t scene_active_gpu_bytes = 0;
 std::uint64_t character_active_gpu_bytes = 0, character_replacement_peak_gpu_bytes = 0;
 std::uint64_t character_texture_allocations = 0, character_material_draws = 0;
 // Bounded diagnostic excerpts; severity counters still include every message.
 std::vector<std::string> debug_messages;
 bool debug_layer = false;
};
// Owned top-down BGRA8 copy of this renderer only. The caller retains one slot.
// A slot reserves at most 32MiB once; stable captures reuse its allocation.
struct CapturedFrame {
 static constexpr std::size_t maximum_bytes = 32u * 1024u * 1024u;
 std::uint32_t width = 0, height = 0;
 std::uint64_t present_id = 0, nonbackground_pixels = 0;
 std::vector<std::byte> bgra;
};
// Enabling validation affects subsequent devices in this process. Skipping
// enablement never disables validation already enabled by another owner.
enum class RenderValidationMode { enable_if_available, do_not_enable };
class Dx12Renderer {
public:
 Dx12Renderer(NativeWindow& window, const SceneMesh& scene, const std::filesystem::path& shader_directory);
 Dx12Renderer(NativeWindow& window, const SceneMesh& scene, const std::filesystem::path& shader_directory, RenderValidationMode validation);
 Dx12Renderer(NativeWindow& window, const SceneMesh& scene, const std::filesystem::path& shader_directory, const RendererConfig& config);
 Dx12Renderer(NativeWindow& window, const SceneMesh& scene, const std::filesystem::path& shader_directory, RenderValidationMode validation, const RendererConfig& config);
 ~Dx12Renderer();
 Dx12Renderer(const Dx12Renderer&) = delete;
 Dx12Renderer& operator=(const Dx12Renderer&) = delete;
 const RendererConfig& config() const noexcept;
 void resize(std::uint32_t width, std::uint32_t height);
 void render(const Camera& camera);
 // Per-frame geometry shares the scene pipeline/depth and is never persisted.
 // Its upload storage is fixed and fence-protected per swapchain buffer.
 static constexpr std::uint32_t transient_vertex_limit = 4096;
 void render(const Camera& camera, const SceneMesh& transient);
 // Validates and stages a new vertex buffer, waits for the previous scene's
 // GPU consumers, then publishes it. Failure preserves the current geometry.
 void set_scene(const SceneMesh& scene);
 // Independently owned textured layer. Staged upload and fence completion
 // precede publication; rejection preserves base geometry and prior textures.
 void set_textured_scene(const TexturedScene& scene);
 // Publish geometry and textured resources together; staging failure changes neither.
 void set_scene(const SceneMesh& base,const TexturedScene& textured);
 // Authored lights/shadow resources are staged before publication. The default
 // disabled state retains legacy rendering. Ordinary frames reuse fixed CBs.
 void set_lighting(const SceneLighting&);
 void set_scene(const SceneMesh& base,const TexturedScene& textured,const SceneLighting&);
 // Per-call active chapter-resource limit. Exact D3D12 allocation queries
 // include retained fixed transient/lighting buffers and the current character.
 // An over-budget candidate rejects before upload/idle/publication. Excludes
 // swapchain/depth/descriptors/driver heaps and temporary replacement uploads.
 void set_scene_bounded(const SceneMesh& base,const TexturedScene& textured,const SceneLighting&,
                        std::uint64_t maximum_content_gpu_bytes);
 // Dedicated owned indexed skin resources. Legacy render overloads do not draw
 // a character; ordinary poses use fixed frame-fenced constants only.
 void set_character(const CharacterMesh&);
 // Complete owned material/image resources are validated and uploaded before
 // publication. The vertex-colored CharacterMesh entry point remains intact.
 void set_character_asset(const CharacterAsset&);
 void clear_character();
 void render(const Camera&,const SceneMesh& transient,const CharacterInstance&);
 // Explicit whole-resource transaction. Null clears the character. The older
 // scene setters preserve independently owned character resources.
 void set_scene(const SceneMesh&,const TexturedScene&,const SceneLighting&,const CharacterMesh*);
 // Bounded whole-resource transaction retaining the legacy vertex-color path.
 void set_scene_character_bounded(const SceneMesh&,const TexturedScene&,const SceneLighting&,
                                  const CharacterMesh*,std::uint64_t maximum_content_gpu_bytes);
 // Distinct name keeps existing four-input nullptr calls unambiguous.
 void set_scene_character_asset(const SceneMesh&,const TexturedScene&,const SceneLighting&,const CharacterAsset*);
 // Same bound, replacing or explicitly clearing the character in one transaction.
 void set_scene_character_asset_bounded(const SceneMesh&,const TexturedScene&,const SceneLighting&,
                                        const CharacterAsset*,std::uint64_t maximum_content_gpu_bytes);
 void wait_idle();
 // Copies the latest completed GPU render target to a BMP and counts pixels
 // differing from the clear color. This is actual GPU readback, not a UI grab.
 std::uint64_t capture(const std::filesystem::path& path);
 // False leaves output untouched when no current present exists or minimized.
 // Invalid/oversize requests throw before GPU work. CPU and GPU readback slots
 // are each bounded to 32MiB and accounted outside chapter-content admission.
 bool capture_frame(CapturedFrame& reusable);
 RenderStats stats() const;
private:
 struct Impl;
 std::unique_ptr<Impl> impl_;
 void render_frame(const Camera&,const SceneMesh&,const CharacterInstance*);
};
}
