# 🎮 Unreal Engine 5 Pre-Viz Pipeline Expansion

By leveraging our AI backend and Unreal Engine's Python API, we can completely automate the "blocking" phase of virtual production. Here is a list of advanced tools we can build to bridge AI-BS and Unreal Engine 5:

## 1. Automated Audio Generation & Audio Tracks (The "Temp Track" Builder)
- **What it does**: AI-BS uses a Text-to-Speech (TTS) engine to generate `.wav` files for every line of dialogue in your script. 
- **In Unreal**: The Python script automatically imports these `.wav` files and physically places them on an Audio Track inside the Sequencer Timeline at the exact right timestamps.
- **Why it's cool**: You get instant rough timing for the whole scene without needing voice actors.

## 2. Smart Camera Spawner (The AI Cinematographer)
- **What it does**: We feed the script's Action lines to LLaMA 3 and ask it to guess the camera angles (e.g., *Wide Shot*, *Close-Up*, *Over-The-Shoulder*).
- **In Unreal**: The Python script physically spawns `CineCameraActor` objects in the scene, names them (e.g., `Cam_CU_John`), adds them to the Sequencer, and creates camera cuts on the Director Track.
- **Why it's cool**: Your timeline is instantly populated with editable cameras.

## 3. Dynamic Lighting & Environment Setup
- **What it does**: The parser reads the Scene Heading (e.g., `EXT. CITY STREET - NIGHT`).
- **In Unreal**: The Python script reads `EXT` and `NIGHT` and automatically spawns a moon directional light, a skylight, and enables Exponential Height Fog. If it reads `INT. - DAY`, it spawns sunlight coming through a directional axis.

## 4. MetaHuman / Character Proxy Binder
- **What it does**: Uses the Character Vault to map characters.
- **In Unreal**: The Python script creates proxy Skeletal Meshes in the sequence (or links to your existing MetaHuman Blueprints if you name them to match the script). It adds them to Sequencer with empty Animation Tracks ready for MoCap dragging and dropping.

## 5. In-Engine Teleprompter (UMG Widget)
- **What it does**: We generate a specific Data Table specifically for a UI Widget.
- **In Unreal**: You get a drag-and-drop UI Blueprint that acts as a Teleprompter on your screen, playing the script text in real-time as the Sequence plays.

## 6. Take Recorder Integration
- **What it does**: Generates a configuration file for Unreal's Virtual Production Take Recorder.
- **In Unreal**: Maps your characters to iOS Live Link Face IDs so you can instantly start acting out the scene with your iPhone.

---

### Implementation Effort
- **Easiest / Fastest**: Dynamic Lighting (Reads INT/EXT/DAY/NIGHT) and Camera Spawner (spawning basic CineCameras).
- **Medium**: Audio Generation (Requires adding TTS to the Python backend to generate the `.wav` files).
- **Advanced**: MetaHuman Binder and Take Recorder Integration.

Which of these pipeline tools sound the most exciting to you? We can implement them one by one!
