# New Unreal Project: The Bad Side Upside Down

Based on the provided screenplay by Julie Stehouwer, the goal is to initialize a new Unreal Engine project (or a new dedicated level within the existing `UnrealHub`) to bring "The Bad Side Upside Down" to life. This will involve setting up the environment, the unique character models (Weeble Wobbles), and the necessary AI-BS bridge scripts.

## User Review Required

> [!IMPORTANT]
> **Project Structure:** Do you want to create a completely new `.uproject` from scratch for this screenplay, or should we create a new **Level/Map** inside the existing `AI_BS_Hub.uproject`? Creating a new level in the existing hub is generally faster and shares the existing Remote Control API configuration.

> [!WARNING]
> **Weeble Wobble Characters:** The script specifies that characters are "WEEBLES WOBBLE FIGURES". We will need to either generate these 3D assets, use placeholder capsule meshes with custom physics, or rely on a specific asset pack if you have one. 

## Open Questions

1. **Environment Setup:** The scene requires a split environment (Heaven vs. Hell on opposite sides of a Candy Store). Should the AI agents use the `unreal_bridge_new.py` to spawn this procedurally, or should we generate an Editor Python script to build the static set?
2. **Audio/TTS:** Do we need to integrate Text-to-Speech (TTS) for the dialogue in the script so the characters can act out the cold open?
3. **Save Point / Context Switch:** I will create a `SAVED_CHECKPOINT.md` to safely pause the previous onboarding work so we can focus entirely on this screenplay project.

## Proposed Changes

---

### 1. Project & Scene Scaffolding

#### [NEW] `c:\AI-BS\screenplay_projects\The_Bad_Side_Upside_Down\scene_builder.py`
- Create a Python script meant to be run inside Unreal Engine (via Editor Utility or Remote Control).
- This script will block out the environment:
  - **Center:** The Candy Store storefront.
  - **Left Side (Hell):** Red fire flames and a furnace.
  - **Right Side (Heaven):** White clouds, blue sky, white picket fence, and a house.

#### [NEW] `c:\AI-BS\screenplay_projects\The_Bad_Side_Upside_Down\character_spawner.py`
- Script to spawn the placeholder Weeble Wobble characters (Fredy, Satan, Jesus, Disturbed, Mr. Pimp) at their designated marks.
- Configures physics constraints so they "wobble" but don't fall over.

---

### 2. Backend & AI-BS Bridge Updates

#### [MODIFY] `c:\AI-BS\backend\routers\unreal_bridge_new.py`
- Add a specific route/function to load the "Bad Side Upside Down" environment layout.
- Ensure the bridge supports triggering character dialogue animations.

#### [MODIFY] `c:\AI-BS\backend\tools\tool_registry.py`
- Register `load_screenplay_scene` tool so the LLM agents can instantly switch the active Unreal level to the Candy Store exterior.

---

### 3. Ledger & Ecosystem Updates

#### [MODIFY] `c:\AI-BS\SAVED_CHECKPOINT.md`
- Save the current state of the Smart Client Onboarding Portal.
- Generate a new resume keyword for when we return to the web dashboard.

#### [MODIFY] `c:\AI-BS\AI_BS_MASTER_ARCHITECTURAL_LEDGER.md`
- Document the creation of the screenplay-to-Unreal pipeline.

#### [MODIFY] `c:\AI-BS\docs\AI_BS_MASTER_ECOSYSTEM_MANUAL.md`
- Add a new section detailing how screenplays (like Julie's) are ingested into the AI-BS 3D Hub.

## Verification Plan

### Automated Tests
- Parse the `The Bad Side Upside Down.md` file using Python to extract the character list and automatically format the JSON payload for the Unreal Bridge.

### Manual Verification
1. Execute the `scene_builder.py` script via the AI-BS Unreal Bridge.
2. Visually confirm in the Unreal Editor (or via Pixel Streaming) that the split Heaven/Hell storefront is generated.
3. Spawn the Weeble Wobble placeholders and verify their positioning.
