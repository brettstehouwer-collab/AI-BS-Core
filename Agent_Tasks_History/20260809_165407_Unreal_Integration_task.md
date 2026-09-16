# Unreal Engine Integration Tasks

- `[x]` 1. Refactor Backend Unreal Bridge
  - `[x]` Update `c:\AI-BS\backend\routers\unreal_bridge_new.py` to support `spawn_asset`, `set_environment`, and `execute_script`.
- `[x]` 2. Update Tool Registry
  - `[x]` Add `spawn_3d_object` tool to `c:\AI-BS\backend\tools\tool_registry.py`.
  - `[x]` Add `update_3d_lighting` tool.
- `[x]` 3. Frontend 3D Integration
  - `[x]` Create `c:\AI-BS\frontend\src\components\UnrealViewport.jsx`.
  - `[x]` Update `c:\AI-BS\frontend\App.jsx` to include the 2D/3D toggle and viewport.
- `[x]` 4. Launch Script Improvements
  - `[x]` Add port health checks for 30010 and 8888 in `c:\AI-BS\Launch_AI_BS.bat`.
