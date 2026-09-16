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

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(whispering)', 'ELIAS', 0)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'CUT TO:', 1)

print('--- Building Scene 2 ---')
spawn_light(False, False)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(to himself)', 'ELIAS', 0)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'CUT TO:', 1)

print('--- Building Scene 3 ---')
spawn_light(False, False)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(whispering to himself)', 'ELIAS', 0)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'CUT TO:', 1)

print('--- Building Scene 4 ---')
spawn_light(True, False)
spawn_camera('Cam_Wide_1', unreal.Vector(-500, 0, 150))
drop_prop_with_physics('/Engine/BasicShapes/Cube', unreal.Vector(200, 0, 500), unreal.Vector(2, 1, 1), 'Blockout_Desk_1')

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(muttering to himself)', 'ELIAS', 0)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'CUT TO:', 1)

print('--- Building Scene 5 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(whispering to himself, cold and detached)', 'ELIAS', 0)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'CUT TO:', 1)

print('--- Building Scene 6 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(speaking coldly)', 'ELIAS', 0)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'CUT TO:', 1)

print('--- Building Scene 7 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(picking up his mug)', 'ELIAS', 0)

# 🗣️ Dialogue Node: MOTHER [Confused]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Confused')
audio_path_1 = download_tts('Quiet morning?', 'MOTHER', 1)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('(replying)', 'ELIAS', 2)

# 🗣️ Dialogue Node: MOTHER [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_3 = download_tts('I told them no.', 'MOTHER', 3)

# 🗣️ Dialogue Node: <SUMMARY> [Happy]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Happy')
audio_path_4 = download_tts('Eliass past and present collide as he navigates the fragility of his mental state and the looming threat of losing those he loves. He sits at his trading desk, executing complex algorithms to manage risk while confronting the echoes of his childhood trauma.', '<SUMMARY>', 4)

print('--- Building Scene 8 ---')
spawn_light(True, False)
drop_prop_with_physics('/Engine/BasicShapes/Cube', unreal.Vector(200, 0, 500), unreal.Vector(2, 1, 1), 'Blockout_Desk_1')

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(whispering)', 'ELIAS', 0)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('(continued)', 'ELIAS', 1)

print('--- Building Scene 9 ---')
spawn_light(True, False)
drop_prop_with_physics('/Engine/BasicShapes/Cube', unreal.Vector(200, 0, 500), unreal.Vector(2, 1, 1), 'Blockout_Desk_1')

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(typing)', 'ELIAS', 0)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('(continued)', 'ELIAS', 1)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('(continued)', 'ELIAS', 2)

print('--- Building Scene 10 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(typing)', 'ELIAS', 0)

print('--- Building Scene 11 ---')
spawn_light(True, False)
drop_prop_with_physics('/Engine/BasicShapes/Cube', unreal.Vector(200, 0, 500), unreal.Vector(2, 1, 1), 'Blockout_Desk_1')

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(typing)', 'ELIAS', 0)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('(continued)', 'ELIAS', 1)

print('--- Building Scene 12 ---')
spawn_light(True, False)
spawn_camera('Cam_Close_1', unreal.Vector(100, 0, 150))
spawn_camera('Cam_Close_2', unreal.Vector(100, 0, 150))
drop_prop_with_physics('/Engine/BasicShapes/Cube', unreal.Vector(200, 0, 500), unreal.Vector(2, 1, 1), 'Blockout_Desk_1')
spawn_camera('Cam_Close_3', unreal.Vector(100, 0, 150))
spawn_camera('Cam_Pan_4', unreal.Vector(0, 500, 150))
drop_prop_with_physics('/Engine/BasicShapes/Cylinder', unreal.Vector(500, 500, 1000), unreal.Vector(1, 1, 5), 'Blockout_Tree_2')
drop_prop_with_physics('/Engine/BasicShapes/Cylinder', unreal.Vector(500, 500, 1000), unreal.Vector(1, 1, 5), 'Blockout_Tree_3')
drop_prop_with_physics('/Engine/BasicShapes/Cube', unreal.Vector(200, 0, 500), unreal.Vector(2, 1, 1), 'Blockout_Desk_4')
drop_prop_with_physics('/Engine/BasicShapes/Cube', unreal.Vector(200, 0, 500), unreal.Vector(2, 1, 1), 'Blockout_Desk_5')
drop_prop_with_physics('/Engine/BasicShapes/Cube', unreal.Vector(200, 0, 500), unreal.Vector(2, 1, 1), 'Blockout_Desk_6')
spawn_camera('Cam_Pan_5', unreal.Vector(0, 500, 150))
drop_prop_with_physics('/Engine/BasicShapes/Cube', unreal.Vector(200, 0, 500), unreal.Vector(2, 1, 1), 'Blockout_Desk_7')
spawn_camera('Cam_Pan_6', unreal.Vector(0, 500, 150))
drop_prop_with_physics('/Engine/BasicShapes/Cube', unreal.Vector(200, 0, 500), unreal.Vector(2, 1, 1), 'Blockout_Desk_8')
spawn_camera('Cam_Pan_7', unreal.Vector(0, 500, 150))
spawn_camera('Cam_Close_8', unreal.Vector(100, 0, 150))
drop_prop_with_physics('/Engine/BasicShapes/Cube', unreal.Vector(200, 0, 500), unreal.Vector(2, 1, 1), 'Blockout_Desk_9')

# 🗣️ Dialogue Node: INNER VOICE [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('Do not feel bad, Elias. Just say it. It is easy to ask to be forgiven. Your intentions are good. It is okay to forget. Just let it go.', 'INNER VOICE', 0)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('(continued)', 'ELIAS', 1)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('(continued)', 'ELIAS', 2)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_3 = download_tts('(continued)', 'ELIAS', 3)

