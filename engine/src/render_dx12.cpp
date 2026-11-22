#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <d3d12.h>
#include <d3d12sdklayers.h>
#include <dxgi1_6.h>
#include <DirectXMath.h>
#include <wrl/client.h>
#include <aibs/render.hpp>
#include <aibs/textured_scene.hpp>
#include <aibs/lighting.hpp>
#include <aibs/character_scene.hpp>
#include <aibs/character_assets.hpp>
#include "render_submission.hpp"
#include "owned_hud.hpp"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <fstream>
#include <limits>
#include <stdexcept>

namespace aibs {
namespace {
using Microsoft::WRL::ComPtr;
void checked(HRESULT result, const char* operation) {
 if (FAILED(result)) throw std::runtime_error(std::string(operation) + " failed, HRESULT=" + std::to_string(static_cast<unsigned long>(result)));
}
std::string utf8(const wchar_t* value) {
 const int count = WideCharToMultiByte(CP_UTF8, 0, value, -1, nullptr, 0, nullptr, nullptr);
 if (count <= 1) return {};
 std::string text(static_cast<std::size_t>(count), '\0');
 WideCharToMultiByte(CP_UTF8, 0, value, -1, text.data(), count, nullptr, nullptr); text.pop_back(); return text;
}
std::vector<char> read_shader(const std::filesystem::path& path) {
 std::ifstream file(path, std::ios::binary | std::ios::ate);
 if (!file) throw std::runtime_error("Compiled shader missing: " + path.string());
 const auto size = file.tellg();
 if (size <= 0 || size > 1024 * 1024) throw std::runtime_error("Invalid compiled shader size");
 std::vector<char> bytes(static_cast<std::size_t>(size)); file.seekg(0); file.read(bytes.data(), size);
 if (!file) throw std::runtime_error("Could not read compiled shader");
 return bytes;
}
D3D12_RESOURCE_DESC buffer_description(UINT64 bytes) {
 D3D12_RESOURCE_DESC description{}; description.Dimension = D3D12_RESOURCE_DIMENSION_BUFFER;
 description.Width = bytes; description.Height = 1; description.DepthOrArraySize = 1; description.MipLevels = 1;
 description.SampleDesc.Count = 1; description.Layout = D3D12_TEXTURE_LAYOUT_ROW_MAJOR; return description;
}
D3D12_HEAP_PROPERTIES heap_properties(D3D12_HEAP_TYPE type) {
 D3D12_HEAP_PROPERTIES properties{}; properties.Type = type; properties.CreationNodeMask = 1; properties.VisibleNodeMask = 1; return properties;
}
D3D12_RESOURCE_BARRIER transition(ID3D12Resource* resource, D3D12_RESOURCE_STATES before, D3D12_RESOURCE_STATES after) {
 D3D12_RESOURCE_BARRIER barrier{}; barrier.Type = D3D12_RESOURCE_BARRIER_TYPE_TRANSITION;
 barrier.Transition.pResource = resource; barrier.Transition.Subresource = D3D12_RESOURCE_BARRIER_ALL_SUBRESOURCES;
 barrier.Transition.StateBefore = before; barrier.Transition.StateAfter = after; return barrier;
}
void validate_mesh(const SceneMesh& scene) {
 if (scene.vertices.size() > 1000000 || scene.vertices.size() % 3 != 0)
  throw std::invalid_argument("Scene must contain at most one million triangle vertices");
 const auto finite = [](Vec3 value) { return std::isfinite(value.x) && std::isfinite(value.y) && std::isfinite(value.z); };
 const auto normalized = [](float value) { return std::isfinite(value) && value >= 0 && value <= 1; };
 for (const auto& vertex : scene.vertices) {
  if (!finite(vertex.position) || !finite(vertex.normal) ||
      (vertex.normal.x == 0 && vertex.normal.y == 0 && vertex.normal.z == 0) ||
      !normalized(vertex.color.x) || !normalized(vertex.color.y) || !normalized(vertex.color.z) || !normalized(vertex.emission))
   throw std::invalid_argument("Scene vertex requires finite position/normal and normalized color/emission");
 }
}
void box(SceneMesh& scene, Vec3 center, Vec3 half, Vec3 color, float emission = 0, float angle = 0) {
 const Vec3 corners[] = {{-1,-1,-1},{1,-1,-1},{1,1,-1},{-1,1,-1},{-1,-1,1},{1,-1,1},{1,1,1},{-1,1,1}};
 constexpr unsigned faces[6][4] = {{0,3,2,1},{4,5,6,7},{0,4,7,3},{1,2,6,5},{3,7,6,2},{0,1,5,4}};
 const Vec3 normals[] = {{0,0,-1},{0,0,1},{-1,0,0},{1,0,0},{0,1,0},{0,-1,0}};
 constexpr unsigned triangles[] = {0,1,2,0,2,3};
 const float cosine = std::cos(angle), sine = std::sin(angle);
 for (unsigned face = 0; face < 6; ++face) {
  const auto normal = normals[face];
  const Vec3 rotated_normal{normal.x * cosine - normal.y * sine, normal.x * sine + normal.y * cosine, normal.z};
  for (const auto corner : triangles) {
   const auto unit = corners[faces[face][corner]];
   const float x = unit.x * half.x, y = unit.y * half.y;
   scene.vertices.push_back({{center.x + x * cosine - y * sine, center.y + x * sine + y * cosine, center.z + unit.z * half.z}, rotated_normal, color, emission});
  }
 }
}
}

void Camera::update(const WindowInput& input, float seconds) {
 if (!std::isfinite(seconds) || seconds < 0) return;
 if (!std::isfinite(input.forward) || !std::isfinite(input.right) || !std::isfinite(input.up)) return;
 if (std::isfinite(input.yaw_delta)) yaw += input.yaw_delta;
 if (std::isfinite(input.pitch_delta)) pitch = std::clamp(pitch + input.pitch_delta, -1.45f, 1.45f);
 const float elapsed = std::min(seconds, 0.1f);
 const float speed = elapsed * (input.sprint ? 35.0f : 14.0f);
 const float forward = std::clamp(input.forward, -1.0f, 1.0f), right = std::clamp(input.right, -1.0f, 1.0f), up = std::clamp(input.up, -1.0f, 1.0f);
 position.x += (std::sin(yaw) * forward + std::cos(yaw) * right) * speed;
 position.z += (std::cos(yaw) * forward - std::sin(yaw) * right) * speed;
 position.y += up * speed;
}
std::array<float, 16> Camera::view_projection(float aspect) const {
 if (!std::isfinite(aspect) || aspect <= 0) throw std::invalid_argument("Camera aspect must be positive and finite");
 if (!std::isfinite(position.x) || !std::isfinite(position.y) || !std::isfinite(position.z) || !std::isfinite(yaw) || !std::isfinite(pitch)) throw std::invalid_argument("Camera transform must be finite");
 using namespace DirectX;
 const auto eye = XMVectorSet(position.x, position.y, position.z, 1);
 const auto direction = XMVectorSet(std::sin(yaw) * std::cos(pitch), std::sin(pitch), std::cos(yaw) * std::cos(pitch), 0);
 const auto view = XMMatrixLookToLH(eye, direction, XMVectorSet(0, 1, 0, 0));
 const auto projection = XMMatrixPerspectiveFovLH(XM_PIDIV4, aspect, 0.1f, 600.0f);
 XMFLOAT4X4 matrix; XMStoreFloat4x4(&matrix, view * projection);
 std::array<float,16> values{}; std::memcpy(values.data(), &matrix, sizeof(matrix)); return values;
}
SceneMesh make_motherboard_scene() {
 SceneMesh scene;
 scene.landmarks = {"ASUS-inspired motherboard", "Ryzen CPU socket", "DDR5 memory towers", "RTX 4090 FE execution core", "M.2 archive"};
 box(scene, {0,-1,0}, {47,1,36}, {0.035f,0.15f,0.12f});
 box(scene, {0,-2.3f,0}, {48,0.3f,37}, {0.08f,0.09f,0.12f});
 for (int i = -8; i <= 8; ++i) {
  const float x = static_cast<float>(i) * 5;
  box(scene, {x,0.06f,0}, {0.10f,0.06f,33}, {0.85f,0.46f,0.12f}, 0.7f);
  box(scene, {0,0.05f,x * 0.75f}, {44,0.04f,0.06f}, {0.30f,0.60f,0.42f}, 0.4f);
 }
 // CPU socket with a reflective lid and surrounding power stages.
 box(scene, {-13,1.1f,-5}, {9,1.1f,9}, {0.12f,0.13f,0.17f});
 box(scene, {-13,2.35f,-5}, {6.3f,0.3f,6.3f}, {0.58f,0.62f,0.69f});
 box(scene, {-13,2.72f,-5}, {4.7f,0.06f,4.7f}, {0.12f,0.22f,0.28f});
 for (int i = 0; i < 10; ++i) box(scene, {-24,1.4f,-14 + static_cast<float>(i) * 2}, {1.1f,1.4f,0.65f}, {0.18f,0.20f,0.24f});
 // Four memory sticks, gold contacts and exposed chips.
 for (int i = 0; i < 4; ++i) {
  const float x = 8 + static_cast<float>(i) * 4.0f;
  box(scene, {x,1,-7}, {1.3f,1,12}, {0.1f,0.11f,0.14f});
  box(scene, {x,5.5f,-7}, {0.6f,4.5f,10.5f}, {0.12f,0.29f,0.22f});
  box(scene, {x,10.1f,-7}, {0.9f,0.2f,10.7f}, {0.70f,0.32f,0.08f}, 0.65f);
  for (int j = 0; j < 6; ++j) box(scene, {x-0.75f,5.7f,-15+static_cast<float>(j)*3.2f}, {0.24f,2,1.2f}, {0.07f,0.08f,0.11f});
 }
 // GPU landmark: dark FE-style monolith with luminous X frame and fan rings.
 box(scene, {0,10,24}, {23,10,3.5f}, {0.09f,0.10f,0.13f});
 box(scene, {0,10,20.3f}, {23.5f,0.75f,0.2f}, {0.92f,0.48f,0.10f}, 1, 0.39f);
 box(scene, {0,10,20.25f}, {23.5f,0.75f,0.2f}, {0.92f,0.48f,0.10f}, 1, -0.39f);
 for (int fan = 0; fan < 2; ++fan) {
  const float center = fan == 0 ? -13.0f : 13.0f;
  for (int segment = 0; segment < 20; ++segment) {
   const float angle = static_cast<float>(segment) * DirectX::XM_2PI / 20;
   box(scene, {center + std::cos(angle)*6,10+std::sin(angle)*6,20}, {0.5f,1,0.25f}, {0.31f,0.34f,0.39f}, 0, angle);
  }
 }
 // Storage archive, capacitors, chipset and PCIe corridors.
 box(scene, {21,1.1f,-27}, {13,1.1f,3}, {0.12f,0.13f,0.16f});
 for (int i = 0; i < 12; ++i) box(scene, {10+static_cast<float>(i)*2,2.3f,-27}, {0.2f,0.4f,3}, {0.35f,0.38f,0.44f});
 for (int i = 0; i < 14; ++i) box(scene, {-40 + static_cast<float>(i % 7)*3,1.8f,-28+static_cast<float>(i/7)*5}, {0.9f,1.8f,0.9f}, {0.22f,0.26f,0.31f});
 for (int i = 0; i < 3; ++i) box(scene, {27,0.7f,4+static_cast<float>(i)*5}, {12,0.7f,0.8f}, {0.11f,0.12f,0.15f});
 box(scene, {-32,1.8f,23}, {7,1.8f,8}, {0.16f,0.18f,0.21f});
 return scene;
}

struct Dx12Renderer::Impl {
 static constexpr UINT frame_count = 2;
 NativeWindow& window;
 ComPtr<IDXGIFactory6> factory;
 ComPtr<IDXGIAdapter1> adapter;
 ComPtr<ID3D12Device> device;
 ComPtr<ID3D12InfoQueue> info;
 ComPtr<ID3D12CommandQueue> queue;
 ComPtr<IDXGISwapChain3> swapchain;
 ComPtr<ID3D12DescriptorHeap> rtv_heap, dsv_heap;
 ComPtr<ID3D12Resource> targets[frame_count], depth, vertex_buffer;
 ComPtr<ID3D12Resource> transient_buffers[frame_count];
 D3D12_VERTEX_BUFFER_VIEW transient_views[frame_count]{};
 ComPtr<ID3D12CommandAllocator> allocators[frame_count];
 ComPtr<ID3D12GraphicsCommandList> commands;
 ComPtr<ID3D12RootSignature> root;
 ComPtr<ID3D12PipelineState> pipeline;
 ComPtr<ID3D12Fence> fence;
 HANDLE fence_event = nullptr;
 UINT64 next_fence = 0, frame_fences[frame_count]{};
 UINT descriptor_size = 0, width = 0, height = 0, vertex_count = 0, last_target = 0;
 D3D12_VERTEX_BUFFER_VIEW vertex_view{};
 RenderStats statistics;
 bool capture_valid = false;
 ComPtr<ID3D12Resource> capture_readback;
 ComPtr<ID3D12CommandAllocator> capture_allocator;
 ComPtr<ID3D12GraphicsCommandList> capture_commands;
 std::filesystem::path texture_shaders;
 struct CharacterGpu;
 #include "render_textures.inl"
 #include "render_lighting.inl"
 #include "render_character.inl"
 static constexpr float clear_color[4] = {0.015f,0.025f,0.035f,1};
 #include "render_owned_hud.inl"

