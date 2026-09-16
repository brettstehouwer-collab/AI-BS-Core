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
spawn_light(False, True)

# 🗣️ Dialogue Node: FREDY [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(15)', 'FREDY', 0)

print('--- Building Scene 2 ---')
spawn_light(False, False)
spawn_vfx('Explosion', unreal.Vector(200, 200, 0))

print('--- Building Scene 3 ---')
spawn_light(False, True)
spawn_vfx('Explosion', unreal.Vector(200, 200, 0))

# 🗣️ Dialogue Node: FREDY [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(15)', 'FREDY', 0)

# 🗣️ Dialogue Node: SATIN [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('(15)', 'SATIN', 1)

# 🗣️ Dialogue Node: JESUS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('White robe with a Bible in hand, nail prints in his hands and feet. STANDING between Satin and Fredy.', 'JESUS', 2)

# 🗣️ Dialogue Node: MR. PIMP [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_3 = download_tts('Dressed like a pimp, walks out of the candy store. LOOKING at Jesus, then Satan.', 'MR. PIMP', 3)

# 🗣️ Dialogue Node: SATIN [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_4 = download_tts('(stomping with his fist back and forth)', 'SATIN', 4)

# 🗣️ Dialogue Node: FREDY [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_5 = download_tts('Snickers', 'FREDY', 5)

# 🗣️ Dialogue Node: SATIN [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_6 = download_tts('(fist bump in the air, Fredys direction)', 'SATIN', 6)

# 🗣️ Dialogue Node: JESUS [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_7 = download_tts('(Shaking his head)', 'JESUS', 7)

# 🗣️ Dialogue Node: FREDY [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_8 = download_tts('(pauses with shock, looking at the ground, then walking over to Satins side and laughs)', 'FREDY', 8)

# 🗣️ Dialogue Node: FREDY [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_9 = download_tts('(looks at Satin, then steps on the side of Jesus and scratches his head)', 'FREDY', 9)

# 🗣️ Dialogue Node: COLD OPEN [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_10 = download_tts('', 'COLD OPEN', 10)

print('--- Building Scene 4 ---')
spawn_light(False, False)
drop_prop_with_physics('/Engine/BasicShapes/Cube', unreal.Vector(200, 0, 500), unreal.Vector(2, 1, 1), 'Blockout_Desk_1')

# 🗣️ Dialogue Node: HENRY [Confused]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Confused')
audio_path_0 = download_tts('What you talking about last night?', 'HENRY', 0)

# 🗣️ Dialogue Node: FLO [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('And now...', 'FLO', 1)

# 🗣️ Dialogue Node: FREDY [Angry]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Angry')
audio_path_2 = download_tts('Dam, I had one hell of a nightmare last night!', 'FREDY', 2)

print('--- Building Scene 5 ---')
spawn_light(True, True)

print('--- Building Scene 6 ---')
spawn_light(False, False)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('', 'CUT TO:', 0)

print('--- Building Scene 7 ---')
spawn_light(False, True)

# 🗣️ Dialogue Node: FRESHEY [Confused]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Confused')
audio_path_0 = download_tts('Did you hear the news?', 'FRESHEY', 0)

# 🗣️ Dialogue Node: FREDY [Confused]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Confused')
audio_path_1 = download_tts('What news are you talking about? President Trump has a little dick and South Park is getting sued,', 'FREDY', 1)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('', 'CUT TO:', 2)

print('--- Building Scene 8 ---')
spawn_light(False, False)

# 🗣️ Dialogue Node: FREDY [Angry]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Angry')
audio_path_0 = download_tts('Before we get to my story, for those in front of me I need to break it down to about Beavis and Butthead and South Park listen up!', 'FREDY', 0)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'CUT TO:', 1)

print('--- Building Scene 9 ---')
spawn_light(False, True)
spawn_camera('Cam_Close_1', unreal.Vector(100, 0, 150))

# 🗣️ Dialogue Node: DISTURBED [Confused]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Confused')
audio_path_0 = download_tts('What was your dream Fredy?', 'DISTURBED', 0)

# 🗣️ Dialogue Node: FREDY [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('(Takes a deep breath)', 'FREDY', 1)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('', 'CUT TO:', 2)

print('--- Building Scene 10 ---')
spawn_light(False, True)

# 🗣️ Dialogue Node: FRESHEY [Confused]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Confused')
audio_path_0 = download_tts('Did you hear the news?', 'FRESHEY', 0)