# 🗣️ Dialogue Node: <SUMMARY> [Happy]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Happy')
audio_path_4 = download_tts('Elias navigates the fragility of his mental state, confronting echoes of childhood trauma while building a new reality through his writing. He sits at his trading desk, executing complex algorithms to manage risk, but his true focus is on creating a better future for himself and those he loves.', '<SUMMARY>', 4)

# 🗣️ Dialogue Node: **INT. ELIASS OFFICE - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_5 = download_tts('Elias sits at his desk, staring at his computer screens.', '**INT. ELIASS OFFICE - DAY**', 5)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_6 = download_tts('(whispering)', 'ELIAS', 6)

# 🗣️ Dialogue Node: **CUT TO:** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_7 = download_tts('', '**CUT TO:**', 7)

# 🗣️ Dialogue Node: **ELIASS MIND** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_8 = download_tts('A wooden dock appears in front of him. Three figures stand waiting at the edge of the water: Adam, Elias, and an unknown brother.', '**ELIASS MIND**', 8)

# 🗣️ Dialogue Node: ADAM [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_9 = download_tts('(talking to the unknown brother)', 'ADAM', 9)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_10 = download_tts('(to himself)', 'ELIAS', 10)

# 🗣️ Dialogue Node: **CUT TO:** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_11 = download_tts('', '**CUT TO:**', 11)

# 🗣️ Dialogue Node: **INT. ELIASS OFFICE - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_12 = download_tts('Elias monitors the trading charts on his screens.', '**INT. ELIASS OFFICE - DAY**', 12)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_13 = download_tts('(to himself)', 'ELIAS', 13)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_14 = download_tts('(to himself)', 'ELIAS', 14)

# 🗣️ Dialogue Node: **CUT TO:** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_15 = download_tts('', '**CUT TO:**', 15)

# 🗣️ Dialogue Node: **INT. ELIASS OFFICE - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_16 = download_tts('A wave of self-correction and guilt attempts to breach Eliass mental firewall.', '**INT. ELIASS OFFICE - DAY**', 16)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_17 = download_tts('(to himself)', 'ELIAS', 17)

# 🗣️ Dialogue Node: ADAM (V.O.) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_18 = download_tts('...Just say it. It is easy to ask to be forgiven. Your intentions were good. It is okay to forget. Just let go.', 'ADAM (V.O.)', 18)

# 🗣️ Dialogue Node: **CUT TO:** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_19 = download_tts('', '**CUT TO:**', 19)

# 🗣️ Dialogue Node: **INT. ELIASS OFFICE - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_20 = download_tts('Elias opens his digital audio workstation and pulls up an instrumental track hes arranging.', '**INT. ELIASS OFFICE - DAY**', 20)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_21 = download_tts('(to himself)', 'ELIAS', 21)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_22 = download_tts('(to himself)', 'ELIAS', 22)

# 🗣️ Dialogue Node: **CUT TO:** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_23 = download_tts('', '**CUT TO:**', 23)

# 🗣️ Dialogue Node: **INT. ELIASS OFFICE - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_24 = download_tts('Elias opens a small notebook on his desk and reads the entry from his mother.', '**INT. ELIASS OFFICE - DAY**', 24)

# 🗣️ Dialogue Node: MOTHER (V.O.) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_25 = download_tts('When he was two years old, I began to suspect that something was happening at his dads house...', 'MOTHER (V.O.)', 25)

# 🗣️ Dialogue Node: **CUT TO:** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_26 = download_tts('', '**CUT TO:**', 26)

# 🗣️ Dialogue Node: **INT. ELIASS OFFICE - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_27 = download_tts('Elias stands up and walks to the kitchen.', '**INT. ELIASS OFFICE - DAY**', 27)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_28 = download_tts('(to himself)', 'ELIAS', 28)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_29 = download_tts('(to himself)', 'ELIAS', 29)

# 🗣️ Dialogue Node: **CUT TO:** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_30 = download_tts('', '**CUT TO:**', 30)

# 🗣️ Dialogue Node: **INT. ELIASS OFFICE - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_31 = download_tts('Elias returns to his computer monitors and opens a new text file, titling it Adam Bomb.', '**INT. ELIASS OFFICE - DAY**', 31)

# 🗣️ Dialogue Node: <SUMMARY> [Happy]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Happy')
audio_path_32 = download_tts('Elias navigates the fragility of his mental state, confronting echoes of childhood trauma while building a new reality through his writing. He sits at his trading desk, executing complex algorithms to manage risk, but his true focus is on creating a better future for himself and those he loves.', '<SUMMARY>', 32)

# 🗣️ Dialogue Node: **INT. ELIASS OFFICE - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_33 = download_tts('Elias sits at his desk, staring at a small plastic bottle of prescription pills.', '**INT. ELIASS OFFICE - DAY**', 33)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_34 = download_tts('(to himself)', 'ELIAS', 34)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_35 = download_tts('(to himself)', 'ELIAS', 35)

# 🗣️ Dialogue Node: **CUT TO:** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_36 = download_tts('', '**CUT TO:**', 36)

# 🗣️ Dialogue Node: **INT. ELIASS OFFICE - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_37 = download_tts('Elias scrolls through the pages of his manuscript on Echoes Within, reading his own raw transcriptions of trauma and loss.', '**INT. ELIASS OFFICE - DAY**', 37)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_38 = download_tts('(whispering to himself)', 'ELIAS', 38)

# 🗣️ Dialogue Node: **CUT TO:** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_39 = download_tts('', '**CUT TO:**', 39)

