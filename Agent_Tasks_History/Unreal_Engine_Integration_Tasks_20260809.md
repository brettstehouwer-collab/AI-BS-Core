# Unreal Engine Integration Tasks

- `[/]` 1. Refactor Backend Unreal Bridge
  - `[ ]` Update `c:\AI-BS\backend\routers\unreal_bridge_new.py` to support `spawn_asset`, `set_environment`, and `execute_script`.
- `[/]` 2. Update Tool Registry
  - `[ ]` Add `spawn_3d_object` tool to `c:\AI-BS\backend\tools\tool_registry.py`.
  - `[ ]` Add `update_3d_lighting` tool.
- `[ ]` 3. Frontend 3D Integration
  - `[ ]` Create `c:\AI-BS\frontend\src\components\UnrealViewport.jsx`.
  - `[ ]` Update `c:\AI-BS\frontend\src\App.jsx` to include the 2D/3D toggle and viewport.
- `[ ]` 4. Launch Script Improvements
  - `[ ]` Add port health checks for 30010 and 8888 in `c:\AI-BS\Launch_AI_BS.bat`.
