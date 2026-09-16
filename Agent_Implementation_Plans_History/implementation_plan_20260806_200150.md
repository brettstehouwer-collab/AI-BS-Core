# Hybrid Spatial Architecture Plan

This plan details how we will upgrade the AI-BS ecosystem to support the "Hybrid Approach" for 3D layout generation. This will allow the system to choose between handing off procedural logic to Unreal Engine, OR having the AI Assistant act as a precise spatial architect that calculates exact 3D coordinates.

## Proposed Changes

### 1. Advanced LLM Spatial Schema
We will upgrade the prompt in `demo_noto.py`. Instead of the AI just returning a flat list of asset names (`spawnActors: ["Chair", "Table"]`), the AI will output a structured spatial array:

```json
"spawnActors": [
  {
    "asset_keyword": "wood table",
    "layout_mode": "ai_transform",
    "transform": {"x": 0, "y": 0, "z": 0, "rotation_z": 0}
  },
  {
    "asset_keyword": "chairs",
    "layout_mode": "engine_procedural",
    "procedural_group": "table_seating"
  }
]
```
This allows the AI to calculate precise layout math (`ai_transform`) for hero pieces, while delegating repetitive tasks (`engine_procedural`) to Unreal Engine.

### 2. Backend Asset Injection
We will modify the secondary lookup loop in `demo_noto.py` to parse these objects. It will perform a database search on `asset_keyword`, find the true Unreal package path, and inject it into the object as `package_path` before sending it to the frontend.

### 3. Frontend UI Upgrades (`BanquetArchitectTab.jsx`)
- **State Migration:** Upgrade the `spawnActors` React state to hold these complex objects instead of flat strings.
- **Visual Nodes:** Update the UI rendering of "Active Spawn Actors" to show the asset name along with a badge indicating its layout mode (e.g., `[AI Transform]` or `[Engine Procedural]`).
- **Manual Search Addition:** When you manually pick an asset using the Asset Browser search, it will default to `engine_procedural` mode, but it will be formatted to match the new schema so it routes perfectly to the engine.

### 4. Remote Control API Payload
When you click "Sync to 3D", the frontend will transmit this advanced array of spatial objects to Unreal Engine. Your blueprint (`SceneController_2`) will now receive the coordinates alongside the asset path, giving it all the data needed to instantly spawn the scene accurately.

## Open Questions

> [!WARNING]
> Please confirm the following design decisions:
> 1. Is the proposed JSON schema for `spawnActors` acceptable for your Unreal Engine Blueprint parsing logic, or do you need the fields named differently (e.g. `location_x` instead of just `x`)?
> 2. When you manually add an asset via the search bar, should it default to `engine_procedural` (Unreal handles it) or `ai_transform` (spawn at 0,0,0)?

## Verification
- Test manual addition via Asset Browser to ensure the object schema is constructed properly.
- Test voice/text NLP command (e.g., "spawn a table and put a chair next to it") to verify the LLM calculates transform coordinates and passes them correctly through the backend.