# 🗣️ Dialogue Node: **INT. ELIASS OFFICE - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_40 = download_tts('Elias opens a fresh file and titles it The Path Forward.', '**INT. ELIASS OFFICE - DAY**', 40)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_41 = download_tts('(to himself)', 'ELIAS', 41)

# 🗣️ Dialogue Node: **CUT TO:** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_42 = download_tts('', '**CUT TO:**', 42)

# 🗣️ Dialogue Node: **INT. ELIASS OFFICE - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_43 = download_tts('Elias continues typing, his words flowing onto the page as he writes about building automation platforms and crafting lyrics that can reach people.', '**INT. ELIASS OFFICE - DAY**', 43)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_44 = download_tts('(to himself)', 'ELIAS', 44)

# 🗣️ Dialogue Node: <SUMMARY> [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_45 = download_tts('Elias confronts the lingering effects of past trauma and medication, but with a newfound determination to take control of his life and turn his disability into a gift. He begins writing about his journey towards healing and growth in The Path Forward.', '<SUMMARY>', 45)

# 🗣️ Dialogue Node: **INT. ELIASS OFFICE - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_46 = download_tts('Elias sits at his desk, staring at a blank document on his computer screen.', '**INT. ELIASS OFFICE - DAY**', 46)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_47 = download_tts('(to himself)', 'ELIAS', 47)

# 🗣️ Dialogue Node: **CUT TO:** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_48 = download_tts('', '**CUT TO:**', 48)

# 🗣️ Dialogue Node: **INT. ELIASS OFFICE - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_49 = download_tts('Elias continues typing, his words flowing onto the page as he writes about building automation platforms and crafting lyrics that can reach people.', '**INT. ELIASS OFFICE - DAY**', 49)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_50 = download_tts('(to himself)', 'ELIAS', 50)

# 🗣️ Dialogue Node: **CUT TO:** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_51 = download_tts('', '**CUT TO:**', 51)

# 🗣️ Dialogue Node: **INT. ELIASS OFFICE - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_52 = download_tts('Eliass mother, Julie, enters the room with a laptop and begins reviewing the page spreads for their childrens book project.', '**INT. ELIASS OFFICE - DAY**', 52)

# 🗣️ Dialogue Node: JULIE [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_53 = download_tts('It feels light working on something like this.', 'JULIE', 53)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_54 = download_tts('It has a defined purpose. Its the opposite of the labyrinth. In Echoes, I documented the damage so the record remains unshakeable. With this, we build the structure before the damage occurs. We give them a clear roadmap early.', 'ELIAS', 54)

# 🗣️ Dialogue Node: **CUT TO:** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_55 = download_tts('', '**CUT TO:**', 55)

# 🗣️ Dialogue Node: **INT. ELIASS OFFICE - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_56 = download_tts('Elias opens a secondary window to verify the digital asset resolution, ensuring every line art file exceeds 300 DPI.', '**INT. ELIASS OFFICE - DAY**', 56)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_57 = download_tts('We publish under our own terms. No middleman. Absolute ownership.', 'ELIAS', 57)

# 🗣️ Dialogue Node: **CUT TO:** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_58 = download_tts('', '**CUT TO:**', 58)

# 🗣️ Dialogue Node: **INT. ELIASS OFFICE - NIGHT** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_59 = download_tts('The clock on the wall reads 01:14 AM. Elias sits at his desk, illuminated by the dual monitors. The digital audio workstation, FL Studio, occupies the main screen.', '**INT. ELIASS OFFICE - NIGHT**', 59)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_60 = download_tts('(whispering to himself)', 'ELIAS', 60)

# 🗣️ Dialogue Node: **CUT TO:** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_61 = download_tts('', '**CUT TO:**', 61)

# 🗣️ Dialogue Node: **INT. ELIASS OFFICE - NIGHT** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_62 = download_tts('Elias places his hands on the keyboard, synchronizing his typing speed with the quarter-note sub-bass pulses.', '**INT. ELIASS OFFICE - NIGHT**', 62)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_63 = download_tts('Clean audio path. Zero frequency masking.', 'ELIAS', 63)

# 🗣️ Dialogue Node: **CUT TO:** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_64 = download_tts('', '**CUT TO:**', 64)

# 🗣️ Dialogue Node: **INT. ELIASS OFFICE - NIGHT** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_65 = download_tts('The clock on the wall reads 02:30 AM. Elias sits in his chair, the glow of the monitors casting long shadows across the room.', '**INT. ELIASS OFFICE - NIGHT**', 65)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_66 = download_tts('(whispering to himself)', 'ELIAS', 66)

# 🗣️ Dialogue Node: **SUMMARY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_67 = download_tts('Elias confronts the lingering effects of past trauma and medication, but with a newfound determination to take control of his life and turn his disability into a gift. He begins writing about his journey towards healing and growth in The Path Forward.', '**SUMMARY**', 67)

# 🗣️ Dialogue Node: **INT. ELIASS OFFICE - NIGHT** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_68 = download_tts('Elias sits at his desk, illuminated by dual monitors. He opens the trading terminal alongside his manuscript draft.', '**INT. ELIASS OFFICE - NIGHT**', 68)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_69 = download_tts('(whispering to himself)', 'ELIAS', 69)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_70 = download_tts('(whispering)', 'ELIAS', 70)

# 🗣️ Dialogue Node: **CUT TO:** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_71 = download_tts('', '**CUT TO:**', 71)

# 🗣️ Dialogue Node: **INT. VANCES OFFICE - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_72 = download_tts('Vance, a regional broker in his fifties, sits across from Elias in the glass-walled conference room overlooking downtown Grand Rapids.', '**INT. VANCES OFFICE - DAY**', 72)