 explicit Impl(NativeWindow& owner) : window(owner) {}
 ~Impl() {
  if (fence_event) CloseHandle(fence_event);
 }
 // A failed wait is not permission to release submitted resources. Failed
 // owners are retired intact and reaped only after completion/device removal.
 Impl* retired_next=nullptr;
 UINT64 retirement_fence=0;
 static Impl*& retired_head()noexcept{static Impl* head=nullptr;return head;}
 static SRWLOCK& retired_lock()noexcept{static SRWLOCK lock=SRWLOCK_INIT;return lock;}
 bool device_removed()const noexcept{return device&&FAILED(device->GetDeviceRemovedReason());}
 static void retire(Impl* owner)noexcept{
  AcquireSRWLockExclusive(&retired_lock());owner->retired_next=retired_head();retired_head()=owner;ReleaseSRWLockExclusive(&retired_lock());
 }
 static void reap_retired()noexcept{
  AcquireSRWLockExclusive(&retired_lock());auto** slot=&retired_head();
  while(*slot){auto* owner=*slot;const auto completed=owner->fence?owner->fence->GetCompletedValue():0;
   if(owner->device_removed()||(owner->retirement_fence&&completed!=UINT64_MAX&&completed>=owner->retirement_fence)){
    *slot=owner->retired_next;owner->submissions.release_after_completion();delete owner;
   }else slot=&owner->retired_next;
  }
  ReleaseSRWLockExclusive(&retired_lock());
 }
 void require_healthy()const{submissions.require_healthy();}
 void wait(UINT64 value) {
  if (!fence || value == 0) return;
  try{
  const auto completed = fence->GetCompletedValue();
  if (completed == UINT64_MAX) throw std::runtime_error("GPU fence unavailable after device removal");
  if (completed >= value) return;
  checked(fence->SetEventOnCompletion(value, fence_event), "Fence SetEventOnCompletion");
  if (WaitForSingleObject(fence_event, 10000) != WAIT_OBJECT_0) throw std::runtime_error("GPU fence timed out");
  checked(device->GetDeviceRemovedReason(), "GPU device state");
  const auto verified=fence->GetCompletedValue();
  if(verified==UINT64_MAX||verified<value)throw std::runtime_error("GPU fence wake did not prove completion");
  }catch(...){submissions.poison();throw;}
 }
 UINT64 signal_queue(){
  try{
   if(next_fence>=UINT64_MAX-1)throw std::runtime_error("GPU fence sequence exhausted");
   const auto value=next_fence+1;checked(queue->Signal(fence.Get(),value),"Queue signal");next_fence=value;return value;
  }catch(...){submissions.poison();throw;}
 }
 void drain() {
  if (!queue || !fence) return;
  ++statistics.full_idle_calls;
  retirement_fence=0;retirement_fence=signal_queue();wait(retirement_fence);
 }
 void idle(){require_healthy();drain();}
 bool shutdown_safe()noexcept{
  try{drain();submissions.release_after_completion();return true;}
  catch(...){if(device_removed()){submissions.release_after_completion();return true;}return false;}
 }
 void surfaces() {
  auto handle = rtv_heap->GetCPUDescriptorHandleForHeapStart();
  for (UINT i = 0; i < frame_count; ++i) {
   checked(swapchain->GetBuffer(i, IID_PPV_ARGS(&targets[i])), "Swapchain buffer");
   device->CreateRenderTargetView(targets[i].Get(), nullptr, handle); handle.ptr += descriptor_size;
  }
  for (UINT i = 0; i < frame_count; ++i) {
   D3D12_RENDER_TARGET_VIEW_DESC srgb{};srgb.Format=DXGI_FORMAT_R8G8B8A8_UNORM_SRGB;srgb.ViewDimension=D3D12_RTV_DIMENSION_TEXTURE2D;
   device->CreateRenderTargetView(targets[i].Get(),&srgb,handle);handle.ptr+=descriptor_size;
  }
  D3D12_RESOURCE_DESC description{}; description.Dimension = D3D12_RESOURCE_DIMENSION_TEXTURE2D;
  description.Width = width; description.Height = height; description.DepthOrArraySize = 1; description.MipLevels = 1;
  description.Format = DXGI_FORMAT_D32_FLOAT; description.SampleDesc.Count = 1; description.Flags = D3D12_RESOURCE_FLAG_ALLOW_DEPTH_STENCIL;
  D3D12_CLEAR_VALUE clear{}; clear.Format = DXGI_FORMAT_D32_FLOAT; clear.DepthStencil.Depth = 1;
  const auto heap = heap_properties(D3D12_HEAP_TYPE_DEFAULT);
  checked(device->CreateCommittedResource(&heap,D3D12_HEAP_FLAG_NONE,&description,D3D12_RESOURCE_STATE_DEPTH_WRITE,&clear,IID_PPV_ARGS(&depth)), "Depth resource");
  device->CreateDepthStencilView(depth.Get(), nullptr, dsv_heap->GetCPUDescriptorHandleForHeapStart());
 }
 struct BaseGpu {ComPtr<ID3D12Resource> buffer;D3D12_VERTEX_BUFFER_VIEW view{};UINT count=0;};
 // One accounting path for live statistics and staged publication. D3D12's
 // allocation query charges committed alignment, never logical mip byte sums.
 static UINT64 gpu_sum(UINT64 total,UINT64 value)noexcept{
  return value>UINT64_MAX-total?UINT64_MAX:total+value;
 }
 UINT64 gpu_allocation(const D3D12_RESOURCE_DESC& desc)const noexcept{
  const auto bytes=device->GetResourceAllocationInfo(0,1,&desc).SizeInBytes;
  return bytes==0?UINT64_MAX:bytes;
 }
 UINT64 gpu_resource(ID3D12Resource* resource)const noexcept{
  return resource?gpu_allocation(resource->GetDesc()):0;
 }
 UINT64 character_gpu_bytes(const CharacterGpu* actor)const noexcept{
  UINT64 total=0;if(!actor)return total;
  total=gpu_sum(total,gpu_resource(actor->vertices.Get()));total=gpu_sum(total,gpu_resource(actor->indices.Get()));
  for(const auto& buffer:actor->constants)total=gpu_sum(total,gpu_resource(buffer.Get()));
  for(const auto& image:actor->images)total=gpu_sum(total,gpu_resource(image.Get()));return total;
 }
 UINT64 content_gpu_bytes(ID3D12Resource* base,const TextureGpu* layer,const ShadowGpu* shadow,const CharacterGpu* actor)const noexcept{
  UINT64 total=gpu_resource(base);
  for(const auto& buffer:transient_buffers)total=gpu_sum(total,gpu_resource(buffer.Get()));
  for(const auto& buffer:lighting_buffers)total=gpu_sum(total,gpu_resource(buffer.Get()));
  if(layer){total=gpu_sum(total,gpu_resource(layer->vertices.Get()));for(const auto& image:layer->images)total=gpu_sum(total,gpu_resource(image.Get()));}
  if(shadow)total=gpu_sum(total,gpu_resource(shadow->texture.Get()));
  return gpu_sum(total,character_gpu_bytes(actor));
 }
 UINT64 planned_content_gpu_bytes(const SceneMesh& base,const TexturedScene& layer,const SceneLighting& lighting,
                                  const CharacterMesh* replacement_mesh,const CharacterAsset* replacement,bool preserve_character)const{
  // Existing upload stages synchronously complete their own submitted work.
  // Query their exact descriptors before entering those stages so a budget
  // rejection cannot submit, wait, increment counters or replace any resource.
  UINT64 total=content_gpu_bytes(nullptr,nullptr,nullptr,preserve_character?character.get():nullptr);
  const auto charge=[&](const D3D12_RESOURCE_DESC& desc){total=gpu_sum(total,gpu_allocation(desc));};
  if(!base.vertices.empty())charge(buffer_description(base.vertices.size()*sizeof(SceneVertex)));
  if(!layer.vertices.empty()){
   charge(buffer_description(layer.vertices.size()*sizeof(TexturedVertex)));
   for(const auto& image:layer.images){D3D12_RESOURCE_DESC d{};d.Dimension=D3D12_RESOURCE_DIMENSION_TEXTURE2D;d.Width=image.levels.front().width;d.Height=image.levels.front().height;d.DepthOrArraySize=1;d.MipLevels=static_cast<UINT16>(image.levels.size());d.Format=image.semantic==ImageSemantic::srgb_color?DXGI_FORMAT_R8G8B8A8_UNORM_SRGB:DXGI_FORMAT_R8G8B8A8_UNORM;d.SampleDesc.Count=1;charge(d);}
  }
  const auto controls=pack_scene_lighting(lighting).controls;
  if(controls[0]&&controls[2]){
   if(directional_shadow&&directional_shadow->resolution==lighting.shadow.resolution)total=gpu_sum(total,gpu_resource(directional_shadow->texture.Get()));
   else{D3D12_RESOURCE_DESC d{};d.Dimension=D3D12_RESOURCE_DIMENSION_TEXTURE2D;d.Width=lighting.shadow.resolution;d.Height=lighting.shadow.resolution;d.DepthOrArraySize=1;d.MipLevels=1;d.Format=DXGI_FORMAT_R32_TYPELESS;d.SampleDesc.Count=1;d.Flags=D3D12_RESOURCE_FLAG_ALLOW_DEPTH_STENCIL;charge(d);}
  }
  if(replacement_mesh){
   const auto cost=character_mesh_cost(*replacement_mesh);charge(buffer_description(cost.gpu_vertex_bytes));charge(buffer_description(cost.gpu_index_bytes));
   for(UINT frame=0;frame<frame_count;++frame)charge(buffer_description(character_constant_bytes));
   const auto image_charge=[&](UINT width,UINT height,UINT16 mips){D3D12_RESOURCE_DESC d{};d.Dimension=D3D12_RESOURCE_DIMENSION_TEXTURE2D;d.Width=width;d.Height=height;d.DepthOrArraySize=1;d.MipLevels=mips;d.Format=DXGI_FORMAT_R8G8B8A8_UNORM_SRGB;d.SampleDesc.Count=1;charge(d);};
   if(replacement)for(const auto& image:replacement->images)image_charge(image.levels.front().width,image.levels.front().height,static_cast<UINT16>(image.levels.size()));
   image_charge(1,1,1); // The separately owned opaque fallback SRV is mandatory.
  }
  return total;
 }
 static void enforce_content_gpu_bytes(UINT64 total,UINT64 maximum){
  if(total==UINT64_MAX||total>maximum)throw std::invalid_argument("Candidate committed chapter GPU resources exceed the remaining content budget");
 }
 void verify_content_gpu_plan(UINT64 planned,ID3D12Resource* base,const TextureGpu* layer,const ShadowGpu* shadow,const CharacterGpu* actor)const{
  // Driver-normalized resource descriptions must agree with the exact input
  // allocation queries. A mismatch is an internal/driver invariant failure,
  // not late budget admission after an upload has already completed.
  if(content_gpu_bytes(base,layer,shadow,actor)!=planned)throw std::runtime_error("Staged GPU resource allocations differ from their admitted exact descriptor plan");
 }
 BaseGpu stage_base_mesh(const SceneMesh& scene) {
  validate_mesh(scene);
  ComPtr<ID3D12Resource> candidate;
  D3D12_VERTEX_BUFFER_VIEW candidate_view{};
  const auto candidate_count = static_cast<UINT>(scene.vertices.size());
  if (candidate_count != 0) {
   const auto bytes = static_cast<UINT64>(scene.vertices.size() * sizeof(SceneVertex));
   const auto buffer = buffer_description(bytes); const auto heap = heap_properties(D3D12_HEAP_TYPE_UPLOAD);
   checked(device->CreateCommittedResource(&heap,D3D12_HEAP_FLAG_NONE,&buffer,D3D12_RESOURCE_STATE_GENERIC_READ,nullptr,IID_PPV_ARGS(&candidate)), "Replacement vertex buffer");
   void* mapped = nullptr; const D3D12_RANGE empty{0,0};
   checked(candidate->Map(0,&empty,&mapped), "Replacement vertex buffer map");
   std::memcpy(mapped,scene.vertices.data(),static_cast<std::size_t>(bytes)); candidate->Unmap(0,nullptr);
   candidate_view = {candidate->GetGPUVirtualAddress(),static_cast<UINT>(bytes),static_cast<UINT>(sizeof(SceneVertex))};
  }
  return {std::move(candidate),candidate_view,candidate_count};
 }
 void replace_scene(const SceneMesh& scene) {
  require_healthy();
  validate_mesh(scene);
  if(scene.vertices.size()>1000000-textured_vertex_count())throw std::invalid_argument("Combined base/textured geometry exceeds one million vertices");
  auto candidate=stage_base_mesh(scene);
  idle();
  vertex_buffer.Swap(candidate.buffer);
  vertex_view = candidate.view;
  vertex_count = candidate.count;
  ++statistics.scene_replacements;
 }
 void replace_resources(const SceneMesh& base,const TexturedScene& layer){
  require_healthy();
  validate_mesh(base);validate_textured_scene(layer);
  if(layer.vertices.size()>1000000-base.vertices.size())throw std::invalid_argument("Combined scene resource geometry budget");
  auto geometry=stage_base_mesh(base);auto candidate=stage_textured(layer);idle();
  vertex_buffer.Swap(geometry.buffer);vertex_view=geometry.view;vertex_count=geometry.count;textures.swap(candidate);++statistics.scene_replacements;
 }
 void replace_resources(const SceneMesh& base,const TexturedScene& layer,const SceneLighting& lighting,UINT64 maximum=UINT64_MAX){
  require_healthy();validate_mesh(base);validate_textured_scene(layer);validate_scene_lighting(lighting);
  if(layer.vertices.size()>1000000-base.vertices.size())throw std::invalid_argument("Combined scene resource geometry budget");
  const auto planned=planned_content_gpu_bytes(base,layer,lighting,nullptr,nullptr,true);enforce_content_gpu_bytes(planned,maximum);
  auto staged_lighting=stage_lighting(lighting);auto geometry=stage_base_mesh(base);auto candidate=stage_textured(layer);
  if(candidate){auto handle=candidate->heap->GetCPUDescriptorHandleForHeapStart();handle.ptr+=candidate->images.size()*device->GetDescriptorHandleIncrementSize(D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV);shadow_descriptor(staged_lighting.shadow?staged_lighting.shadow->texture.Get():nullptr,handle);}
  auto character_descriptors=stage_character_shadow(staged_lighting.shadow?staged_lighting.shadow->texture.Get():nullptr);
  verify_content_gpu_plan(planned,geometry.buffer.Get(),candidate.get(),staged_lighting.shadow.get(),character.get());
  idle();vertex_buffer.Swap(geometry.buffer);vertex_view=geometry.view;vertex_count=geometry.count;textures.swap(candidate);publish_character_shadow(character_descriptors);publish_lighting(staged_lighting);++statistics.scene_replacements;
 }
 void replace_resources(const SceneMesh& base,const TexturedScene& layer,const SceneLighting& lighting,const CharacterMesh* mesh,UINT64 maximum=UINT64_MAX){
  require_healthy();validate_mesh(base);validate_textured_scene(layer);validate_scene_lighting(lighting);if(mesh)validate_character_mesh(*mesh);
  if(layer.vertices.size()>1000000-base.vertices.size())throw std::invalid_argument("Combined scene resource geometry budget");
  const auto planned=planned_content_gpu_bytes(base,layer,lighting,mesh,nullptr,false);enforce_content_gpu_bytes(planned,maximum);
  auto staged_lighting=stage_lighting(lighting);auto geometry=stage_base_mesh(base);auto candidate=stage_textured(layer);auto staged_character=mesh?stage_character(*mesh):std::unique_ptr<CharacterGpu>{};
  if(candidate){auto handle=candidate->heap->GetCPUDescriptorHandleForHeapStart();handle.ptr+=candidate->images.size()*device->GetDescriptorHandleIncrementSize(D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV);shadow_descriptor(staged_lighting.shadow?staged_lighting.shadow->texture.Get():nullptr,handle);}
  if(staged_character)staged_character->heap=character_heap_with_shadow(*staged_character,staged_lighting.shadow?staged_lighting.shadow->texture.Get():nullptr);
  verify_content_gpu_plan(planned,geometry.buffer.Get(),candidate.get(),staged_lighting.shadow.get(),staged_character.get());
  // Nothing above publishes logical resources. A final drain also covers
  // all old scenery consumers when no new character upload was needed.
  idle();vertex_buffer.Swap(geometry.buffer);vertex_view=geometry.view;vertex_count=geometry.count;textures.swap(candidate);publish_lighting(staged_lighting);publish_character(staged_character);++statistics.scene_replacements;
 }
 void replace_resources_asset(const SceneMesh& base,const TexturedScene& layer,const SceneLighting& lighting,const CharacterAsset* asset,UINT64 maximum=UINT64_MAX){
  require_healthy();validate_mesh(base);validate_textured_scene(layer);validate_scene_lighting(lighting);if(asset)validate_character_asset(*asset);
  if(layer.vertices.size()>1000000-base.vertices.size())throw std::invalid_argument("Combined scene resource geometry budget");
  const auto planned=planned_content_gpu_bytes(base,layer,lighting,asset?&asset->mesh:nullptr,asset,false);enforce_content_gpu_bytes(planned,maximum);
  auto staged_lighting=stage_lighting(lighting);auto geometry=stage_base_mesh(base);auto candidate=stage_textured(layer);auto staged_character=asset?stage_character(asset->mesh,asset):std::unique_ptr<CharacterGpu>{};
  if(candidate){auto handle=candidate->heap->GetCPUDescriptorHandleForHeapStart();handle.ptr+=candidate->images.size()*device->GetDescriptorHandleIncrementSize(D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV);shadow_descriptor(staged_lighting.shadow?staged_lighting.shadow->texture.Get():nullptr,handle);}
  if(staged_character)staged_character->heap=character_heap_with_shadow(*staged_character,staged_lighting.shadow?staged_lighting.shadow->texture.Get():nullptr);
  verify_content_gpu_plan(planned,geometry.buffer.Get(),candidate.get(),staged_lighting.shadow.get(),staged_character.get());
  idle();vertex_buffer.Swap(geometry.buffer);vertex_view=geometry.view;vertex_count=geometry.count;textures.swap(candidate);publish_lighting(staged_lighting);publish_character(staged_character);++statistics.scene_replacements;
 }
 void initialize(const SceneMesh& scene, const std::filesystem::path& shader_directory, RenderValidationMode validation) {
  if(validation!=RenderValidationMode::enable_if_available&&validation!=RenderValidationMode::do_not_enable)
   throw std::invalid_argument("Unknown renderer validation mode");
  texture_shaders=shader_directory;
  validate_mesh(scene);
  ComPtr<ID3D12Debug> debug;
  if (validation==RenderValidationMode::enable_if_available&&SUCCEEDED(D3D12GetDebugInterface(IID_PPV_ARGS(&debug)))) { debug->EnableDebugLayer(); statistics.debug_layer = true; }
  HRESULT result = CreateDXGIFactory2(statistics.debug_layer ? DXGI_CREATE_FACTORY_DEBUG : 0, IID_PPV_ARGS(&factory));
  if (FAILED(result)) checked(CreateDXGIFactory2(0, IID_PPV_ARGS(&factory)), "Create DXGI factory");
  for (UINT index = 0; ; ++index) {
   ComPtr<IDXGIAdapter1> candidate;
   result = factory->EnumAdapterByGpuPreference(index, DXGI_GPU_PREFERENCE_HIGH_PERFORMANCE, IID_PPV_ARGS(&candidate));
   if (result == DXGI_ERROR_NOT_FOUND) break;
   checked(result, "Enumerate GPU");
   DXGI_ADAPTER_DESC1 description{}; checked(candidate->GetDesc1(&description), "Adapter description");
   if ((description.Flags & DXGI_ADAPTER_FLAG_SOFTWARE) != 0) continue;
   if (SUCCEEDED(D3D12CreateDevice(candidate.Get(),D3D_FEATURE_LEVEL_11_0,IID_PPV_ARGS(&device)))) {
    adapter = candidate; statistics.adapter = utf8(description.Description); statistics.vendor_id = description.VendorId; statistics.device_id = description.DeviceId; break;
   }
  }
  if (!device) throw std::runtime_error("No hardware Direct3D 12 adapter found");
  // Each frame owns one fixed upload buffer. A frame's fence must complete
  // before that buffer is mapped again; ordinary draws never allocate or idle.
  const auto transient_bytes = static_cast<UINT64>(Dx12Renderer::transient_vertex_limit) * sizeof(SceneVertex);
  const auto transient_description = buffer_description(transient_bytes);
  const auto transient_heap = heap_properties(D3D12_HEAP_TYPE_UPLOAD);
  for (UINT index = 0; index < frame_count; ++index) {
   checked(device->CreateCommittedResource(&transient_heap,D3D12_HEAP_FLAG_NONE,&transient_description,
     D3D12_RESOURCE_STATE_GENERIC_READ,nullptr,IID_PPV_ARGS(&transient_buffers[index])), "Transient frame vertex buffer");
   transient_views[index] = {transient_buffers[index]->GetGPUVirtualAddress(),static_cast<UINT>(transient_bytes),static_cast<UINT>(sizeof(SceneVertex))};
   ++statistics.transient_buffer_allocations;
  }
  const D3D_FEATURE_LEVEL levels[] = {D3D_FEATURE_LEVEL_12_2,D3D_FEATURE_LEVEL_12_1,D3D_FEATURE_LEVEL_12_0,D3D_FEATURE_LEVEL_11_1,D3D_FEATURE_LEVEL_11_0};
  D3D12_FEATURE_DATA_FEATURE_LEVELS features{static_cast<UINT>(std::size(levels)), levels, D3D_FEATURE_LEVEL_11_0};
  checked(device->CheckFeatureSupport(D3D12_FEATURE_FEATURE_LEVELS,&features,sizeof(features)), "Feature level query");
  statistics.feature_level = std::to_string((static_cast<unsigned>(features.MaxSupportedFeatureLevel) >> 12) & 0xf) + "." + std::to_string((static_cast<unsigned>(features.MaxSupportedFeatureLevel) >> 8) & 0xf);
  if (statistics.debug_layer) checked(device.As(&info), "Debug info queue");
  else { (void)device.As(&info); statistics.debug_layer=static_cast<bool>(info); }
  D3D12_COMMAND_QUEUE_DESC queue_description{}; queue_description.Type = D3D12_COMMAND_LIST_TYPE_DIRECT;
  checked(device->CreateCommandQueue(&queue_description,IID_PPV_ARGS(&queue)), "Command queue");
  width = window.width(); height = window.height();
  DXGI_SWAP_CHAIN_DESC1 swap{}; swap.Width = width; swap.Height = height; swap.Format = DXGI_FORMAT_R8G8B8A8_UNORM;
  // Sequential flip retains the completed buffer for explicit post-present
  // readback. Discarding flip would make that capture content unspecified.
  swap.SampleDesc.Count = 1; swap.BufferUsage = DXGI_USAGE_RENDER_TARGET_OUTPUT; swap.BufferCount = frame_count; swap.SwapEffect = DXGI_SWAP_EFFECT_FLIP_SEQUENTIAL;
  ComPtr<IDXGISwapChain1> temporary;
  checked(factory->CreateSwapChainForHwnd(queue.Get(),static_cast<HWND>(window.native_handle()),&swap,nullptr,nullptr,&temporary), "Native swapchain");
  checked(temporary.As(&swapchain), "Swapchain interface");
  checked(factory->MakeWindowAssociation(static_cast<HWND>(window.native_handle()), DXGI_MWA_NO_ALT_ENTER), "Window association");
  D3D12_DESCRIPTOR_HEAP_DESC descriptors{}; descriptors.NumDescriptors = frame_count*2; descriptors.Type = D3D12_DESCRIPTOR_HEAP_TYPE_RTV;
  checked(device->CreateDescriptorHeap(&descriptors,IID_PPV_ARGS(&rtv_heap)), "RTV descriptors");
  descriptors.NumDescriptors = 1; descriptors.Type = D3D12_DESCRIPTOR_HEAP_TYPE_DSV;
  checked(device->CreateDescriptorHeap(&descriptors,IID_PPV_ARGS(&dsv_heap)), "DSV descriptors");
  descriptor_size = device->GetDescriptorHandleIncrementSize(D3D12_DESCRIPTOR_HEAP_TYPE_RTV);
  surfaces();
  for (auto& allocator : allocators) checked(device->CreateCommandAllocator(D3D12_COMMAND_LIST_TYPE_DIRECT,IID_PPV_ARGS(&allocator)), "Command allocator");
  lighting_initialize();
  D3D12_DESCRIPTOR_RANGE shadow_range{};shadow_range.RangeType=D3D12_DESCRIPTOR_RANGE_TYPE_SRV;shadow_range.NumDescriptors=1;shadow_range.BaseShaderRegister=1;
  D3D12_ROOT_PARAMETER parameters[3]{}; parameters[0].ParameterType = D3D12_ROOT_PARAMETER_TYPE_32BIT_CONSTANTS; parameters[0].Constants.Num32BitValues = 16; parameters[0].Constants.ShaderRegister = 0; parameters[0].ShaderVisibility = D3D12_SHADER_VISIBILITY_VERTEX;
  parameters[1].ParameterType=D3D12_ROOT_PARAMETER_TYPE_CBV;parameters[1].Descriptor.ShaderRegister=2;parameters[1].ShaderVisibility=D3D12_SHADER_VISIBILITY_PIXEL;
  parameters[2].ParameterType=D3D12_ROOT_PARAMETER_TYPE_DESCRIPTOR_TABLE;parameters[2].DescriptorTable.NumDescriptorRanges=1;parameters[2].DescriptorTable.pDescriptorRanges=&shadow_range;parameters[2].ShaderVisibility=D3D12_SHADER_VISIBILITY_PIXEL;
  const auto comparison_sampler=shadow_sampler();
  D3D12_ROOT_SIGNATURE_DESC root_description{}; root_description.NumParameters = 3; root_description.pParameters = parameters;root_description.NumStaticSamplers=1;root_description.pStaticSamplers=&comparison_sampler; root_description.Flags = D3D12_ROOT_SIGNATURE_FLAG_ALLOW_INPUT_ASSEMBLER_INPUT_LAYOUT;
  ComPtr<ID3DBlob> signature, errors;
  checked(D3D12SerializeRootSignature(&root_description,D3D_ROOT_SIGNATURE_VERSION_1,&signature,&errors), "Root signature serialization");
  checked(device->CreateRootSignature(0,signature->GetBufferPointer(),signature->GetBufferSize(),IID_PPV_ARGS(&root)), "Root signature");
  const auto vertex_shader = read_shader(shader_directory / "motherboard.vs.cso"), pixel_shader = read_shader(shader_directory / "motherboard.ps.cso");
  const D3D12_INPUT_ELEMENT_DESC layout[] = {
   {"POSITION",0,DXGI_FORMAT_R32G32B32_FLOAT,0,0,D3D12_INPUT_CLASSIFICATION_PER_VERTEX_DATA,0},
   {"NORMAL",0,DXGI_FORMAT_R32G32B32_FLOAT,0,12,D3D12_INPUT_CLASSIFICATION_PER_VERTEX_DATA,0},
   {"COLOR",0,DXGI_FORMAT_R32G32B32_FLOAT,0,24,D3D12_INPUT_CLASSIFICATION_PER_VERTEX_DATA,0},
   {"TEXCOORD",0,DXGI_FORMAT_R32_FLOAT,0,36,D3D12_INPUT_CLASSIFICATION_PER_VERTEX_DATA,0}};
  D3D12_GRAPHICS_PIPELINE_STATE_DESC state{}; state.pRootSignature = root.Get();
  state.VS = {vertex_shader.data(),vertex_shader.size()}; state.PS = {pixel_shader.data(),pixel_shader.size()};
  state.BlendState.RenderTarget[0].SrcBlend = D3D12_BLEND_ONE; state.BlendState.RenderTarget[0].DestBlend = D3D12_BLEND_ZERO;
  state.BlendState.RenderTarget[0].BlendOp = D3D12_BLEND_OP_ADD; state.BlendState.RenderTarget[0].SrcBlendAlpha = D3D12_BLEND_ONE;
  state.BlendState.RenderTarget[0].DestBlendAlpha = D3D12_BLEND_ZERO; state.BlendState.RenderTarget[0].BlendOpAlpha = D3D12_BLEND_OP_ADD;
  state.BlendState.RenderTarget[0].LogicOp = D3D12_LOGIC_OP_NOOP; state.BlendState.RenderTarget[0].RenderTargetWriteMask = D3D12_COLOR_WRITE_ENABLE_ALL;
  state.SampleMask = UINT_MAX; state.RasterizerState.FillMode = D3D12_FILL_MODE_SOLID; state.RasterizerState.CullMode = D3D12_CULL_MODE_NONE; state.RasterizerState.DepthClipEnable = TRUE;
  state.DepthStencilState.DepthEnable = TRUE; state.DepthStencilState.DepthWriteMask = D3D12_DEPTH_WRITE_MASK_ALL; state.DepthStencilState.DepthFunc = D3D12_COMPARISON_FUNC_LESS;
  state.InputLayout = {layout,static_cast<UINT>(std::size(layout))}; state.PrimitiveTopologyType = D3D12_PRIMITIVE_TOPOLOGY_TYPE_TRIANGLE;
  state.NumRenderTargets = 1; state.RTVFormats[0] = DXGI_FORMAT_R8G8B8A8_UNORM; state.DSVFormat = DXGI_FORMAT_D32_FLOAT; state.SampleDesc.Count = 1;
  checked(device->CreateGraphicsPipelineState(&state,IID_PPV_ARGS(&pipeline)), "Graphics pipeline");
  checked(device->CreateCommandList(0,D3D12_COMMAND_LIST_TYPE_DIRECT,allocators[0].Get(),pipeline.Get(),IID_PPV_ARGS(&commands)), "Graphics command list");
  checked(commands->Close(), "Initial command-list close");
  checked(device->CreateFence(0,D3D12_FENCE_FLAG_NONE,IID_PPV_ARGS(&fence)), "GPU fence");
  fence_event = CreateEventW(nullptr,FALSE,FALSE,nullptr);
  if (!fence_event) throw std::runtime_error("Could not create GPU fence event");
  replace_scene(scene);
 }
 RenderStats stats() const {
  auto result = statistics;
  result.scene_active_gpu_bytes=content_gpu_bytes(vertex_buffer.Get(),textures.get(),directional_shadow.get(),character.get());

  if (info) {
   const auto count = info->GetNumStoredMessagesAllowedByRetrievalFilter();
   for (UINT64 i = 0; i < count; ++i) {
    SIZE_T size = 0; if (FAILED(info->GetMessage(i,nullptr,&size))) continue;
    std::vector<unsigned char> storage(size); auto* message = reinterpret_cast<D3D12_MESSAGE*>(storage.data());
    if (FAILED(info->GetMessage(i,message,&size))) continue;
    if (message->Severity == D3D12_MESSAGE_SEVERITY_ERROR || message->Severity == D3D12_MESSAGE_SEVERITY_CORRUPTION) ++result.debug_errors;
    if (message->Severity == D3D12_MESSAGE_SEVERITY_WARNING) ++result.debug_warnings;
    if(message->Severity<=D3D12_MESSAGE_SEVERITY_WARNING&&result.debug_messages.size()<32){
     std::string description;
     if(message->pDescription&&message->DescriptionByteLength){description.assign(message->pDescription,std::min<std::size_t>(message->DescriptionByteLength,2048));if(!description.empty()&&description.back()=='\0')description.pop_back();}
     result.debug_messages.push_back("DX12 message "+std::to_string(static_cast<unsigned>(message->ID))+": "+description);
    }
   }
  }
  return result;
 }
};

Dx12Renderer::Dx12Renderer(NativeWindow& window, const SceneMesh& scene, const std::filesystem::path& shaders)
 :Dx12Renderer(window,scene,shaders,RenderValidationMode::enable_if_available) {}
Dx12Renderer::Dx12Renderer(NativeWindow& window, const SceneMesh& scene, const std::filesystem::path& shaders, RenderValidationMode validation)
 :impl_(std::make_unique<Impl>(window)) { Impl::reap_retired();impl_->initialize(scene,shaders,validation); }
Dx12Renderer::~Dx12Renderer() {
 if(impl_&&!impl_->shutdown_safe())Impl::retire(impl_.release());
 Impl::reap_retired();
}
void Dx12Renderer::wait_idle() { impl_->idle(); }
void Dx12Renderer::set_scene(const SceneMesh& scene) { impl_->replace_scene(scene); }
void Dx12Renderer::set_textured_scene(const TexturedScene& scene) { impl_->replace_textured(scene); }
void Dx12Renderer::set_scene(const SceneMesh& base,const TexturedScene& layer) {impl_->replace_resources(base,layer);}
void Dx12Renderer::set_lighting(const SceneLighting& lighting){impl_->replace_lighting(lighting);}
void Dx12Renderer::set_scene(const SceneMesh& base,const TexturedScene& layer,const SceneLighting& lighting){impl_->replace_resources(base,layer,lighting);}
void Dx12Renderer::set_scene_bounded(const SceneMesh& base,const TexturedScene& layer,const SceneLighting& lighting,std::uint64_t maximum){impl_->replace_resources(base,layer,lighting,maximum);}
void Dx12Renderer::set_character(const CharacterMesh& mesh){impl_->replace_character(&mesh);}
void Dx12Renderer::set_character_asset(const CharacterAsset& asset){impl_->replace_character_asset(asset);}
void Dx12Renderer::clear_character(){impl_->replace_character(nullptr);}
void Dx12Renderer::set_scene(const SceneMesh& base,const TexturedScene& layer,const SceneLighting& lighting,const CharacterMesh* mesh){impl_->replace_resources(base,layer,lighting,mesh);}
void Dx12Renderer::set_scene_character_bounded(const SceneMesh& base,const TexturedScene& layer,const SceneLighting& lighting,const CharacterMesh* mesh,std::uint64_t maximum){impl_->replace_resources(base,layer,lighting,mesh,maximum);}
void Dx12Renderer::set_scene_character_asset(const SceneMesh& base,const TexturedScene& layer,const SceneLighting& lighting,const CharacterAsset* asset){impl_->replace_resources_asset(base,layer,lighting,asset);}
void Dx12Renderer::set_scene_character_asset_bounded(const SceneMesh& base,const TexturedScene& layer,const SceneLighting& lighting,const CharacterAsset* asset,std::uint64_t maximum){impl_->replace_resources_asset(base,layer,lighting,asset,maximum);}
void Dx12Renderer::resize(std::uint32_t width, std::uint32_t height) {
 impl_->require_healthy();
 if (!width || !height || impl_->window.minimized() || (width == impl_->width && height == impl_->height)) return;
 if (width > 8192 || height > 8192) throw std::invalid_argument("Renderer dimensions exceed 8192");
 impl_->idle();
 impl_->capture_valid = false;
 for (auto& target : impl_->targets) target.Reset(); impl_->depth.Reset();
 checked(impl_->swapchain->ResizeBuffers(Impl::frame_count,width,height,DXGI_FORMAT_R8G8B8A8_UNORM,0), "Resize swapchain");
 impl_->width = width; impl_->height = height; impl_->surfaces();
 for (auto& value : impl_->frame_fences) value = 0;
}
void Dx12Renderer::render(const Camera& camera) {
 render(camera, {});
}
void Dx12Renderer::render(const Camera& camera, const SceneMesh& transient) {
 render_frame(camera,transient,nullptr);
}
void Dx12Renderer::render(const Camera& camera,const SceneMesh& transient,const CharacterInstance& character){
 render_frame(camera,transient,&character);
}
void Dx12Renderer::render_frame(const Camera& camera,const SceneMesh& transient,const CharacterInstance* instance){
 impl_->require_healthy();
 if (transient.vertices.size() > transient_vertex_limit) throw std::invalid_argument("Transient geometry exceeds 4096 vertices");
 validate_mesh(transient);
 // Reject a malformed pose before resizing, mapping a frame buffer, or
 // recording commands. This preserves the previous completed frame.
 Impl::CharacterConstants character_constants{};std::array<float,16> matrix{};
 if(instance){
  const auto width=impl_->window.width(),height=impl_->window.height();
  if(impl_->window.minimized()||!width||!height)character_constants=impl_->prepare_character(*instance);
  else{
   matrix=camera.view_projection(static_cast<float>(width)/static_cast<float>(height));
   character_constants=impl_->prepare_character(*instance,&matrix);
  }
  character_constants.camera_world={camera.position.x,camera.position.y,camera.position.z,0};
 }
 if (impl_->window.minimized() || !impl_->window.width() || !impl_->window.height()) return;
 resize(impl_->window.width(),impl_->window.height());
 auto& r = *impl_;
 if(!instance)matrix=camera.view_projection(static_cast<float>(r.width)/static_cast<float>(r.height));
 const UINT index = r.swapchain->GetCurrentBackBufferIndex(); r.wait(r.frame_fences[index]);
 r.prepare_hud(index);
 r.upload_lighting(index);
 const bool draw_character=instance&&instance->opacity>0;
 if(draw_character)r.upload_character(index,character_constants);
 const auto transient_count = static_cast<UINT>(transient.vertices.size());
 auto transient_view = r.transient_views[index];
 if (transient_count != 0) {
  const auto bytes = transient.vertices.size() * sizeof(SceneVertex);
  void* mapped = nullptr; const D3D12_RANGE empty{0,0};
  checked(r.transient_buffers[index]->Map(0,&empty,&mapped), "Transient frame buffer map");
  std::memcpy(mapped,transient.vertices.data(),bytes);
  const D3D12_RANGE written{0,bytes}; r.transient_buffers[index]->Unmap(0,&written);
  transient_view.SizeInBytes = static_cast<UINT>(bytes);
 }
 checked(r.allocators[index]->Reset(), "Reset frame allocator"); checked(r.commands->Reset(r.allocators[index].Get(),r.pipeline.Get()), "Reset frame commands");
 r.shadow_pass(transient_count,transient_view);
 r.commands->SetPipelineState(r.pipeline.Get());
 r.commands->SetGraphicsRootSignature(r.root.Get());
 r.commands->SetGraphicsRoot32BitConstants(0,16,matrix.data(),0);
 r.commands->SetGraphicsRootConstantBufferView(1,r.lighting_buffers[index]->GetGPUVirtualAddress());
 ID3D12DescriptorHeap* lighting_heaps[]={r.lighting_heap.Get()};r.commands->SetDescriptorHeaps(1,lighting_heaps);r.commands->SetGraphicsRootDescriptorTable(2,r.lighting_heap->GetGPUDescriptorHandleForHeapStart());
 const D3D12_VIEWPORT viewport{0,0,static_cast<float>(r.width),static_cast<float>(r.height),0,1}; const D3D12_RECT scissor{0,0,static_cast<LONG>(r.width),static_cast<LONG>(r.height)};
 r.commands->RSSetViewports(1,&viewport); r.commands->RSSetScissorRects(1,&scissor);
 auto barrier = transition(r.targets[index].Get(),D3D12_RESOURCE_STATE_PRESENT,D3D12_RESOURCE_STATE_RENDER_TARGET); r.commands->ResourceBarrier(1,&barrier);
 auto color = r.rtv_heap->GetCPUDescriptorHandleForHeapStart(); color.ptr += static_cast<SIZE_T>(index) * r.descriptor_size;
 const auto depth = r.dsv_heap->GetCPUDescriptorHandleForHeapStart(); r.commands->OMSetRenderTargets(1,&color,FALSE,&depth);
 r.commands->ClearRenderTargetView(color,Impl::clear_color,0,nullptr); r.commands->ClearDepthStencilView(depth,D3D12_CLEAR_FLAG_DEPTH,1,0,0,nullptr);
 if (r.vertex_count != 0) {
  r.commands->IASetPrimitiveTopology(D3D_PRIMITIVE_TOPOLOGY_TRIANGLELIST); r.commands->IASetVertexBuffers(0,1,&r.vertex_view); r.commands->DrawInstanced(r.vertex_count,1,0,0);
 }
 if (transient_count != 0) {
  r.commands->IASetPrimitiveTopology(D3D_PRIMITIVE_TOPOLOGY_TRIANGLELIST); r.commands->IASetVertexBuffers(0,1,&transient_view); r.commands->DrawInstanced(transient_count,1,0,0);
 }
 r.draw_textured(matrix,index);
 if(draw_character)r.draw_character(matrix,index);
 r.finish_with_hud(index);
 checked(r.commands->Close(), "Close frame commands"); ID3D12CommandList* lists[] = {r.commands.Get()}; r.queue->ExecuteCommandLists(1,lists);
 try{checked(r.swapchain->Present(1,0), "Present");}catch(...){r.submissions.poison();throw;}
 r.frame_fences[index] = r.signal_queue();
 r.last_target = index; ++r.statistics.frames; r.capture_valid = true;
 if (transient_count != 0) ++r.statistics.transient_frames;
 if(draw_character)++r.statistics.character_frames;
}
std::uint64_t Dx12Renderer::capture(const std::filesystem::path& path) {
 auto& r = *impl_;r.require_healthy(); if (r.statistics.frames == 0) throw std::runtime_error("No GPU frame available for capture"); r.idle();
 D3D12_PLACED_SUBRESOURCE_FOOTPRINT footprint{}; UINT rows = 0; UINT64 row_size = 0, total = 0;
 const auto texture = r.targets[r.last_target]->GetDesc(); r.device->GetCopyableFootprints(&texture,0,1,0,&footprint,&rows,&row_size,&total);
 const auto buffer = buffer_description(total); const auto heap = heap_properties(D3D12_HEAP_TYPE_READBACK); ComPtr<ID3D12Resource> readback;
 checked(r.device->CreateCommittedResource(&heap,D3D12_HEAP_FLAG_NONE,&buffer,D3D12_RESOURCE_STATE_COPY_DEST,nullptr,IID_PPV_ARGS(&readback)), "Capture readback buffer");
 const UINT index = r.swapchain->GetCurrentBackBufferIndex(); checked(r.allocators[index]->Reset(), "Capture allocator reset"); checked(r.commands->Reset(r.allocators[index].Get(),nullptr), "Capture commands reset");
 auto barrier = transition(r.targets[r.last_target].Get(),D3D12_RESOURCE_STATE_PRESENT,D3D12_RESOURCE_STATE_COPY_SOURCE); r.commands->ResourceBarrier(1,&barrier);
 D3D12_TEXTURE_COPY_LOCATION source{}; source.pResource = r.targets[r.last_target].Get(); source.Type = D3D12_TEXTURE_COPY_TYPE_SUBRESOURCE_INDEX;
 D3D12_TEXTURE_COPY_LOCATION destination{}; destination.pResource = readback.Get(); destination.Type = D3D12_TEXTURE_COPY_TYPE_PLACED_FOOTPRINT; destination.PlacedFootprint = footprint;
 r.commands->CopyTextureRegion(&destination,0,0,0,&source,nullptr); barrier = transition(r.targets[r.last_target].Get(),D3D12_RESOURCE_STATE_COPY_SOURCE,D3D12_RESOURCE_STATE_PRESENT); r.commands->ResourceBarrier(1,&barrier);
 checked(r.commands->Close(), "Capture close commands");
 auto job=std::make_unique<Impl::InFlightResources>();job->readback=readback;
 r.submissions.prepare(std::move(job));
 auto completed=r.submissions.submit_and_wait([&]{ID3D12CommandList* lists[]={r.commands.Get()};r.queue->ExecuteCommandLists(1,lists);},[&]{r.idle();});
 void* mapped = nullptr; const D3D12_RANGE range{0,static_cast<SIZE_T>(total)}; checked(readback->Map(0,&range,&mapped), "Map captured pixels");
 std::vector<unsigned char> pixels(static_cast<std::size_t>(r.width) * r.height * 4); std::uint64_t nonbackground = 0;
 const auto* source_pixels = static_cast<const unsigned char*>(mapped);
 for (UINT y = 0; y < r.height; ++y) for (UINT x = 0; x < r.width; ++x) {
  const auto* input = source_pixels + footprint.Offset + static_cast<SIZE_T>(y)*footprint.Footprint.RowPitch + static_cast<SIZE_T>(x)*4;
  auto* output = pixels.data() + (static_cast<std::size_t>(y)*r.width+x)*4; output[0] = input[2]; output[1] = input[1]; output[2] = input[0]; output[3] = 255;
  if (std::abs(static_cast<int>(input[0])-4)>4 || std::abs(static_cast<int>(input[1])-6)>4 || std::abs(static_cast<int>(input[2])-9)>4) ++nonbackground;
 }
 const D3D12_RANGE empty{0,0}; readback->Unmap(0,&empty);
 BITMAPFILEHEADER file{}; file.bfType = 0x4d42; file.bfOffBits = sizeof(BITMAPFILEHEADER)+sizeof(BITMAPINFOHEADER); file.bfSize = file.bfOffBits+static_cast<DWORD>(pixels.size());
 BITMAPINFOHEADER bitmap{}; bitmap.biSize = sizeof(bitmap); bitmap.biWidth = static_cast<LONG>(r.width); bitmap.biHeight = -static_cast<LONG>(r.height); bitmap.biPlanes = 1; bitmap.biBitCount = 32; bitmap.biCompression = BI_RGB; bitmap.biSizeImage = static_cast<DWORD>(pixels.size());
 std::ofstream output(path,std::ios::binary); output.write(reinterpret_cast<const char*>(&file),sizeof(file)); output.write(reinterpret_cast<const char*>(&bitmap),sizeof(bitmap)); output.write(reinterpret_cast<const char*>(pixels.data()),static_cast<std::streamsize>(pixels.size()));
 if (!output) throw std::runtime_error("Could not write GPU capture"); return nonbackground;
}
bool Dx12Renderer::capture_frame(CapturedFrame& output) {
 auto& r=*impl_;r.require_healthy();
 if(!r.capture_valid||r.window.minimized()||!r.width||!r.height||
    r.window.width()!=r.width||r.window.height()!=r.height)return false;
 const auto bytes=static_cast<std::uint64_t>(r.width)*r.height*4;
 if(bytes>CapturedFrame::maximum_bytes||output.bgra.capacity()>CapturedFrame::maximum_bytes)
  throw std::invalid_argument("Owned capture exceeds its 32MiB slot");
 D3D12_PLACED_SUBRESOURCE_FOOTPRINT footprint{};UINT rows=0;UINT64 row_size=0,total=0;
 const auto texture=r.targets[r.last_target]->GetDesc();
 r.device->GetCopyableFootprints(&texture,0,1,0,&footprint,&rows,&row_size,&total);
 if(texture.Format!=DXGI_FORMAT_R8G8B8A8_UNORM||rows!=r.height||row_size!=static_cast<UINT64>(r.width)*4||
    total>CapturedFrame::maximum_bytes||footprint.Offset>total)
  throw std::invalid_argument("Unsupported owned capture footprint");
 // Reserve before GPU submission; no allocation is performed on steady frames.
 if(output.bgra.capacity()<CapturedFrame::maximum_bytes){
  // Discard an undersized scratch allocation before taking the full slot;
  // reserve must not momentarily own old+new full-frame storage.
  std::vector<std::byte>().swap(output.bgra);
  output.bgra.reserve(CapturedFrame::maximum_bytes);
 }
 if(!r.capture_readback){
  const auto description=buffer_description(CapturedFrame::maximum_bytes);
  const auto heap=heap_properties(D3D12_HEAP_TYPE_READBACK);
  ComPtr<ID3D12Resource> buffer;ComPtr<ID3D12CommandAllocator> allocator;ComPtr<ID3D12GraphicsCommandList> commands;
  checked(r.device->CreateCommittedResource(&heap,D3D12_HEAP_FLAG_NONE,&description,D3D12_RESOURCE_STATE_COPY_DEST,nullptr,IID_PPV_ARGS(&buffer)),"Owned capture readback");
  checked(r.device->CreateCommandAllocator(D3D12_COMMAND_LIST_TYPE_DIRECT,IID_PPV_ARGS(&allocator)),"Owned capture allocator");
  checked(r.device->CreateCommandList(0,D3D12_COMMAND_LIST_TYPE_DIRECT,allocator.Get(),nullptr,IID_PPV_ARGS(&commands)),"Owned capture commands");
  checked(commands->Close(),"Initial owned capture close");
  r.capture_readback=std::move(buffer);r.capture_allocator=std::move(allocator);r.capture_commands=std::move(commands);
  ++r.statistics.capture_buffer_allocations;r.statistics.capture_active_readback_bytes=CapturedFrame::maximum_bytes;
 }
 r.idle();checked(r.capture_allocator->Reset(),"Owned capture allocator reset");
 checked(r.capture_commands->Reset(r.capture_allocator.Get(),nullptr),"Owned capture commands reset");
 auto barrier=transition(r.targets[r.last_target].Get(),D3D12_RESOURCE_STATE_PRESENT,D3D12_RESOURCE_STATE_COPY_SOURCE);
 r.capture_commands->ResourceBarrier(1,&barrier);
 D3D12_TEXTURE_COPY_LOCATION source{};source.pResource=r.targets[r.last_target].Get();source.Type=D3D12_TEXTURE_COPY_TYPE_SUBRESOURCE_INDEX;
 D3D12_TEXTURE_COPY_LOCATION destination{};destination.pResource=r.capture_readback.Get();destination.Type=D3D12_TEXTURE_COPY_TYPE_PLACED_FOOTPRINT;destination.PlacedFootprint=footprint;
 r.capture_commands->CopyTextureRegion(&destination,0,0,0,&source,nullptr);
 barrier=transition(r.targets[r.last_target].Get(),D3D12_RESOURCE_STATE_COPY_SOURCE,D3D12_RESOURCE_STATE_PRESENT);
 r.capture_commands->ResourceBarrier(1,&barrier);checked(r.capture_commands->Close(),"Owned capture close");
 ID3D12CommandList* lists[]={r.capture_commands.Get()};r.queue->ExecuteCommandLists(1,lists);
 // All submitted resources are permanent Impl members. The renderer's existing
 // poison/retirement path retains them if signal/wait fails or the device dies.
 r.wait(r.signal_queue());
 void* mapped=nullptr;const D3D12_RANGE read{0,static_cast<SIZE_T>(total)};
 checked(r.capture_readback->Map(0,&read,&mapped),"Owned capture map");
 output.bgra.resize(static_cast<std::size_t>(bytes));
 const auto* pixels=static_cast<const unsigned char*>(mapped);std::uint64_t nonbackground=0;
 for(UINT y=0;y<r.height;++y)for(UINT x=0;x<r.width;++x){
  const auto* input=pixels+footprint.Offset+static_cast<SIZE_T>(y)*footprint.Footprint.RowPitch+static_cast<SIZE_T>(x)*4;
  auto* out=output.bgra.data()+(static_cast<std::size_t>(y)*r.width+x)*4;
  out[0]=static_cast<std::byte>(input[2]);out[1]=static_cast<std::byte>(input[1]);out[2]=static_cast<std::byte>(input[0]);out[3]=std::byte{255};
  if(std::abs(static_cast<int>(input[0])-4)>4||std::abs(static_cast<int>(input[1])-6)>4||std::abs(static_cast<int>(input[2])-9)>4)++nonbackground;
 }
 const D3D12_RANGE empty{0,0};r.capture_readback->Unmap(0,&empty);
 output.width=r.width;output.height=r.height;output.present_id=r.statistics.frames;output.nonbackground_pixels=nonbackground;
 ++r.statistics.capture_frames;
 return true;
}
RenderStats Dx12Renderer::stats() const { return impl_->stats(); }
}
