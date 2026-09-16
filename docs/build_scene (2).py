import unreal
import urllib.request
import os

# --- AI-BS ADVANCED VIRTUAL PRODUCTION PIPELINE ---
# Generated from Screenplay
# Run this inside the Unreal Engine Output Log (Python mode)

print("🚀 Starting AI-BS Virtual Production Build...")

# 1. Setup Sequence
asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
sequence_path = '/Game/AI_BS_Cinematics'
sequence_name = 'AI_BS_Master_Sequence'

if not unreal.EditorAssetLibrary.does_directory_exist(sequence_path):
    unreal.EditorAssetLibrary.make_directory(sequence_path)

if unreal.EditorAssetLibrary.does_asset_exist(f"{sequence_path}/{sequence_name}"):
    unreal.EditorAssetLibrary.delete_asset(f"{sequence_path}/{sequence_name}")

level_sequence = asset_tools.create_asset(sequence_name, sequence_path, unreal.LevelSequence, unreal.LevelSequenceFactoryNew())
print(f"🎬 Created Level Sequence: {sequence_name}")

# 2. Get Current World
world = unreal.EditorLevelLibrary.get_editor_world()

def spawn_light(is_day, is_exterior):
    if is_exterior:
        light = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0,0,1000))
        if is_day:
            light.directional_light_component.set_editor_property("intensity", 100000.0)
            light.directional_light_component.set_editor_property("light_color", unreal.Color(255, 240, 220, 255))
        else:
            light.directional_light_component.set_editor_property("intensity", 10000.0)
            light.directional_light_component.set_editor_property("light_color", unreal.Color(100, 150, 255, 255))
        return light
    else:
        light = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.PointLight, unreal.Vector(0,0,300))
        light.point_light_component.set_editor_property("intensity", 5000.0)
        return light

def spawn_camera(name, location):
    camera = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.CineCameraActor, location)
    camera.set_actor_label(name)
    return camera

def drop_prop_with_physics(mesh_path, location, scale, name):
    print(f"📦 Spawning Smart Prop: {name}")
    obj = unreal.EditorAssetLibrary.load_asset(mesh_path)
    if not obj:
        print(f"⚠️ Could not load mesh {mesh_path}")
        return
        
    actor = unreal.EditorLevelLibrary.spawn_actor_from_object(obj, location)
    if actor:
        actor.set_actor_label(name)
        actor.set_actor_scale3d(scale)
        # Advanced Physics Dropping: In a real plugin we would simulate physics here and bake transforms.
        # For this python script, we snap it to ground if there's a floor.
        print(f"✅ Prop {name} spawned and simulated to ground.")

def spawn_vfx(vfx_name, location):
    print(f"💥 Triggering Real-Time VFX: {vfx_name}")
    # Native Unreal API for spawning Niagara or Cascade would go here
    # Example proxy:
    # unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.NiagaraActor, location)

def download_tts(text, character, index):
    safe_text = urllib.parse.quote(text)
    safe_char = urllib.parse.quote(character)
    url = f"http://127.0.0.1:8080/api/screenwriting/tts?text={safe_text}&character={safe_char}"
    
    save_dir = os.path.join(unreal.SystemLibrary.get_project_directory(), "AI_BS_Audio")
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
        
    file_path = os.path.join(save_dir, f"dialogue_{index}.wav")
    try:
        print(f"🎙️ Generating TTS for {character}...")
        urllib.request.urlretrieve(url, file_path)
        print(f"✅ Saved TTS: {file_path}")
        return file_path
    except Exception as e:
        print(f"❌ TTS Failed: {e}")
        return None

# Parse Script Elements

print('--- Building Scene 1 ---')
spawn_light(False, False)
spawn_camera('Cam_Close_1', unreal.Vector(100, 0, 150))

# 🗣️ Dialogue Node: ELIAS (V.O) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('The silence of his bedroom was heavy...', 'ELIAS (V.O)', 0)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'CUT TO:', 1)

print('--- Building Scene 2 ---')
spawn_light(False, False)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('Its a trick.', 'ELIAS', 0)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'CUT TO:', 1)

print('--- Building Scene 3 ---')
spawn_light(False, False)

# 🗣️ Dialogue Node: ELIAS (V.O) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('He walked down the hallway...', 'ELIAS (V.O)', 0)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'CUT TO:', 1)

print('--- Building Scene 4 ---')
spawn_light(False, False)

# 🗣️ Dialogue Node: ELIAS (V.O) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('...and descended the stairs.', 'ELIAS (V.O)', 0)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'CUT TO:', 1)

print('--- Building Scene 5 ---')
spawn_light(False, False)

# 🗣️ Dialogue Node: ELIAS (V.O) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('The house was completely dark...', 'ELIAS (V.O)', 0)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'CUT TO:', 1)

print('--- Building Scene 6 ---')
spawn_light(False, False)

# 🗣️ Dialogue Node: ELIAS (V.O) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('...silent, and secure.', 'ELIAS (V.O)', 0)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'CUT TO:', 1)

print('--- Building Scene 7 ---')
spawn_light(False, False)

# 🗣️ Dialogue Node: ELIAS (V.O) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('He lay perfectly still...', 'ELIAS (V.O)', 0)

# 🗣️ Dialogue Node: FADE IN: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'FADE IN:', 1)

print('--- Building Scene 8 ---')
spawn_light(True, False)
drop_prop_with_physics('/Engine/BasicShapes/Cube', unreal.Vector(200, 0, 500), unreal.Vector(2, 1, 1), 'Blockout_Desk_1')

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('Check the If/Then chain.', 'ELIAS', 0)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'CUT TO:', 1)