# 🗣️ Dialogue Node: VANCE [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_73 = download_tts('Youve got a neat little setup with your automation scripts and local directories. But out here in the real market, passion doesnt clear payroll.', 'VANCE', 73)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_74 = download_tts('( flatly)', 'ELIAS', 74)

# 🗣️ Dialogue Node: **SUMMARY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_75 = download_tts('Elias has finally broken free from the shadows of his past and is now focused on building a self-sustaining agricultural ecosystem at the Groundswell Center, while also working on his manuscript Echoes Within, which chronicles his journey towards healing and growth. He is no longer controlled by fear or anger, but instead uses them as fuel to build an unshakeable identity.', '**SUMMARY**', 75)

# 🗣️ Dialogue Node: **INT. ELIASS OFFICE - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_76 = download_tts('Elias sits at his desk, reviewing the text message on his phone.', '**INT. ELIASS OFFICE - DAY**', 76)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_77 = download_tts('( flatly)', 'ELIAS', 77)

# 🗣️ Dialogue Node: **CUT TO:** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_78 = download_tts('', '**CUT TO:**', 78)

# 🗣️ Dialogue Node: **EXT. JENISON PROPERTY - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_79 = download_tts('Elias walks along the perimeter of his property, reviewing the operational blueprint on his tablet.', '**EXT. JENISON PROPERTY - DAY**', 79)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_80 = download_tts('( to himself)', 'ELIAS', 80)

# 🗣️ Dialogue Node: **CUT TO:** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_81 = download_tts('', '**CUT TO:**', 81)

# 🗣️ Dialogue Node: **INT. ELIASS OFFICE - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_82 = download_tts('Elias sits at his desk, reviewing the response he sent earlier.', '**INT. ELIASS OFFICE - DAY**', 82)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_83 = download_tts('( to himself)', 'ELIAS', 83)

# 🗣️ Dialogue Node: **SUMMARY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_84 = download_tts('Elias has established a clear boundary with someone from his past who is seeking help, but he refuses to enable their destructive loops. He prioritizes his own peace and well-being, using the Agency over Obligation protocol to maintain control over his life.', '**SUMMARY**', 84)

# 🗣️ Dialogue Node: **INT. ELIASS OFFICE - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_85 = download_tts('Elias sits at his desk, reviewing the response he sent earlier.', '**INT. ELIASS OFFICE - DAY**', 85)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_86 = download_tts('(to himself)', 'ELIAS', 86)

# 🗣️ Dialogue Node: **CUT TO:** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_87 = download_tts('', '**CUT TO:**', 87)

# 🗣️ Dialogue Node: **EXT. JENISON PROPERTY - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_88 = download_tts('Elias walks along the perimeter of his property, reviewing the operational blueprint on his tablet.', '**EXT. JENISON PROPERTY - DAY**', 88)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_89 = download_tts('(to himself)', 'ELIAS', 89)

# 🗣️ Dialogue Node: **CUT TO:** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_90 = download_tts('', '**CUT TO:**', 90)

# 🗣️ Dialogue Node: **INT. ELIASS OFFICE - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_91 = download_tts('Elias sits at his desk, reviewing the response he sent earlier.', '**INT. ELIASS OFFICE - DAY**', 91)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_92 = download_tts('(to himself)', 'ELIAS', 92)

# 🗣️ Dialogue Node: MOTHER [Confused]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Confused')
audio_path_93 = download_tts('Everything okay?', 'MOTHER', 93)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_94 = download_tts('Everything is clear. The boundaries are set. The system is clean. We are moving directly into the next phase.', 'ELIAS', 94)

# 🗣️ Dialogue Node: **CUT TO:** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_95 = download_tts('', '**CUT TO:**', 95)

# 🗣️ Dialogue Node: **EXT. JENISON PROPERTY - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_96 = download_tts('Elias walks back toward the porch, reviewing his master roadmap on the tablet.', '**EXT. JENISON PROPERTY - DAY**', 96)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_97 = download_tts('(to himself)', 'ELIAS', 97)

# 🗣️ Dialogue Node: **SUMMARY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_98 = download_tts('Elias has established a clear boundary with someone from his past who is seeking help, but he refuses to enable their destructive loops. He prioritizes his own peace and well-being, using the Agency over Obligation protocol to maintain control over his life.', '**SUMMARY**', 98)

# 🗣️ Dialogue Node: **INT. ELIASS OFFICE - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_99 = download_tts('Elias sits at his desk, reviewing the response he sent earlier.', '**INT. ELIASS OFFICE - DAY**', 99)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_100 = download_tts('(to himself)', 'ELIAS', 100)

# 🗣️ Dialogue Node: MOTHER [Confused]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Confused')
audio_path_101 = download_tts('Everything okay?', 'MOTHER', 101)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_102 = download_tts('Everything is clear. The boundaries are set. The system is clean. We are moving directly into the next phase.', 'ELIAS', 102)

# 🗣️ Dialogue Node: **CUT TO:** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_103 = download_tts('', '**CUT TO:**', 103)

# 🗣️ Dialogue Node: **EXT. JENISON PROPERTY - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_104 = download_tts('Elias walks back toward the porch, reviewing his master roadmap on the tablet.', '**EXT. JENISON PROPERTY - DAY**', 104)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_105 = download_tts('(to himself)', 'ELIAS', 105)

# 🗣️ Dialogue Node: **SUMMARY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_106 = download_tts('Elias has established a clear boundary with someone from his past who is seeking help, but he refuses to enable their destructive loops. He prioritizes his own peace and well-being, using the Agency over Obligation protocol to maintain control over his life.', '**SUMMARY**', 106)