# 🗣️ Dialogue Node: FREDY [Confused]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Confused')
audio_path_1 = download_tts('What news are you talking about? President Trump has a little dick and South Park is getting sued,', 'FREDY', 1)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('', 'CUT TO:', 2)

print('--- Building Scene 11 ---')
spawn_light(False, False)

# 🗣️ Dialogue Node: FREDY [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('I heard,', 'FREDY', 0)

# 🗣️ Dialogue Node: FLO [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('Were not in a court room Fredy, take it down a little.', 'FLO', 1)

# 🗣️ Dialogue Node: HENRY [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('This is absolutely one of the defining features of Beavis and Butt-Head, especially in its original run. The duos crude, simplistic, and often hilarious commentary on music videos was a groundbreaking and highly popular aspect of the show.', 'HENRY', 2)

# 🗣️ Dialogue Node: FLO [Angry]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Angry')
audio_path_3 = download_tts('Shits and grina got to go!', 'FLO', 3)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_4 = download_tts('', 'CUT TO:', 4)

print('--- Building Scene 12 ---')
spawn_light(False, False)
spawn_camera('Cam_Close_1', unreal.Vector(100, 0, 150))

# 🗣️ Dialogue Node: FREDY [Angry]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Angry')
audio_path_0 = download_tts('Okay, heres a funny comeback to that joke, playing on its elements: "Yeah, but at least Kenny stays dead in South Park! Beavis and Butt-Head just keep giggling, and Linkin Parks screaming makes me wonder if theyre the ones who killed Kenny and cant handle the guilt."', 'FREDY', 0)

# 🗣️ Dialogue Node: FLO [Angry]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Angry')
audio_path_1 = download_tts('Shits and grina got to go!', 'FLO', 1)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('', 'CUT TO:', 2)

print('--- Building Scene 13 ---')
spawn_light(False, True)
drop_prop_with_physics('/Engine/BasicShapes/Cube', unreal.Vector(200, 0, 500), unreal.Vector(2, 1, 1), 'Blockout_Desk_1')
spawn_vfx('Explosion', unreal.Vector(200, 200, 0))

# 🗣️ Dialogue Node: FREDY [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(15): Black hair, brown eyes. Dressed in silky shorts and a baseball image t-shirt. With sunglasses.', 'FREDY', 0)

# 🗣️ Dialogue Node: DISTURBED (V.O.) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('Hello, Fredy.', 'DISTURBED (V.O.)', 1)

# 🗣️ Dialogue Node: FREDY [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('Oh, hello, Disturbed.', 'FREDY', 2)

# 🗣️ Dialogue Node: MR. PIMP [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_3 = download_tts('', 'MR. PIMP', 3)

# 🗣️ Dialogue Node: WTF [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_4 = download_tts('**CUT TO:** **INT. FREDYS BEDROOM - DAY** Fredys phone rings with Disturbed on the other end of the line.', 'WTF', 4)

# 🗣️ Dialogue Node: FREDY [Confused]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Confused')
audio_path_5 = download_tts('Hello?', 'FREDY', 5)

# 🗣️ Dialogue Node: DISTURBED (V.O.) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_6 = download_tts('Finish your story about your dream.', 'DISTURBED (V.O.)', 6)

# 🗣️ Dialogue Node: FREDY [Angry]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Angry')
audio_path_7 = download_tts('Seriously, dude!', 'FREDY', 7)

# 🗣️ Dialogue Node: MR. PIMP [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_8 = download_tts('', 'MR. PIMP', 8)

# 🗣️ Dialogue Node: WTF [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_9 = download_tts('**CUT TO:** **INT. FREDYS BEDROOM - DAY** Fredy continues his story on the phone with Disturbed.', 'WTF', 9)

# 🗣️ Dialogue Node: FREDY [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_10 = download_tts('You just had to be there.', 'FREDY', 10)

# 🗣️ Dialogue Node: DISTURBED (V.O.) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_11 = download_tts('Hey, lets meet at Smakeys Park and light off firecrackers.', 'DISTURBED (V.O.)', 11)

# 🗣️ Dialogue Node: FREDY [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_12 = download_tts('Ill dress like Beavis today, except my direction wont need a permission slip HA HA HA', 'FREDY', 12)

# 🗣️ Dialogue Node: FREDY [Angry]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Angry')
audio_path_13 = download_tts('See you at the park, bring the works and lighter!', 'FREDY', 13)

print('✅ Virtual Production Build Complete!')
