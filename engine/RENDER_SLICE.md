# Native PC rendering slice — SDK 0.3.0

## Implemented boundary

`AIBS::Platform` owns a Win32 window and PC input with focus/capture handling, close, DPI setup and resize/minimize lifecycle. Its public interface hides HWND behind an opaque native handle and pimpl. `AIBS::Render` owns the DX12 device, hardware adapter selection, direct command queue, two-buffer flip-sequential swapchain, RTV/DSV resources, depth buffer, shaders, vertex data, command allocators/lists, resource transitions and fences. The SDK exports these targets alongside the existing core/world/authoring/persistence targets.

The scene is real triangle geometry generated from boxes: PCB/traces, CPU socket and lid, four memory towers, slots, storage fins, chipset/capacitors and an RTX-inspired X-frame/fan landmark. Directional diffuse shading and emissive-looking colors provide the initial visual proof. This is not PBR, actual light propagation, a CAD replica or game progression. Camera controls use keyboard movement, right-drag look, elevation and sprint; there is no collision or player character yet.

The standalone native `aibs_motherboard` executable loads compiled shaders beside itself. It requires no browser, Qt, Python, HTTP service, model provider, Unity or Unreal to render. The installed SDK consumer links the new targets and exercises geometry/camera contracts without creating a graphics device.

## Build choices and compatibility

The approved candidate plan proposed SDL3 for windows/input. This slice uses an **interim Win32 adapter** because the existing Windows SDK already supplies all needed interfaces; it introduces no unpinned package or extra runtime. Requirement: owned native PC platform/rendering boundary. Compatibility: public pimpl interfaces leave a later SDL3 backend possible; no SDL3 behavior or cross-platform support is claimed. Status: scoped implemented alternative for the first Windows proof, preserving the larger platform roadmap.

HLSL is compiled offline using Windows SDK 10.0.26100.0's DXC: `dxcompiler.dll 1.8.2502.11`, vertex/pixel shader model 6.0, strict warnings. CMake finds DXC or accepts `AIBS_DXC`. Output `.cso` files are installed under `bin/shaders`; the runtime does not load a shader compiler DLL. GPU capture uses explicit render-target-to-readback copies. Flip-sequential intentionally retains post-present buffer contents for that capture.

The source SDK version advances from 0.2.0 to 0.3.0; clients rebuild against matching MSVC/configuration. Existing checkpoint format 1 is unchanged. No stable plugin binary ABI is promised. Standard Windows/MSVC runtime availability was verified on this development PC; a clean-machine installer/minimum-hardware matrix remains future work.

## Verification observed on this PC

- NVIDIA GeForce RTX 4090, vendor 4318, device 9860, DX12 feature level 12.2.
- WMI driver version observed: 32.0.16.2101. The AMD integrated adapter was enumerated but was not the exercised renderer.
- Fifteen rendered frames, three resize/recreation cycles, minimized submission suspended and restored, completed fence waits, GPU readback 960×640 containing 317,660 non-background pixels.
- Windows Graphics Tools was initially missing. It was installed successfully without reboot. Subsequent native Debug and Release self-tests exercised the D3D12 debug layer with zero reported errors and warnings. Earlier false/zero records are not treated as debug validation.
- Shader compilation and library compilation passed MSVC `/W4 /WX /permissive-`.
- Camera/geometry tests validate movement, finite data, pitch limits and bad inputs. Existing identity/save/continuity tests remain part of the same run.
- The copied renderer/shaders were also executed from the deployed Studio's bundled game-assets directory on the RTX 4090. The packaged Studio game workspace passed a separate real-Qt frozen smoke check.

The lifecycle tests cover the exercised paths, not arbitrary device removal, repeated multi-hour stress, all drivers/displays or GPU-based validation. The current graphics scene is not extracted from CreatorSession; persistent world-to-render mapping and visible editing are the next integration step.

## Commands and artifacts

From the repository root:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File engine/scripts/verify.ps1 -Configuration Debug
powershell.exe -NoProfile -ExecutionPolicy Bypass -File engine/scripts/verify.ps1 -Configuration Release
& engine/install/release/bin/aibs_motherboard.exe
```

Headless hardware/lifecycle test:

```powershell
& engine/install/release/bin/aibs_motherboard.exe --self-test --capture engine/out/motherboard-render.bmp --report engine/out/renderer_verification.json
```

The monitor reads `renderer_verification.json`, public hosting readback evidence, local checkpoints and storage metrics. Hosted WebGL smoke evidence is separate from native DX12 evidence. Source/evidence archives exclude the large generated build trees and private project materials.