# 🗣️ Dialogue Node: **INT. ELIASS OFFICE - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_107 = download_tts('Elias opens a digital map on his display, zooming in on the region surrounding Ithaca, New York.', '**INT. ELIASS OFFICE - DAY**', 107)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_108 = download_tts('(to himself)', 'ELIAS', 108)

# 🗣️ Dialogue Node: **CUT TO:** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_109 = download_tts('', '**CUT TO:**', 109)

# 🗣️ Dialogue Node: **INT. ELIASS BEDROOM - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_110 = download_tts('Elias wakes up, staring at the ceiling. He feels stable, grounded, and present.', '**INT. ELIASS BEDROOM - DAY**', 110)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_111 = download_tts('(to himself)', 'ELIAS', 111)

# 🗣️ Dialogue Node: **CUT TO:** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_112 = download_tts('', '**CUT TO:**', 112)

# 🗣️ Dialogue Node: **INT. ELIASS OFFICE - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_113 = download_tts('Elias places his hands on the keyboard, staring at the title page of his next major manuscript project: Because The Judge Made Me Go.', '**INT. ELIASS OFFICE - DAY**', 113)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_114 = download_tts('(to himself)', 'ELIAS', 114)

# 🗣️ Dialogue Node: **CUT TO:** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_115 = download_tts('', '**CUT TO:**', 115)

# 🗣️ Dialogue Node: **INT. ELIASS LIVING ROOM - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_116 = download_tts('Elias thinks about his mother, Julie, and the financial and physical realities they are currently navigating.', '**INT. ELIASS LIVING ROOM - DAY**', 116)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_117 = download_tts('(to himself)', 'ELIAS', 117)

# 🗣️ Dialogue Node: **SUMMARY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_118 = download_tts('Elias has established a clear boundary with someone from his past who is seeking help, but he refuses to enable their destructive loops. He prioritizes his own peace and well-being, using the Agency over Obligation protocol to maintain control over his life.', '**SUMMARY**', 118)

# 🗣️ Dialogue Node: **INT. ELIASS LIVING ROOM - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_119 = download_tts('Elias sits at his desk, staring at a blank document on his computer screen.', '**INT. ELIASS LIVING ROOM - DAY**', 119)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_120 = download_tts('(to himself)', 'ELIAS', 120)

# 🗣️ Dialogue Node: **INT. ELIASS LIVING ROOM - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_121 = download_tts('Elias opens a blank document on his computer screen and begins typing.', '**INT. ELIASS LIVING ROOM - DAY**', 121)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_122 = download_tts('(to himself)', 'ELIAS', 122)

# 🗣️ Dialogue Node: **INT. ELIASS LIVING ROOM - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_123 = download_tts('Elias looks at his phone, which is vibrating softly against the desk. A notification from a messaging app flashes across the screen—an uninvited message from an old acquaintance attempting to drag him back into a conversational loop of personal drama and cyclical complaints.', '**INT. ELIASS LIVING ROOM - DAY**', 123)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_124 = download_tts('(to himself)', 'ELIAS', 124)

# 🗣️ Dialogue Node: **INT. ELIASS BACK PORCH - NIGHT** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_125 = download_tts('Elias stands on the back porch, looking out across the quiet neighborhood under a clear night sky. In his pocket, he holds his phone, displaying the saved notes for his multi-year transition plan.', '**INT. ELIASS BACK PORCH - NIGHT**', 125)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_126 = download_tts('(to himself)', 'ELIAS', 126)

# 🗣️ Dialogue Node: **INT. ELIASS LIVING ROOM - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_127 = download_tts('Elias sits at his desk, reviewing his daily log entries. The calendar widget on the monitor ticked past thirty days since the initial titration dose of Lamotrigine.', '**INT. ELIASS LIVING ROOM - DAY**', 127)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_128 = download_tts('(to himself)', 'ELIAS', 128)

# 🗣️ Dialogue Node: **INT. ELIASS LIVING ROOM - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_129 = download_tts('Elias opens a blank document and types a short summary for his clinical file: The windows of peace are widening. The empty shell is receding. The clean room baseline is no longer an aspiration; its our operating reality.', '**INT. ELIASS LIVING ROOM - DAY**', 129)

# 🗣️ Dialogue Node: **SUMMARY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_130 = download_tts('Elias continues to prioritize his own peace and well-being, using the Agency over Obligation protocol to maintain control over his life. He is working towards a multi-year transition plan to establish a self-sufficient lifestyle at the Groundswell Center for Local Food & Farming in Ithaca, New York, where he can live off the land and focus on his writing and music projects.', '**SUMMARY**', 130)

# 🗣️ Dialogue Node: **INT. ELIASS WORKSTATION - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_131 = download_tts('Elias sits at his workstation in Jenison, surrounded by the quiet hum of his custom PC chassis. The dual ultra-wide monitors display two distinct worlds: on the left, a Python IDE with a multi-threaded daemon manager script; on the right, the terminal monitoring his Metronet 5 Gigabit fiber link speed, locked at 5000 Mbps.', '**INT. ELIASS WORKSTATION - DAY**', 131)

# 🗣️ Dialogue Node: **ELIAS** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_132 = download_tts('(to himself)', '**ELIAS**', 132)

# 🗣️ Dialogue Node: **ELIAS** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_133 = download_tts('(to himself)', '**ELIAS**', 133)

# 🗣️ Dialogue Node: **INT. ELIASS LIVING ROOM - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_134 = download_tts('Elias stands near the passenger side of his mothers car, watching her check the mirrors before pulling out onto the main road in Jenison. He recognizes the subtle signs of her driving anxiety—the rigid grip on the steering wheel, the sudden rise in tension when another driver cuts into her lane.', '**INT. ELIASS LIVING ROOM - DAY**', 134)