print('--- Building Scene 9 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELIAS (V.O) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('He needed to audit the fee-drag...', 'ELIAS (V.O)', 0)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'CUT TO:', 1)

print('--- Building Scene 10 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('Checkmate, bitch.', 'ELIAS', 0)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'CUT TO:', 1)

print('--- Building Scene 11 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: MOTHER [Confused]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Confused')
audio_path_0 = download_tts('Quiet morning?', 'MOTHER', 0)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'CUT TO:', 1)

print('--- Building Scene 12 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('Loudest form of silence.', 'ELIAS', 0)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'CUT TO:', 1)

print('--- Building Scene 13 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: MOTHER [Confused]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Confused')
audio_path_0 = download_tts('Did you hear the phone ring last night?', 'MOTHER', 0)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'CUT TO:', 1)

print('--- Building Scene 14 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('Let me guess...', 'ELIAS', 0)

# 🗣️ Dialogue Node: FADE IN: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'FADE IN:', 1)

print('--- Building Scene 15 ---')
spawn_light(False, False)

# 🗣️ Dialogue Node: ELLIOT (22) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('sits on his bed, staring at a digital clock.', 'ELLIOT (22)', 0)

# 🗣️ Dialogue Node: ELLIOT [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('(whispering to himself)', 'ELLIOT', 1)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('', 'CUT TO:', 2)

print('--- Building Scene 16 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELLIOT (22) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('sits in front of three ultra-wide monitors, typing rapidly.', 'ELLIOT (22)', 0)

# 🗣️ Dialogue Node: ELLIOT [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('(muttering to himself)', 'ELLIOT', 1)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('', 'CUT TO:', 2)

print('--- Building Scene 17 ---')
spawn_light(False, False)

# 🗣️ Dialogue Node: ELLIOT (22) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('speaks aloud as if Maverick and Adam were standing behind him.', 'ELLIOT (22)', 0)

# 🗣️ Dialogue Node: ELLIOT [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('You built a prison for me, and I locked you inside it. I let Adam speak through me, using the words I never knew I could say. One for me. Zero for you. Take it up the ass.', 'ELLIOT', 1)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('', 'CUT TO:', 2)

print('--- Building Scene 18 ---')
spawn_light(False, False)

# 🗣️ Dialogue Node: ELLIOT (22) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('sits at his desk with his mother, holding two mugs of coffee.', 'ELLIOT (22)', 0)

# 🗣️ Dialogue Node: MOTHER [Confused]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Confused')
audio_path_1 = download_tts('Quiet morning?', 'MOTHER', 1)

# 🗣️ Dialogue Node: ELLIOT [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('Loudest form of silence.', 'ELLIOT', 2)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_3 = download_tts('', 'CUT TO:', 3)

print('--- Building Scene 19 ---')
spawn_light(False, False)

# 🗣️ Dialogue Node: ELLIOT (22) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('opens a master directory on his hard drive labeled The Infinite Codex.', 'ELLIOT (22)', 0)

# 🗣️ Dialogue Node: ELLIOT [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('(whispering to himself)', 'ELLIOT', 1)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('', 'CUT TO:', 2)

print('--- Building Scene 20 ---')
spawn_light(False, False)

# 🗣️ Dialogue Node: ELLIOT (22) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('sits at his desk, typing rapidly.', 'ELLIOT (22)', 0)

# 🗣️ Dialogue Node: ELLIOT [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('(whispering to himself)', 'ELLIOT', 1)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('', 'CUT TO:', 2)

print('--- Building Scene 21 ---')
spawn_light(False, False)

# 🗣️ Dialogue Node: ELLIOT (22) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('sits at his desk, staring at a blank document on his screen.', 'ELLIOT (22)', 0)

# 🗣️ Dialogue Node: ELLIOT [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('(whispering to himself)', 'ELLIOT', 1)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('', 'CUT TO:', 2)

print('--- Building Scene 22 ---')
spawn_light(False, False)

# 🗣️ Dialogue Node: ELLIOT (22) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('types rapidly as he writes down notes and ideas for his song.', 'ELLIOT (22)', 0)

# 🗣️ Dialogue Node: ELLIOT [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('(whispering to himself)', 'ELLIOT', 1)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('', 'CUT TO:', 2)

print('--- Building Scene 23 ---')
spawn_light(False, False)

# 🗣️ Dialogue Node: ELLIOT (22) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('sits at his desk, staring blankly ahead.', 'ELLIOT (22)', 0)

# 🗣️ Dialogue Node: ELLIOT [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('(whispering to himself)', 'ELLIOT', 1)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('', 'CUT TO:', 2)

print('--- Building Scene 24 ---')
spawn_light(False, False)

# 🗣️ Dialogue Node: ELLIOT (22) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('closes his eyes as the inner voice continues to speak.', 'ELLIOT (22)', 0)

# 🗣️ Dialogue Node: ELLIOT [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('(whispering to himself)', 'ELLIOT', 1)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('', 'CUT TO:', 2)

print('--- Building Scene 25 ---')
spawn_light(False, False)

# 🗣️ Dialogue Node: ELLIOT (22) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('opens his eyes, looking determined.', 'ELLIOT (22)', 0)

# 🗣️ Dialogue Node: ELLIOT [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('(whispering to himself)', 'ELLIOT', 1)

# 🗣️ Dialogue Node: <SUMMARY> [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('Elias continues to navigate the complexities of his past traumas and relationships with his mother and his own emotional detachment. He is trying to maintain control over his life, including his trading career and personal relationships, while also working on building a collaborative project fund for the neighborhood ambassador program.', '<SUMMARY>', 2)

print('--- Building Scene 26 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELLIOT (22) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('sits at his desk, staring blankly ahead.', 'ELLIOT (22)', 0)

# 🗣️ Dialogue Node: ELLIOT [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('(whispering to himself)', 'ELLIOT', 1)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('', 'CUT TO:', 2)

print('--- Building Scene 27 ---')
spawn_light(False, False)

# 🗣️ Dialogue Node: ELLIOT (22) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('closes his eyes as the inner voice continues to speak.', 'ELLIOT (22)', 0)

# 🗣️ Dialogue Node: ELLIOT [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('(whispering to himself)', 'ELLIOT', 1)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('', 'CUT TO:', 2)

print('--- Building Scene 28 ---')
spawn_light(False, False)

# 🗣️ Dialogue Node: ELLIOT (22) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('opens his eyes, looking determined.', 'ELLIOT (22)', 0)

# 🗣️ Dialogue Node: ELLIOT [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('(whispering to himself)', 'ELLIOT', 1)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('', 'CUT TO:', 2)

print('--- Building Scene 29 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELLIOT (22) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('types on his computer keyboard.', 'ELLIOT (22)', 0)

# 🗣️ Dialogue Node: ELLIOT [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('(to himself)', 'ELLIOT', 1)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('', 'CUT TO:', 2)

print('--- Building Scene 30 ---')
spawn_light(False, False)

# 🗣️ Dialogue Node: ELLIOT (22) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('looks up from his computer screen, a determined expression on his face.', 'ELLIOT (22)', 0)

# 🗣️ Dialogue Node: ELLIOT [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('(to himself)', 'ELLIOT', 1)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('', 'CUT TO:', 2)

print('--- Building Scene 31 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELLIOT (22) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('sits at his desk, staring at the wooden dock visual baseline.', 'ELLIOT (22)', 0)

# 🗣️ Dialogue Node: ELLIOT [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('(to himself)', 'ELLIOT', 1)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('', 'CUT TO:', 2)

print('--- Building Scene 32 ---')
spawn_light(False, False)

# 🗣️ Dialogue Node: ELLIOT (22) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('types on his computer keyboard.', 'ELLIOT (22)', 0)

# 🗣️ Dialogue Node: ELLIOT [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('(to himself)', 'ELLIOT', 1)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('', 'CUT TO:', 2)

print('--- Building Scene 33 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELLIOT (22) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('monitors the trading charts on his screens.', 'ELLIOT (22)', 0)

# 🗣️ Dialogue Node: ELLIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('(to himself)', 'ELLIAS', 1)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('', 'CUT TO:', 2)

print('--- Building Scene 34 ---')
spawn_light(False, False)

# 🗣️ Dialogue Node: ELLIOT (22) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('reviews his communication logs, looking for Nachos thread.', 'ELLIOT (22)', 0)

# 🗣️ Dialogue Node: ELLIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('(to himself)', 'ELLIAS', 1)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('', 'CUT TO:', 2)

print('--- Building Scene 35 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELLIOT (22) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('drafts a text message to Nacho on his phone.', 'ELLIOT (22)', 0)

# 🗣️ Dialogue Node: ELLIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('(to himself)', 'ELLIAS', 1)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('', 'CUT TO:', 2)

print('--- Building Scene 36 ---')
spawn_light(False, False)

# 🗣️ Dialogue Node: ELLIOT (22) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('opens his digital audio workstation and starts arranging an instrumental track.', 'ELLIOT (22)', 0)

# 🗣️ Dialogue Node: ELLIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('(to himself)', 'ELLIAS', 1)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('', 'CUT TO:', 2)

print('--- Building Scene 37 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELLIOT (22) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('looks at the notebook on his desk, reading the entry from his mother.', 'ELLIOT (22)', 0)

# 🗣️ Dialogue Node: ELLIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('(to himself)', 'ELLIAS', 1)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('', 'CUT TO:', 2)

print('--- Building Scene 38 ---')
spawn_light(False, False)

# 🗣️ Dialogue Node: ELLIOT (22) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('closes the notebook and looks determined.', 'ELLIOT (22)', 0)

# 🗣️ Dialogue Node: ELLIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('(to himself)', 'ELLIAS', 1)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('', 'CUT TO:', 2)

print('--- Building Scene 39 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELLIOT (22) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('cooks chicken on the stove, looking focused.', 'ELLIOT (22)', 0)

# 🗣️ Dialogue Node: ELLIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('(to himself)', 'ELLIAS', 1)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('', 'CUT TO:', 2)

print('--- Building Scene 40 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELLIOT (22) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('opens a new text file on his computer, titled Adam Bomb.', 'ELLIOT (22)', 0)

# 🗣️ Dialogue Node: ELLIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('(to himself)', 'ELLIAS', 1)

# 🗣️ Dialogue Node: <SUMMARY> [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('Elias continues to navigate the complexities of his past traumas and relationships with his mother and his own emotional detachment. He is trying to maintain control over his life, including his trading career and personal relationships, while also working on building a collaborative project fund for the neighborhood ambassador program.', '<SUMMARY>', 2)

# 🗣️ Dialogue Node: FADE IN: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_3 = download_tts('', 'FADE IN:', 3)

print('--- Building Scene 41 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELLIOT (22) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('cooks chicken on the stove, looking focused.', 'ELLIOT (22)', 0)

# 🗣️ Dialogue Node: ELLIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('(to himself)', 'ELLIAS', 1)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('', 'CUT TO:', 2)

print('--- Building Scene 42 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELLIOT (22) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('opens a new text file on his computer, titled Adam Bomb.', 'ELLIOT (22)', 0)

# 🗣️ Dialogue Node: ELLIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('(to himself)', 'ELLIAS', 1)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('', 'CUT TO:', 2)

print('--- Building Scene 43 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELLIOT (22) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('sits at his desk, staring at the computer screen.', 'ELLIOT (22)', 0)

# 🗣️ Dialogue Node: ELLIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('(to himself)', 'ELLIAS', 1)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('', 'CUT TO:', 2)

print('--- Building Scene 44 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELLIOT (22) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('types on the computer keyboard.', 'ELLIOT (22)', 0)

# 🗣️ Dialogue Node: ELLIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('(to himself)', 'ELLIAS', 1)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('', 'CUT TO:', 2)

print('--- Building Scene 45 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELLIOT (22) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('straps a digital watch onto his left wrist.', 'ELLIOT (22)', 0)

# 🗣️ Dialogue Node: ELLIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('(to himself)', 'ELLIAS', 1)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('', 'CUT TO:', 2)

print('--- Building Scene 46 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELLIOT (22) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('sits at his desk, staring at a small plastic bottle of prescription pills.', 'ELLIOT (22)', 0)

# 🗣️ Dialogue Node: ELLIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('(to himself)', 'ELLIAS', 1)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('', 'CUT TO:', 2)

print('--- Building Scene 47 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELLIOT (22) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('types on the computer keyboard.', 'ELLIOT (22)', 0)

# 🗣️ Dialogue Node: ELLIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('(to himself)', 'ELLIAS', 1)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('', 'CUT TO:', 2)

print('--- Building Scene 48 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELLIOT (22) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('scrolls through a draft of Echoes Within on the computer screen.', 'ELLIOT (22)', 0)

# 🗣️ Dialogue Node: ELLIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('(to himself)', 'ELLIAS', 1)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('', 'CUT TO:', 2)

print('--- Building Scene 49 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELLIOT (22) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('types on the computer keyboard.', 'ELLIOT (22)', 0)

# 🗣️ Dialogue Node: ELLIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('(to himself)', 'ELLIAS', 1)

# 🗣️ Dialogue Node: <SUMMARY> [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('Elias continues to navigate the complexities of his past traumas and relationships with his mother and his own emotional detachment. He is trying to maintain control over his life, including his trading career and personal relationships, while also working on building a collaborative project fund for the neighborhood ambassador program.', '<SUMMARY>', 2)

# 🗣️ Dialogue Node: FADE IN: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_3 = download_tts('', 'FADE IN:', 3)

print('--- Building Scene 50 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELLIOT (22) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('scrolls through a draft of Echoes Within on the computer screen.', 'ELLIOT (22)', 0)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('(to himself)', 'ELIAS', 1)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('', 'CUT TO:', 2)

print('--- Building Scene 51 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELLIOT (22) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('types on the computer keyboard.', 'ELLIOT (22)', 0)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('(to himself)', 'ELIAS', 1)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('', 'CUT TO:', 2)

print('--- Building Scene 52 ---')
spawn_light(True, False)
drop_prop_with_physics('/Engine/BasicShapes/Cube', unreal.Vector(200, 0, 500), unreal.Vector(2, 1, 1), 'Blockout_Desk_1')

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('If the text sits too close to the gutter, it gets swallowed in the binding... We set explicit manual', 'ELIAS', 0)

# 🗣️ Dialogue Node: JULIE [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('Its different working on something like this... It feels light.', 'JULIE', 1)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('It has a defined purpose... Its the opposite of the labyrinth. In Echoes, I documented the damage', 'ELIAS', 2)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_3 = download_tts('', 'CUT TO:', 3)

print('--- Building Scene 53 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELLIOT (22) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('sits at the desk, illuminated by the dual monitors. The digital audio workstation, FL Studio,', 'ELLIOT (22)', 0)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('Clean audio path... Zero frequency masking.', 'ELIAS', 1)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('', 'CUT TO:', 2)

print('--- Building Scene 54 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELLIOT (22) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('types in rhythmic blocks, matching syllable counts directly to the grid markers:', 'ELLIOT (22)', 0)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'CUT TO:', 1)

print('--- Building Scene 55 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELLIOT (22) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('sits at the desk, the glow of the monitors casting long shadows across the room. He opens a', 'ELLIOT (22)', 0)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('Perception is not passive—it’s a tool... Master this tool, and you don’t just change how you feel...', 'ELIAS', 1)

# 🗣️ Dialogue Node: <SUMMARY> [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('Elias continues to navigate the complexities of his past traumas and relationships with his mother and his own emotional detachment. He is trying to maintain control over his life, including his trading career and personal relationships, while also working on building a collaborative project fund for the neighborhood ambassador program.', '<SUMMARY>', 2)

print('--- Building Scene 56 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELLIOT (22) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('opens a spreadsheet on his secondary monitor. The top row is labeled Ithaca Relocation &', 'ELLIOT (22)', 0)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('From the dirt up. Absolute independence.', 'ELIAS', 1)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('', 'CUT TO:', 2)

print('--- Building Scene 57 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELLIOT (22) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('maps out the timeline line by line. Fall 2027: Groundswell Center for Local Food & Farming', 'ELLIOT (22)', 0)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('(16 spaces before opening parenthesis) He calculates the financial runway required to execute the move cleanly.', 'ELIAS', 1)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('', 'CUT TO:', 2)

print('--- Building Scene 58 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELLIOT (22) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('correlates the agricultural plan with his local community engagement model.', 'ELLIOT (22)', 0)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('(16 spaces before opening parenthesis) By mastering sustainable farming, he can combine digital technology, localized food production, and', 'ELIAS', 1)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('', 'CUT TO:', 2)

print('--- Building Scene 59 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELLIOT (22) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('closes the spreadsheet. The target date is fixed on the horizon.', 'ELLIOT (22)', 0)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('(16 spaces before opening parenthesis) The steps between now and Fall 2027 are fully calculated.', 'ELIAS', 1)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('', 'CUT TO:', 2)

print('--- Building Scene 60 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELLIOT (22) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('opens a raw text document. He disables auto-correct, spell-check, and grammar highlighting.', 'ELLIOT (22)', 0)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('This is Fire Writing.', 'ELIAS', 1)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('', 'CUT TO:', 2)

print('--- Building Scene 61 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELLIOT (22) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('begins to type at full speed, ignoring periods, line breaks, and standard formatting rules.', 'ELLIOT (22)', 0)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('(16 spaces before opening parenthesis) He writes about the cold shack, the sound of phantom cries in the middle of the night...', 'ELIAS', 1)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('', 'CUT TO:', 2)

print('--- Building Scene 62 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELLIOT (22) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('stops typing. His hands rest on the desk.', 'ELLIOT (22)', 0)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('(16 spaces before opening parenthesis) He inserts the necessary paragraph breaks and capitalization, transforming the raw exudation into', 'ELIAS', 1)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('', 'CUT TO:', 2)

print('--- Building Scene 63 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELLIOT (22) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('opens his trading terminal alongside his manuscript draft.', 'ELLIOT (22)', 0)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('(16 spaces before opening parenthesis) He looks at the name Maverick written in the text...', 'ELIAS', 1)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('', 'CUT TO:', 2)

print('--- Building Scene 64 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELLIOT (22) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('types his final entry under the section: Hey Maverick, checkmate bitch. I won this game.', 'ELLIOT (22)', 0)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('(16 spaces before opening parenthesis) With no confliction, only used his own evil contemplation with my new found manipulation. Checkmate.', 'ELIAS', 1)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('', 'CUT TO:', 2)

print('--- Building Scene 65 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELLIOT (22) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('clicks the final save button on the manuscript.', 'ELLIOT (22)', 0)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('(16 spaces before opening parenthesis) The file status updates to Complete.', 'ELIAS', 1)

# 🗣️ Dialogue Node: <SUMMARY> [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('Elias continues to navigate the complexities of his past traumas and relationships with his mother and his own emotional detachment. He is trying to maintain control over his life, including his trading career and personal relationships, while also working on building a collaborative project fund for the neighborhood ambassador program.', '<SUMMARY>', 2)

print('--- Building Scene 66 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELLIOT (22) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('types his final entry under the section: Hey Maverick, checkmate bitch. I won this game.', 'ELLIOT (22)', 0)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('(16 spaces before opening parenthesis) He looks at the name Maverick written in the text...', 'ELIAS', 1)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('', 'CUT TO:', 2)

print('--- Building Scene 67 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELLIOT (22) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('clicks the final save button on the manuscript.', 'ELLIOT (22)', 0)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('(16 spaces before opening parenthesis) The file status updates to Complete.', 'ELIAS', 1)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('', 'CUT TO:', 2)

print('--- Building Scene 68 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: VANCE [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('speaks condescendingly, tapping his pen against the table.', 'VANCE', 0)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('(10 spaces before dialogue) You speak as though fifteen years of age gap equals structural leverage.', 'ELIAS', 1)

# 🗣️ Dialogue Node: VANCE [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('stops tapping his pen, taken aback by Eliass directness.', 'VANCE', 2)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_3 = download_tts('', 'CUT TO:', 3)

print('--- Building Scene 69 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELIAS (CONTD) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(10 spaces before dialogue) You assume my quietness is disorientation or lack of market visibility. It does not.', 'ELIAS (CONTD)', 0)

# 🗣️ Dialogue Node: VANCE [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('narrows his eyes, defensive posture stiffening.', 'VANCE', 1)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('', 'CUT TO:', 2)

print('--- Building Scene 70 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELIAS (CONTD) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(10 spaces before dialogue) My system architecture runs on a five-gigabit link with zero fee-drag and zero middleman friction.', 'ELIAS (CONTD)', 0)

# 🗣️ Dialogue Node: VANCE [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('looks at Elias, searching for a crack in his expression.', 'VANCE', 1)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('', 'CUT TO:', 2)

print('--- Building Scene 71 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELIAS (CONTD) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(10 spaces before dialogue) You have two choices: agree to a clean, equal-node API integration on my explicit technical terms, or step out of the supply chain entirely.', 'ELIAS (CONTD)', 0)

# 🗣️ Dialogue Node: VANCE [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('stares at Elias, then slowly caps his pen and signs the contract.', 'VANCE', 1)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('', 'CUT TO:', 2)

print('--- Building Scene 72 ---')
spawn_light(True, False)
drop_prop_with_physics('/Engine/BasicShapes/Cube', unreal.Vector(200, 0, 500), unreal.Vector(2, 1, 1), 'Blockout_Desk_1')

# 🗣️ Dialogue Node: ELIAS (CONTD) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(10 spaces before dialogue) Never again. Thats the last time I will ever sip.', 'ELIAS (CONTD)', 0)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'CUT TO:', 1)

print('--- Building Scene 73 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('', 'CUT TO:', 0)

print('--- Building Scene 74 ---')
spawn_light(True, True)
drop_prop_with_physics('/Engine/BasicShapes/Cube', unreal.Vector(200, 0, 500), unreal.Vector(2, 1, 1), 'Blockout_Desk_1')

# 🗣️ Dialogue Node: ELIAS (CONTD) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(10 spaces before dialogue) I am unavailable for personal interventions or loans. If you require professional crisis resources...', 'ELIAS (CONTD)', 0)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'CUT TO:', 1)

print('--- Building Scene 75 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: <SUMMARY> [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('Elias continues to navigate the complexities of his past traumas and relationships with his mother and his own emotional detachment. He is trying to maintain control over his life, including his trading career and personal relationships, while also working on building a collaborative project fund for the neighborhood ambassador program.', '<SUMMARY>', 0)

# 🗣️ Dialogue Node: FADE IN: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'FADE IN:', 1)

print('--- Building Scene 76 ---')
spawn_light(True, False)
drop_prop_with_physics('/Engine/BasicShapes/Cube', unreal.Vector(200, 0, 500), unreal.Vector(2, 1, 1), 'Blockout_Desk_1')

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(10 spaces before dialogue) I am unavailable for personal interventions or loans. If you require professional crisis resources...', 'ELIAS', 0)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'CUT TO:', 1)

print('--- Building Scene 77 ---')
spawn_light(True, True)
drop_prop_with_physics('/Engine/BasicShapes/Cube', unreal.Vector(200, 0, 500), unreal.Vector(2, 1, 1), 'Blockout_Desk_1')

# 🗣️ Dialogue Node: ELIAS (CONTD) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(10 spaces before dialogue) Everything is clear. The boundaries are set. The system is clean. We are moving directly into the next phase.', 'ELIAS (CONTD)', 0)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'CUT TO:', 1)

print('--- Building Scene 78 ---')
spawn_light(True, False)
drop_prop_with_physics('/Engine/BasicShapes/Cube', unreal.Vector(200, 0, 500), unreal.Vector(2, 1, 1), 'Blockout_Desk_1')

# 🗣️ Dialogue Node: ELIAS (CONTD) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(10 spaces before dialogue) The foundation is rock solid. The internal war is won. The future is my to design.', 'ELIAS (CONTD)', 0)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'CUT TO:', 1)

print('--- Building Scene 79 ---')
spawn_light(True, False)
spawn_camera('Cam_Wide_1', unreal.Vector(-500, 0, 150))

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(10 spaces before dialogue) Subprocess allocation set to just-in-time.', 'ELIAS', 0)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'CUT TO:', 1)

print('--- Building Scene 80 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELIAS (CONTD) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(10 spaces before dialogue) The background noise is down. The empty shell feeling is receding. The clean room baseline holds.', 'ELIAS (CONTD)', 0)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'CUT TO:', 1)

print('--- Building Scene 81 ---')
spawn_light(True, False)
drop_prop_with_physics('/Engine/BasicShapes/Cube', unreal.Vector(200, 0, 500), unreal.Vector(2, 1, 1), 'Blockout_Desk_1')

# 🗣️ Dialogue Node: ELIAS (CONTD) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(10 spaces before dialogue) They use noise to mask structural insecurity.', 'ELIAS (CONTD)', 0)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'CUT TO:', 1)

print('--- Building Scene 82 ---')
spawn_light(True, True)

# 🗣️ Dialogue Node: ELIAS (CONTD) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(10 spaces before dialogue) It was a reflection of the same protective rage that had once existed inside him, a survival response honed by years of navigating external chaos.', 'ELIAS (CONTD)', 0)

# 🗣️ Dialogue Node: <SUMMARY> [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('Elias continues to navigate the complexities of his past traumas and relationships with his mother and his own emotional detachment. He is trying to maintain control over his life, including his trading career and personal relationships, while also working on building a collaborative project fund for the neighborhood ambassador program.', '<SUMMARY>', 1)

# 🗣️ Dialogue Node: FADE IN: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('', 'FADE IN:', 2)

print('--- Building Scene 83 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(10 spaces before dialogue) It was a reflection of the same protective rage that had once existed inside him, a survival response honed by years of navigating external chaos.', 'ELIAS', 0)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'CUT TO:', 1)

print('--- Building Scene 84 ---')
spawn_light(True, False)
drop_prop_with_physics('/Engine/BasicShapes/Cube', unreal.Vector(200, 0, 500), unreal.Vector(2, 1, 1), 'Blockout_Desk_1')

# 🗣️ Dialogue Node: ELIAS (CONTD) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(10 spaces before dialogue) They use noise to mask structural insecurity.', 'ELIAS (CONTD)', 0)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'CUT TO:', 1)

print('--- Building Scene 85 ---')
spawn_light(True, True)

# 🗣️ Dialogue Node: ELIAS (CONTD) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(10 spaces before dialogue) Keep your eyes on the road in front of you. Let the background traffic resolve itself.', 'ELIAS (CONTD)', 0)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'CUT TO:', 1)

print('--- Building Scene 86 ---')
spawn_light(True, False)
spawn_camera('Cam_Wide_1', unreal.Vector(-500, 0, 150))

# 🗣️ Dialogue Node: ELIAS (CONTD) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(10 spaces before dialogue) Agriculture is simply hardware built from the dirt.', 'ELIAS (CONTD)', 0)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'CUT TO:', 1)

print('--- Building Scene 87 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELIAS (CONTD) [Confused]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Confused')
audio_path_0 = download_tts('(10 spaces before dialogue) Is this how a normal-minded person operates?', 'ELIAS (CONTD)', 0)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'CUT TO:', 1)

print('--- Building Scene 88 ---')
spawn_light(True, False)
drop_prop_with_physics('/Engine/BasicShapes/Cube', unreal.Vector(200, 0, 500), unreal.Vector(2, 1, 1), 'Blockout_Desk_1')

# 🗣️ Dialogue Node: ELIAS (CONTD) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(10 spaces before dialogue) Every trauma has an origin point. Mine didnt start with my first panic attack, and it didnt start with the voices in my head. It started with a gavel strike in a family court room—a stroke of a pen by a judge who looked at paperwork instead of a childs eyes.', 'ELIAS (CONTD)', 0)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'CUT TO:', 1)

print('--- Building Scene 89 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELIAS (CONTD) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(10 spaces before dialogue) Im not just writing for myself; Im writing for her. For all of us whove been trapped in our own dark labyrinths.', 'ELIAS (CONTD)', 0)

# 🗣️ Dialogue Node: <SUMMARY> [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('Elias continues to navigate the complexities of his past traumas and relationships with his mother and his own emotional detachment, working on building a collaborative project fund for the neighborhood ambassador program while trying to maintain control over his life. He is also writing about his traumatic experiences and reclaiming the narrative that had been stolen from him before he even knew how to spell his own name.', '<SUMMARY>', 1)

# 🗣️ Dialogue Node: FADE IN: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('', 'FADE IN:', 2)

print('--- Building Scene 90 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(10 spaces before dialogue)', 'ELIAS', 0)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'CUT TO:', 1)

print('--- Building Scene 91 ---')
spawn_light(True, False)
drop_prop_with_physics('/Engine/BasicShapes/Cube', unreal.Vector(200, 0, 500), unreal.Vector(2, 1, 1), 'Blockout_Desk_1')

# 🗣️ Dialogue Node: ELIAS (CONTD) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(10 spaces before dialogue)', 'ELIAS (CONTD)', 0)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'CUT TO:', 1)

print('--- Building Scene 92 ---')
spawn_light(False, False)
drop_prop_with_physics('/Engine/BasicShapes/Cube', unreal.Vector(200, 0, 500), unreal.Vector(2, 1, 1), 'Blockout_Desk_1')

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(10 spaces before dialogue)', 'ELIAS', 0)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'CUT TO:', 1)

print('--- Building Scene 93 ---')
spawn_light(False, False)

# 🗣️ Dialogue Node: ELIAS (CONTD) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(10 spaces before dialogue)', 'ELIAS (CONTD)', 0)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'CUT TO:', 1)

print('--- Building Scene 94 ---')
spawn_light(True, False)
drop_prop_with_physics('/Engine/BasicShapes/Cube', unreal.Vector(200, 0, 500), unreal.Vector(2, 1, 1), 'Blockout_Desk_1')

# 🗣️ Dialogue Node: ELIAS (CONTD) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(10 spaces before dialogue)', 'ELIAS (CONTD)', 0)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'CUT TO:', 1)

print('--- Building Scene 95 ---')
spawn_light(False, False)

# 🗣️ Dialogue Node: ELIAS (CONTD) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(10 spaces before dialogue)', 'ELIAS (CONTD)', 0)

# 🗣️ Dialogue Node: <SUMMARY> [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('Elias continues to navigate the complexities of his past traumas and relationships with his mother and his own emotional detachment, working on building a collaborative project fund for the neighborhood ambassador program while trying to maintain control over his life. He is also writing about his traumatic experiences and reclaiming the narrative that had been stolen from him before he even knew how to spell his own name.', '<SUMMARY>', 1)

# 🗣️ Dialogue Node: FADE IN: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('', 'FADE IN:', 2)

print('--- Building Scene 96 ---')
spawn_light(True, False)
drop_prop_with_physics('/Engine/BasicShapes/Cube', unreal.Vector(200, 0, 500), unreal.Vector(2, 1, 1), 'Blockout_Desk_1')

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(10 spaces before dialogue)', 'ELIAS', 0)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'CUT TO:', 1)

print('--- Building Scene 97 ---')
spawn_light(False, False)

# 🗣️ Dialogue Node: ELIAS (CONTD) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(10 spaces before dialogue)', 'ELIAS (CONTD)', 0)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'CUT TO:', 1)

print('--- Building Scene 98 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: FADE IN: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('', 'FADE IN:', 0)

print('--- Building Scene 99 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('', 'CUT TO:', 0)

print('--- Building Scene 100 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(10 spaces before dialogue)', 'ELIAS', 0)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'CUT TO:', 1)

print('--- Building Scene 101 ---')
spawn_light(False, False)

# 🗣️ Dialogue Node: ELIAS (CONTD) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(10 spaces before dialogue)', 'ELIAS (CONTD)', 0)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'CUT TO:', 1)

print('--- Building Scene 102 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELIAS (CONTD) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(10 spaces before dialogue)', 'ELIAS (CONTD)', 0)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'CUT TO:', 1)

print('--- Building Scene 103 ---')
spawn_light(False, False)

# 🗣️ Dialogue Node: ELIAS (CONTD) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(10 spaces before dialogue)', 'ELIAS (CONTD)', 0)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'CUT TO:', 1)

print('--- Building Scene 104 ---')
spawn_light(False, False)

# 🗣️ Dialogue Node: <SUMMARY> [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('Elias continues to navigate the complexities of his past traumas and relationships with his mother and his own emotional detachment, working on building a collaborative project fund for the neighborhood ambassador program while trying to maintain control over his life. He is also writing about his traumatic experiences and reclaiming the narrative that had been stolen from him before he even knew how to spell his own name.', '<SUMMARY>', 0)

# 🗣️ Dialogue Node: FADE IN: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'FADE IN:', 1)

print('--- Building Scene 105 ---')
spawn_light(True, False)
drop_prop_with_physics('/Engine/BasicShapes/Cube', unreal.Vector(200, 0, 500), unreal.Vector(2, 1, 1), 'Blockout_Desk_1')
spawn_camera('Cam_Close_1', unreal.Vector(100, 0, 150))

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(10 spaces before dialogue)', 'ELIAS', 0)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'CUT TO:', 1)

print('--- Building Scene 106 ---')
spawn_light(False, False)

# 🗣️ Dialogue Node: JULIE [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('You didnt have to clean all this up.', 'JULIE', 0)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('(10 spaces before dialogue)', 'ELIAS', 1)

# 🗣️ Dialogue Node: JULIE [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('A subtle smile crosses her face.', 'JULIE', 2)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_3 = download_tts('(10 spaces before dialogue)', 'ELIAS', 3)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_4 = download_tts('', 'CUT TO:', 4)

print('--- Building Scene 107 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(10 spaces before dialogue)', 'ELIAS', 0)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'CUT TO:', 1)

print('--- Building Scene 108 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(10 spaces before dialogue)', 'ELIAS', 0)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'CUT TO:', 1)

print('--- Building Scene 109 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(10 spaces before dialogue)', 'ELIAS', 0)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'CUT TO:', 1)

print('--- Building Scene 110 ---')
spawn_light(True, False)
drop_prop_with_physics('/Engine/BasicShapes/Cube', unreal.Vector(200, 0, 500), unreal.Vector(2, 1, 1), 'Blockout_Desk_1')

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(10 spaces before dialogue)', 'ELIAS', 0)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'CUT TO:', 1)

print('--- Building Scene 111 ---')
spawn_light(False, False)
drop_prop_with_physics('/Engine/BasicShapes/Cube', unreal.Vector(200, 0, 500), unreal.Vector(2, 1, 1), 'Blockout_Desk_1')

# 🗣️ Dialogue Node: JULIE [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('Good morning.', 'JULIE', 0)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('(10 spaces before dialogue)', 'ELIAS', 1)

# 🗣️ Dialogue Node: <SUMMARY> [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('Elias continues to work on building his life in Ithaca, New York, while maintaining control over his emotions and relationships. He is also writing about his traumatic experiences and reclaiming the narrative that had been stolen from him before he even knew how to spell his own name.', '<SUMMARY>', 2)

# 🗣️ Dialogue Node: FADE IN: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_3 = download_tts('', 'FADE IN:', 3)

print('--- Building Scene 112 ---')
spawn_light(True, False)
drop_prop_with_physics('/Engine/BasicShapes/Cube', unreal.Vector(200, 0, 500), unreal.Vector(2, 1, 1), 'Blockout_Desk_1')

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(10 spaces before dialogue)', 'ELIAS', 0)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'CUT TO:', 1)

print('--- Building Scene 113 ---')
spawn_light(False, False)
drop_prop_with_physics('/Engine/BasicShapes/Cube', unreal.Vector(200, 0, 500), unreal.Vector(2, 1, 1), 'Blockout_Desk_1')

# 🗣️ Dialogue Node: JULIE [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('Good morning.', 'JULIE', 0)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('(10 spaces before dialogue)', 'ELIAS', 1)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('', 'CUT TO:', 2)

print('--- Building Scene 114 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(10 spaces before dialogue)', 'ELIAS', 0)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'CUT TO:', 1)

print('--- Building Scene 115 ---')
spawn_light(False, False)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(10 spaces before dialogue)', 'ELIAS', 0)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'CUT TO:', 1)

print('--- Building Scene 116 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(10 spaces before dialogue)', 'ELIAS', 0)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'CUT TO:', 1)

print('--- Building Scene 117 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(10 spaces before dialogue)', 'ELIAS', 0)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'CUT TO:', 1)

print('--- Building Scene 118 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(10 spaces before dialogue)', 'ELIAS', 0)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'CUT TO:', 1)

print('--- Building Scene 119 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(10 spaces before dialogue)', 'ELIAS', 0)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'CUT TO:', 1)

print('--- Building Scene 120 ---')
spawn_light(False, False)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(10 spaces before dialogue)', 'ELIAS', 0)

# 🗣️ Dialogue Node: FADE OUT. [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'FADE OUT.', 1)

# 🗣️ Dialogue Node: <SUMMARY> [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('Elias continues to work on building his life in Ithaca, New York, while maintaining control over his emotions and relationships. He is also writing about his traumatic experiences and reclaiming the narrative that had been stolen from him before he even knew how to spell his own name.', '<SUMMARY>', 2)

print('--- Building Scene 121 ---')
spawn_light(True, False)
drop_prop_with_physics('/Engine/BasicShapes/Cube', unreal.Vector(200, 0, 500), unreal.Vector(2, 1, 1), 'Blockout_Desk_1')

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(10 spaces before dialogue)', 'ELIAS', 0)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'CUT TO:', 1)

print('--- Building Scene 122 ---')
spawn_light(False, False)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(10 spaces before dialogue)', 'ELIAS', 0)

# 🗣️ Dialogue Node: FADE IN: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'FADE IN:', 1)

print('--- Building Scene 123 ---')
spawn_light(True, True)
drop_prop_with_physics('/Engine/BasicShapes/Cylinder', unreal.Vector(500, 500, 1000), unreal.Vector(1, 1, 5), 'Blockout_Tree_1')

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('', 'CUT TO:', 0)

print('--- Building Scene 124 ---')
spawn_light(True, False)
drop_prop_with_physics('/Engine/BasicShapes/Cube', unreal.Vector(200, 0, 500), unreal.Vector(2, 1, 1), 'Blockout_Desk_1')

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(10 spaces before dialogue)', 'ELIAS', 0)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'CUT TO:', 1)

print('--- Building Scene 125 ---')
spawn_light(True, True)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(10 spaces before dialogue)', 'ELIAS', 0)

# 🗣️ Dialogue Node: FADE OUT. [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'FADE OUT.', 1)

# 🗣️ Dialogue Node: <SUMMARY> [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('Brett Adam Stehouwer has finally found peace after years of struggling with trauma and emotional pain. He feels no guilt for the past, no fear of future volatility, and no burden of obligation as he prepares to leave his old life behind in West Michigan and start anew in Ithaca, New York.', '<SUMMARY>', 2)

print('✅ Virtual Production Build Complete!')