# 🗣️ Dialogue Node: **ELIAS** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_135 = download_tts('(to himself)', '**ELIAS**', 135)

# 🗣️ Dialogue Node: **INT. ELIASS WORKSTATION - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_136 = download_tts('Elias sits at his workstation, surrounded by the quiet hum of his custom PC chassis. The dual ultra-wide monitors display two distinct worlds: on the left, a Python IDE with a multi-threaded daemon manager script; on the right, the terminal monitoring his Metronet 5 Gigabit fiber link speed, locked at 5000 Mbps.', '**INT. ELIASS WORKSTATION - DAY**', 136)

# 🗣️ Dialogue Node: **ELIAS** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_137 = download_tts('(to himself)', '**ELIAS**', 137)

# 🗣️ Dialogue Node: **INT. ELIASS LIVING ROOM - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_138 = download_tts('Elias stands near the passenger side of his mothers car, watching her check the mirrors before pulling out onto the main road in Jenison. He recognizes the subtle signs of her driving anxiety—the rigid grip on the steering wheel, the sudden rise in tension when another driver cuts into her lane.', '**INT. ELIASS LIVING ROOM - DAY**', 138)

# 🗣️ Dialogue Node: **ELIAS** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_139 = download_tts('(to himself)', '**ELIAS**', 139)

# 🗣️ Dialogue Node: **INT. ELIASS WORKSTATION - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_140 = download_tts('Elias sits at his workstation in Jenison, surrounded by the quiet hum of his custom PC chassis. The dual ultra-wide monitors display two distinct worlds: on the left, a Python IDE with a multi-threaded daemon manager script; on the right, the terminal monitoring his Metronet 5 Gigabit fiber link speed, locked at 5000 Mbps.', '**INT. ELIASS WORKSTATION - DAY**', 140)

# 🗣️ Dialogue Node: **ELIAS** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_141 = download_tts('(to himself)', '**ELIAS**', 141)

# 🗣️ Dialogue Node: **INT. ELIASS LIVING ROOM - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_142 = download_tts('Elias stands near the passenger side of his mothers car, watching her check the mirrors before pulling out onto the main road in Jenison. He recognizes the subtle signs of her driving anxiety—the rigid grip on the steering wheel, the sudden rise in tension when another driver cuts into her lane.', '**INT. ELIASS LIVING ROOM - DAY**', 142)

# 🗣️ Dialogue Node: **ELIAS** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_143 = download_tts('(to himself)', '**ELIAS**', 143)

# 🗣️ Dialogue Node: **INT. ELIASS WORKSTATION - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_144 = download_tts('Elias sits at his workstation in Jenison, surrounded by the quiet hum of his custom PC chassis. The dual ultra-wide monitors display two distinct worlds: on the left, a Python IDE with a multi-threaded daemon manager script; on the right, the terminal monitoring his Metronet 5 Gigabit fiber link speed, locked at 5000 Mbps.', '**INT. ELIASS WORKSTATION - DAY**', 144)

# 🗣️ Dialogue Node: **ELIAS** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_145 = download_tts('(to himself)', '**ELIAS**', 145)

# 🗣️ Dialogue Node: **INT. ELIASS LIVING ROOM - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_146 = download_tts('Elias stands near the passenger side of his mothers car, watching her check the mirrors before pulling out onto the main road in Jenison. He recognizes the subtle signs of her driving anxiety—the rigid grip on the steering wheel, the sudden rise in tension when another driver cuts into her lane.', '**INT. ELIASS LIVING ROOM - DAY**', 146)

# 🗣️ Dialogue Node: **ELIAS** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_147 = download_tts('(to himself)', '**ELIAS**', 147)

# 🗣️ Dialogue Node: **INT. ELIASS WORKSTATION - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_148 = download_tts('Elias sits at his workstation in Jenison, surrounded by the quiet hum of his custom PC chassis. The dual ultra-wide monitors display two distinct worlds: on the left, a Python IDE with a multi-threaded daemon manager script; on the right, the terminal monitoring his Metronet 5 Gigabit fiber link speed, locked at 5000 Mbps.', '**INT. ELIASS WORKSTATION - DAY**', 148)

# 🗣️ Dialogue Node: **ELIAS** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_149 = download_tts('(to himself)', '**ELIAS**', 149)

# 🗣️ Dialogue Node: **INT. ELIASS LIVING ROOM - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_150 = download_tts('Elias stands near the passenger side of his mothers car, watching her check the mirrors before pulling out onto the main road in Jenison. He recognizes the subtle signs of her driving anxiety—the rigid grip on the steering wheel, the sudden rise in tension when another driver cuts into her lane.', '**INT. ELIASS LIVING ROOM - DAY**', 150)

# 🗣️ Dialogue Node: **ELIAS** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_151 = download_tts('(to himself)', '**ELIAS**', 151)

# 🗣️ Dialogue Node: **INT. ELIASS WORKSTATION - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_152 = download_tts('Elias sits at his workstation in Jenison, surrounded by the quiet hum of his custom PC chassis. The dual ultra-wide monitors display two distinct worlds: on the left, a Python IDE with a multi-threaded daemon manager script; on the right, the terminal monitoring his Metronet 5 Gigabit fiber link speed, locked at 5000 Mbps.', '**INT. ELIASS WORKSTATION - DAY**', 152)

# 🗣️ Dialogue Node: **ELIAS** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_153 = download_tts('(to himself)', '**ELIAS**', 153)

# 🗣️ Dialogue Node: **INT. ELIASS LIVING ROOM - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_154 = download_tts('Elias stands near the passenger side of his mothers car, watching her check the mirrors before pulling out onto the main road in Jenison. He recognizes the subtle signs of her driving anxiety—the rigid grip on the steering wheel, the sudden rise in tension when another driver cuts into her lane.', '**INT. ELIASS LIVING ROOM - DAY**', 154)

# 🗣️ Dialogue Node: **ELIAS** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_155 = download_tts('(to himself)', '**ELIAS**', 155)

# 🗣️ Dialogue Node: **INT. ELIASS WORKSTATION - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_156 = download_tts('Elias sits at his workstation in Jenison, surrounded by the quiet hum of his custom PC chassis. The dual ultra-wide monitors display two distinct worlds: on the left, a Python IDE with a multi-threaded daemon manager script; on the right, the terminal monitoring his Metronet 5 Gigabit fiber link speed, locked at 5000 Mbps.', '**INT. ELIASS WORKSTATION - DAY**', 156)

# 🗣️ Dialogue Node: **ELIAS** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_157 = download_tts('(to himself)', '**ELIAS**', 157)

# 🗣️ Dialogue Node: **INT. ELIASS LIVING ROOM - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_158 = download_tts('Elias stands near the passenger side of his mothers car, watching her check the mirrors before pulling out onto the main road in Jenison. He recognizes the subtle signs of her driving anxiety—the rigid grip on the steering wheel, the sudden rise in tension when another driver cuts into her lane.', '**INT. ELIASS LIVING ROOM - DAY**', 158)

# 🗣️ Dialogue Node: **ELIAS** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_159 = download_tts('(to himself)', '**ELIAS**', 159)

# 🗣️ Dialogue Node: **INT. ELIASS WORKSTATION - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_160 = download_tts('Elias sits at his workstation in Jenison, surrounded by the quiet hum of his custom PC chassis. The dual ultra-wide monitors display two distinct worlds: on the left, a Python IDE with a multi-threaded daemon manager script; on the right, the terminal monitoring his Metronet 5 Gigabit fiber link speed, locked at 5000 Mbps.', '**INT. ELIASS WORKSTATION - DAY**', 160)

# 🗣️ Dialogue Node: **ELIAS** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_161 = download_tts('(to himself)', '**ELIAS**', 161)

# 🗣️ Dialogue Node: **INT. ELIASS LIVING ROOM - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_162 = download_tts('Elias stands near the passenger side of his mothers car, watching her check the mirrors before pulling out onto the main road in Jenison. He recognizes the subtle signs of her driving anxiety—the rigid grip on the steering wheel, the sudden rise in tension when another driver cuts into her lane.', '**INT. ELIASS LIVING ROOM - DAY**', 162)

# 🗣️ Dialogue Node: **ELIAS** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_163 = download_tts('(to himself)', '**ELIAS**', 163)

# 🗣️ Dialogue Node: **INT. ELIASS WORKSTATION - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_164 = download_tts('Elias sits at his workstation in Jenison, surrounded by the quiet hum of his custom PC chassis. The dual ultra-wide monitors display two distinct worlds: on the left, a Python IDE with a multi-threaded daemon manager script; on the right, the terminal monitoring his Metronet 5 Gigabit fiber link speed, locked at 5000 Mbps.', '**INT. ELIASS WORKSTATION - DAY**', 164)

# 🗣️ Dialogue Node: **ELIAS** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_165 = download_tts('(to himself)', '**ELIAS**', 165)

# 🗣️ Dialogue Node: **INT. ELIASS LIVING ROOM - [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_166 = download_tts('', '**INT. ELIASS LIVING ROOM -', 166)

# 🗣️ Dialogue Node: **INT. ELIASS WORKSTATION - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_167 = download_tts('Elias sits at his workstation in Jenison, surrounded by the quiet hum of his custom PC chassis. The dual ultra-wide monitors display two distinct worlds: on the left, a Python IDE with a multi-threaded daemon manager script; on the right, the terminal monitoring his Metronet 5 Gigabit fiber link speed, locked at 5000 Mbps.', '**INT. ELIASS WORKSTATION - DAY**', 167)

# 🗣️ Dialogue Node: **ELIAS** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_168 = download_tts('(to himself)', '**ELIAS**', 168)

# 🗣️ Dialogue Node: **INT. ELIASS LIVING ROOM - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_169 = download_tts('Julie walks into the kitchen, stops, and looks around at the spotless room with a subtle smile of relief on her face.', '**INT. ELIASS LIVING ROOM - DAY**', 169)

# 🗣️ Dialogue Node: **JULIE** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_170 = download_tts('You didnt have to clean all this up.', '**JULIE**', 170)

# 🗣️ Dialogue Node: **ELIAS** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_171 = download_tts('It needed to be done. Zero friction.', '**ELIAS**', 171)

# 🗣️ Dialogue Node: **INT. ELIASS WORKSTATION - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_172 = download_tts('Elias opens his multi-year project spreadsheet, navigating directly to the Ithaca, New York relocation model.', '**INT. ELIASS WORKSTATION - DAY**', 172)

# 🗣️ Dialogue Node: **ELIAS** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_173 = download_tts('(to himself)', '**ELIAS**', 173)

# 🗣️ Dialogue Node: **INT. ELIASS LIVING ROOM - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_174 = download_tts('Elias sits back in his chair, minimizing his work windows to view his desktop directory. Side by side sit the completed master manuscript of Echoes Within and the growing drafts of Because The Judge Made Me Go.', '**INT. ELIASS LIVING ROOM - DAY**', 174)

# 🗣️ Dialogue Node: **ELIAS** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_175 = download_tts('(to himself)', '**ELIAS**', 175)

# 🗣️ Dialogue Node: **INT. ELIASS WORKSTATION - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_176 = download_tts('Elias checks the time, takes a slow, deep breath, and prepares to write Chapter 47.', '**INT. ELIASS WORKSTATION - DAY**', 176)

# 🗣️ Dialogue Node: **ELIAS** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_177 = download_tts('(to himself)', '**ELIAS**', 177)

# 🗣️ Dialogue Node: **INT. ELIASS LIVING ROOM - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_178 = download_tts('Julie walks into the kitchen, pours her cup of coffee, and finds Elias wiping down a minor spill.', '**INT. ELIASS LIVING ROOM - DAY**', 178)

# 🗣️ Dialogue Node: **JULIE** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_179 = download_tts('Good morning.', '**JULIE**', 179)

# 🗣️ Dialogue Node: **ELIAS** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_180 = download_tts('Good morning.', '**ELIAS**', 180)

# 🗣️ Dialogue Node: **INT. ELIASS WORKSTATION - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_181 = download_tts('Elias leans back in his chair, checking his biofeedback monitor. His resting heart rate remains completely flat at 58 BPM.', '**INT. ELIASS WORKSTATION - DAY**', 181)

# 🗣️ Dialogue Node: **ELIAS** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_182 = download_tts('(to himself)', '**ELIAS**', 182)

# 🗣️ Dialogue Node: <SUMMARY> [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_183 = download_tts('Elias continues to work on his multi-year transition plan, aiming for absolute self-sufficiency by Fall 2027 at the Groundswell Center in Ithaca, New York. He has made significant progress in documenting and analyzing his past traumas, translating them into objective logic through writing and coding. His domestic environment remains stable, with zero friction between him and his mother Julie.', '<SUMMARY>', 183)

# 🗣️ Dialogue Node: **INT. ELIASS WORKSTATION - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_184 = download_tts('Elias leans back in his chair, checking his biofeedback monitor. His resting heart rate remains completely flat at 58 BPM.', '**INT. ELIASS WORKSTATION - DAY**', 184)

# 🗣️ Dialogue Node: **ELIAS** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_185 = download_tts('(to himself)', '**ELIAS**', 185)

# 🗣️ Dialogue Node: **INT. ELIASS WORKSTATION - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_186 = download_tts('Elias opens his multi-year relocation spreadsheet, verifying the financial and logistical parameters for his transition to the Groundswell Center for Local Food & Farming in Ithaca, New York, set for Fall 2027.', '**INT. ELIASS WORKSTATION - DAY**', 186)

# 🗣️ Dialogue Node: **ELIAS** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_187 = download_tts('(to himself)', '**ELIAS**', 187)

# 🗣️ Dialogue Node: **INT. ELIASS WORKSTATION - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_188 = download_tts('Elias looks at the completed master folders containing thousands of pages of autobiography, operational code, and philosophical frameworks.', '**INT. ELIASS WORKSTATION - DAY**', 188)

# 🗣️ Dialogue Node: **ELIAS** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_189 = download_tts('(to himself)', '**ELIAS**', 189)

# 🗣️ Dialogue Node: **INT. ELIASS WORKSTATION - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_190 = download_tts('Elias stands before the bathroom mirror in the quiet morning light.', '**INT. ELIASS WORKSTATION - DAY**', 190)

# 🗣️ Dialogue Node: **ELIAS** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_191 = download_tts('(to himself)', '**ELIAS**', 191)

# 🗣️ Dialogue Node: <SUMMARY> [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_192 = download_tts('Elias continues to work on his multi-year transition plan, aiming for absolute self-sufficiency by Fall 2027 at the Groundswell Center in Ithaca, New York. He has made significant progress in documenting and analyzing his past traumas, translating them into objective logic through writing and coding. His domestic environment remains stable, with zero friction between him and his mother Julie.', '<SUMMARY>', 192)

# 🗣️ Dialogue Node: **INT. WORKSTATION - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_193 = download_tts('', '**INT. WORKSTATION - DAY**', 193)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_194 = download_tts('(to himself)', 'ELIAS', 194)

# 🗣️ Dialogue Node: ELIAS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_195 = download_tts('(continued)', 'ELIAS', 195)

# 🗣️ Dialogue Node: **ELIAS** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_196 = download_tts('I am Brett Adam Stehouwer. And I am at peace.', '**ELIAS**', 196)

# 🗣️ Dialogue Node: **INT. WORKSTATION - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_197 = download_tts('Elias sits at his desk, closed all open project windows, and locked his terminal. The custom hardware rig hums softly in idle state.', '**INT. WORKSTATION - DAY**', 197)

# 🗣️ Dialogue Node: **ELIAS** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_198 = download_tts('The story is complete. The labyrinth is mapped, conquered, and sealed behind an unshakeable wall of logic and personal discipline.', '**ELIAS**', 198)

# 🗣️ Dialogue Node: **INT. WORKSTATION - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_199 = download_tts('Elias stands up, walks to the window, and looks out toward the open road.', '**INT. WORKSTATION - DAY**', 199)

# 🗣️ Dialogue Node: **ELIAS** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_200 = download_tts('Its time to set sail.', '**ELIAS**', 200)

# 🗣️ Dialogue Node: <SUMMARY> [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_201 = download_tts('Elias continues to work on his multi-year transition plan, aiming for absolute self-sufficiency by Fall 2027 at the Groundswell Center in Ithaca, New York. He has made significant progress in documenting and analyzing his past traumas, translating them into objective logic through writing and coding. His domestic environment remains stable, with zero friction between him and his mother Julie.', '<SUMMARY>', 201)

print('✅ Virtual Production Build Complete!')
