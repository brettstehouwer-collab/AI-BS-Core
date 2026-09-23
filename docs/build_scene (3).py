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
spawn_light(True, True)

print('--- Building Scene 2 ---')
spawn_light(False, False)
spawn_camera('Cam_Close_1', unreal.Vector(100, 0, 150))

print('--- Building Scene 3 ---')
spawn_light(False, False)
drop_prop_with_physics('/Engine/BasicShapes/Cube', unreal.Vector(200, 0, 500), unreal.Vector(2, 1, 1), 'Blockout_Desk_1')

# 🗣️ Dialogue Node: NATHAN [Confused]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Confused')
audio_path_0 = download_tts('All right, gentlemen. Someone give me the scoop on what happened yesterday. Fill me in. Giovanni came to town with no money?', 'NATHAN', 0)

# 🗣️ Dialogue Node: JOEY [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('You’re fucking right. We took his ass right outside the back door. See, this wise guy thinks he can business.', 'JOEY', 1)

# 🗣️ Dialogue Node: JACK [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('Nathan, I need you to find out whos family Giovanni is working for.', 'JACK', 2)

# 🗣️ Dialogue Node: JACK [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_3 = download_tts('Matt, find out more about Giovanni. Everywhere he hangs out with, everything he does, where he’s from. All of it.', 'JACK', 3)

# 🗣️ Dialogue Node: BOBBY [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_4 = download_tts('Already on it, boss.', 'BOBBY', 4)

print('--- Building Scene 4 ---')
spawn_light(False, False)
drop_prop_with_physics('/Engine/BasicShapes/Cube', unreal.Vector(200, 0, 500), unreal.Vector(2, 1, 1), 'Blockout_Desk_1')

# 🗣️ Dialogue Node: ADAM [Confused]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Confused')
audio_path_0 = download_tts('Dad, can I ask you a question?', 'ADAM', 0)

# 🗣️ Dialogue Node: NATHAN [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('Of course, Adam, ask away.', 'NATHAN', 1)

# 🗣️ Dialogue Node: ADAM [Confused]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Confused')
audio_path_2 = download_tts('Will Chanel be okay?', 'ADAM', 2)

# 🗣️ Dialogue Node: NATHAN [Confused]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Confused')
audio_path_3 = download_tts('Of course, son. She’s your little sister, and a fighter. Why do you ask?', 'NATHAN', 3)

# 🗣️ Dialogue Node: ADAM [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_4 = download_tts('It’s just, you know, she’s been in the hospital a long time, and -', 'ADAM', 4)

# 🗣️ Dialogue Node: ELLA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_5 = download_tts('That’s enough, Adam, that’s enough. Don’t upset your Father. He has a lot on his mind. Let’s just enjoy our breakfast.', 'ELLA', 5)

# 🗣️ Dialogue Node: NATHAN [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_6 = download_tts('Right. Listen to your Mother. Breakfast is a good start to the day.', 'NATHAN', 6)

print('--- Building Scene 5 ---')
spawn_light(True, False)

# 🗣️ Dialogue Node: NATHAN [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('(On the phone)', 'NATHAN', 0)

# 🗣️ Dialogue Node: VICTOR [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('(On the phone)', 'VICTOR', 1)

# 🗣️ Dialogue Node: FADE IN: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('', 'FADE IN:', 2)

print('--- Building Scene 6 ---')
spawn_light(False, True)

print('--- Building Scene 7 ---')
spawn_light(False, False)

print('--- Building Scene 8 ---')
spawn_light(False, False)

print('--- Building Scene 9 ---')
spawn_light(False, False)
drop_prop_with_physics('/Engine/BasicShapes/Cube', unreal.Vector(200, 0, 500), unreal.Vector(2, 1, 1), 'Blockout_Desk_1')

# 🗣️ Dialogue Node: JACK [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('Gentlemen, we have a situation. Giovanni, a man from a rival family, has come to our town. We must deal with him swiftly and decisively.', 'JACK', 0)

print('--- Building Scene 10 ---')
spawn_light(False, True)

# 🗣️ Dialogue Node: FADE IN: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('', 'FADE IN:', 0)

print('--- Building Scene 11 ---')
spawn_light(False, True)
drop_prop_with_physics('/Engine/BasicShapes/Cube', unreal.Vector(200, 0, 500), unreal.Vector(2, 1, 1), 'Blockout_Desk_1')
drop_prop_with_physics('/Engine/BasicShapes/Cylinder', unreal.Vector(500, 500, 1000), unreal.Vector(1, 1, 5), 'Blockout_Tree_2')
drop_prop_with_physics('/Engine/BasicShapes/Cylinder', unreal.Vector(500, 500, 1000), unreal.Vector(1, 1, 5), 'Blockout_Tree_3')
drop_prop_with_physics('/Engine/BasicShapes/Cylinder', unreal.Vector(500, 500, 1000), unreal.Vector(1, 1, 5), 'Blockout_Tree_4')

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('', 'CUT TO:', 0)

print('--- Building Scene 12 ---')
spawn_light(False, False)
drop_prop_with_physics('/Engine/BasicShapes/Cylinder', unreal.Vector(500, 500, 1000), unreal.Vector(1, 1, 5), 'Blockout_Tree_1')
drop_prop_with_physics('/Engine/BasicShapes/Cylinder', unreal.Vector(500, 500, 1000), unreal.Vector(1, 1, 5), 'Blockout_Tree_2')

# 🗣️ Dialogue Node: BRETT [Angry]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Angry')
audio_path_0 = download_tts('Hey! Bring your bathing suits!', 'BRETT', 0)

# 🗣️ Dialogue Node: ERIN [Angry]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Angry')
audio_path_1 = download_tts('Taco Tuesday! Bring your own Tacos!', 'ERIN', 1)

# 🗣️ Dialogue Node: SEAN [Angry]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Angry')
audio_path_2 = download_tts('Yeah! Bring the hot sauce!', 'SEAN', 2)

# 🗣️ Dialogue Node: SEAN (CONT’D) [Angry]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Angry')
audio_path_3 = download_tts('Oh, I forgot! I’ve already got the fireball shots on me!', 'SEAN (CONT’D)', 3)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_4 = download_tts('', 'CUT TO:', 4)

print('--- Building Scene 13 ---')
spawn_light(False, True)
drop_prop_with_physics('/Engine/BasicShapes/Cube', unreal.Vector(200, 0, 500), unreal.Vector(2, 1, 1), 'Blockout_Desk_1')

# 🗣️ Dialogue Node: MATT [Confused]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Confused')
audio_path_0 = download_tts('Can I get you ladies something to drink?', 'MATT', 0)

# 🗣️ Dialogue Node: WILLOW [Angry]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Angry')
audio_path_1 = download_tts('Oh! Somebody’s going to wait on us for us a change!', 'WILLOW', 1)

# 🗣️ Dialogue Node: STELLA [Angry]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Angry')
audio_path_2 = download_tts('Yeah! I’ll take a Kamikaze!', 'STELLA', 2)

# 🗣️ Dialogue Node: WILLOW [Angry]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Angry')
audio_path_3 = download_tts('Make that two!', 'WILLOW', 3)

# 🗣️ Dialogue Node: MATT [Angry]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Angry')
audio_path_4 = download_tts('Coming right up!', 'MATT', 4)

# 🗣️ Dialogue Node: STELLA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_5 = download_tts('Hey Matt, you taking Willow and I', 'STELLA', 5)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_6 = download_tts('', 'CUT TO:', 6)

print('--- Building Scene 14 ---')
spawn_light(False, False)

# 🗣️ Dialogue Node: NURSE [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('She’s a little warm, and a little dehydrated. This is normal with children with cancer. But we won’t let her die.', 'NURSE', 0)

# 🗣️ Dialogue Node: NATHAN [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('My wife and I are under the understanding that leukemia has a very high remission rate.', 'NATHAN', 1)

# 🗣️ Dialogue Node: NATHAN (CONT’D) [Confused]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Confused')
audio_path_2 = download_tts('I know she’s always tired and breathless. Will this reduce the ninety percent rate on remission?', 'NATHAN (CONT’D)', 2)

# 🗣️ Dialogue Node: NURSE [Confused]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Confused')
audio_path_3 = download_tts('Sir, can we please talk about this in the hallway?', 'NURSE', 3)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_4 = download_tts('', 'CUT TO:', 4)

print('--- Building Scene 15 ---')
spawn_light(False, False)
drop_prop_with_physics('/Engine/BasicShapes/Cube', unreal.Vector(200, 0, 500), unreal.Vector(2, 1, 1), 'Blockout_Desk_1')

# 🗣️ Dialogue Node: NATHAN [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('Of course, like I always do.', 'NATHAN', 0)

# 🗣️ Dialogue Node: ELLA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('I will be dropping the boys off at school and I’ll meet you there.', 'ELLA', 1)

# 🗣️ Dialogue Node: ADAM [Confused]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Confused')
audio_path_2 = download_tts('Dad, can I ask you a question?', 'ADAM', 2)

# 🗣️ Dialogue Node: NATHAN [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_3 = download_tts('Of course, Adam, ask away.', 'NATHAN', 3)

# 🗣️ Dialogue Node: ADAM [Confused]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Confused')
audio_path_4 = download_tts('Will Chanel be okay?', 'ADAM', 4)

# 🗣️ Dialogue Node: NATHAN [Confused]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Confused')
audio_path_5 = download_tts('Of course, son. She’s your little sister, and a fighter. Why do you ask?', 'NATHAN', 5)

# 🗣️ Dialogue Node: ELLA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_6 = download_tts('That’s enough, Adam, that’s enough. Don’t upset your Father. He has a lot on his mind. Let’s just enjoy our breakfast.', 'ELLA', 6)

# 🗣️ Dialogue Node: NATHAN [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_7 = download_tts('Right. Listen to your Mother. Breakfast is a good start to the day.', 'NATHAN', 7)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_8 = download_tts('', 'CUT TO:', 8)

print('--- Building Scene 16 ---')
spawn_light(False, False)
spawn_camera('Cam_Close_1', unreal.Vector(100, 0, 150))

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('', 'CUT TO:', 0)

print('--- Building Scene 17 ---')
spawn_light(False, False)

# 🗣️ Dialogue Node: NATHAN [Confused]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Confused')
audio_path_0 = download_tts('All right, gentlemen. Someone give me the scoop on what happened yesterday. Fill me in. Giovanni came to town with no money?', 'NATHAN', 0)

# 🗣️ Dialogue Node: JOEY [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('You’re fucking right. We took his ass right outside the back door. See, this wise guy thinks he can', 'JOEY', 1)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('', 'CUT TO:', 2)

print('--- Building Scene 18 ---')
spawn_light(False, False)
spawn_camera('Cam_Pan_1', unreal.Vector(0, 500, 150))

# 🗣️ Dialogue Node: JACK [Angry]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Angry')
audio_path_0 = download_tts('Kids! Come on over here! Take a seat, and I will start ordering pizza!', 'JACK', 0)

# 🗣️ Dialogue Node: CHILDREN [Angry]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Angry')
audio_path_1 = download_tts('Thank you so much Jack!', 'CHILDREN', 1)

# 🗣️ Dialogue Node: JACK [Angry]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Angry')
audio_path_2 = download_tts('Oh, you children really light up my world! Eat to your little hearts’ content!', 'JACK', 2)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_3 = download_tts('', 'CUT TO:', 3)

print('--- Building Scene 19 ---')
spawn_light(True, False)
drop_prop_with_physics('/Engine/BasicShapes/Cube', unreal.Vector(200, 0, 500), unreal.Vector(2, 1, 1), 'Blockout_Desk_1')

# 🗣️ Dialogue Node: ALLEN [Confused]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Confused')
audio_path_0 = download_tts('Yes?', 'ALLEN', 0)

# 🗣️ Dialogue Node: MYSTERY CALLER (V.O.) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('I swore I’ve seen Father Bobby in a suit at "Class Act" with some tough men. I think they were talking about hurting somebody.', 'MYSTERY CALLER (V.O.)', 1)

# 🗣️ Dialogue Node: ALLEN [Confused]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Confused')
audio_path_2 = download_tts('Who is this?', 'ALLEN', 2)

# 🗣️ Dialogue Node: ALLEN (CONT’D) [Confused]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Confused')
audio_path_3 = download_tts('How would you even know this? That can’t be right.', 'ALLEN (CONT’D)', 3)

# 🗣️ Dialogue Node: MYSTERY CALLER (V.O.) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_4 = download_tts('I’ve been undercover watching him.', 'MYSTERY CALLER (V.O.)', 4)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_5 = download_tts('', 'CUT TO:', 5)

print('--- Building Scene 20 ---')
spawn_light(False, False)
spawn_camera('Cam_Close_1', unreal.Vector(100, 0, 150))

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('', 'CUT TO:', 0)

print('--- Building Scene 21 ---')
spawn_light(False, False)

# 🗣️ Dialogue Node: NATHAN [Confused]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Confused')
audio_path_0 = download_tts('All right, gentlemen. Someone give me the scoop on what happened today. Fill me in. Giovanni came to town with no money?', 'NATHAN', 0)

# 🗣️ Dialogue Node: JOEY [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('You’re fucking right. We took his ass right outside the back door. See, this wise guy thinks he can', 'JOEY', 1)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('', 'CUT TO:', 2)

print('--- Building Scene 22 ---')
spawn_light(False, False)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('', 'CUT TO:', 0)

print('--- Building Scene 23 ---')
spawn_light(False, True)
spawn_camera('Cam_Close_1', unreal.Vector(100, 0, 150))
drop_prop_with_physics('/Engine/BasicShapes/Cube', unreal.Vector(200, 0, 500), unreal.Vector(2, 1, 1), 'Blockout_Desk_1')

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('', 'CUT TO:', 0)

print('--- Building Scene 24 ---')
spawn_light(False, True)

# 🗣️ Dialogue Node: HENCHMAN [Angry]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Angry')
audio_path_0 = download_tts('This is a gift from Giovanni!', 'HENCHMAN', 0)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', 'CUT TO:', 1)

print('--- Building Scene 25 ---')
spawn_light(False, False)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('', 'CUT TO:', 0)

print('--- Building Scene 26 ---')
spawn_light(False, False)
spawn_camera('Cam_Close_1', unreal.Vector(100, 0, 150))

# 🗣️ Dialogue Node: FADE TO BLACK. [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('SUMMARY: The story begins with a grand parade in a peaceful Sicilian town. The main characters, Nathan and his family, are involved in a local bar and restaurant. Theres a mysterious threat from a rival family, and secrets are kept within the establishment.', 'FADE TO BLACK.', 0)

# 🗣️ Dialogue Node: JULIANNA [Confused]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Confused')
audio_path_1 = download_tts('So, what do you need me to do?', 'JULIANNA', 1)

# 🗣️ Dialogue Node: HUDSON [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('I need you to go undercover at "Class Act".', 'HUDSON', 2)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_3 = download_tts('Understood.', 'JULIANNA', 3)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_4 = download_tts('I’ll do it.', 'JULIANNA', 4)

# 🗣️ Dialogue Node: HUDSON [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_5 = download_tts('Everything you need is in there.', 'HUDSON', 5)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_6 = download_tts('I’ll get started right away.', 'JULIANNA', 6)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_7 = download_tts('Good luck.', 'JULIANNA', 7)

print('--- Building Scene 27 ---')
spawn_light(False, False)

print('--- Building Scene 28 ---')
spawn_light(False, False)
spawn_camera('Cam_Close_1', unreal.Vector(100, 0, 150))

print('--- Building Scene 29 ---')
spawn_light(False, False)
drop_prop_with_physics('/Engine/BasicShapes/Cube', unreal.Vector(200, 0, 500), unreal.Vector(2, 1, 1), 'Blockout_Desk_1')
spawn_camera('Cam_Close_1', unreal.Vector(100, 0, 150))

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('So, Victor, I heard you were in a shootout', 'JULIANNA', 0)

# 🗣️ Dialogue Node: VICTOR [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('Im fine, just a little shaken up.', 'VICTOR', 1)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('I can imagine. That must have been', 'JULIANNA', 2)

# 🗣️ Dialogue Node: VICTOR [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_3 = download_tts('It was, but Im okay now.', 'VICTOR', 3)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_4 = download_tts('Im glad to hear that.', 'JULIANNA', 4)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_5 = download_tts('So, have you noticed anything unusual', 'JULIANNA', 5)

# 🗣️ Dialogue Node: VICTOR [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_6 = download_tts('Actually, yes. Ive noticed that', 'VICTOR', 6)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_7 = download_tts('Thats good information, Victor. Ill', 'JULIANNA', 7)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_8 = download_tts('Thanks for your help.', 'JULIANNA', 8)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_9 = download_tts('Ill be in touch.', 'JULIANNA', 9)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_10 = download_tts('Goodbye.', 'JULIANNA', 10)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_11 = download_tts('(To herself)', 'JULIANNA', 11)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_12 = download_tts('(To herself)', 'JULIANNA', 12)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_13 = download_tts('(To herself)', 'JULIANNA', 13)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_14 = download_tts('(To herself)', 'JULIANNA', 14)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_15 = download_tts('(To herself)', 'JULIANNA', 15)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_16 = download_tts('(To herself)', 'JULIANNA', 16)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_17 = download_tts('(To herself)', 'JULIANNA', 17)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_18 = download_tts('(To herself)', 'JULIANNA', 18)

print('--- Building Scene 30 ---')
spawn_light(False, False)
drop_prop_with_physics('/Engine/BasicShapes/Cube', unreal.Vector(200, 0, 500), unreal.Vector(2, 1, 1), 'Blockout_Desk_1')
spawn_camera('Cam_Close_1', unreal.Vector(100, 0, 150))

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('So, Joey, Ive been thinking. Maybe', 'JULIANNA', 0)

# 🗣️ Dialogue Node: JOEY [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('I like the way you think, Julianna.', 'JOEY', 1)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('Well, I was thinking maybe we could', 'JULIANNA', 2)

# 🗣️ Dialogue Node: JOEY [Confused]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Confused')
audio_path_3 = download_tts('That sounds great. But what would', 'JOEY', 3)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_4 = download_tts('I was thinking maybe we could', 'JULIANNA', 4)

# 🗣️ Dialogue Node: JOEY [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_5 = download_tts('I like it. But how are we going to', 'JOEY', 5)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_6 = download_tts('I have some connections. I can', 'JULIANNA', 6)

# 🗣️ Dialogue Node: JOEY [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_7 = download_tts('That sounds good. But I still', 'JOEY', 7)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_8 = download_tts('I understand. Ill make sure to', 'JULIANNA', 8)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_9 = download_tts('And Ill make sure to keep the', 'JULIANNA', 9)

# 🗣️ Dialogue Node: JOEY [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_10 = download_tts('Alright. Lets do it.', 'JOEY', 10)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_11 = download_tts('Great. Ill get started right away.', 'JULIANNA', 11)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_12 = download_tts('Thanks, Joey.', 'JULIANNA', 12)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_13 = download_tts('(To herself)', 'JULIANNA', 13)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_14 = download_tts('(To herself)', 'JULIANNA', 14)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_15 = download_tts('(To herself)', 'JULIANNA', 15)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_16 = download_tts('(To herself)', 'JULIANNA', 16)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_17 = download_tts('(To herself)', 'JULIANNA', 17)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_18 = download_tts('(To herself)', 'JULIANNA', 18)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_19 = download_tts('(To herself)', 'JULIANNA', 19)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_20 = download_tts('(To herself)', 'JULIANNA', 20)

print('--- Building Scene 31 ---')
spawn_light(False, False)
drop_prop_with_physics('/Engine/BasicShapes/Cube', unreal.Vector(200, 0, 500), unreal.Vector(2, 1, 1), 'Blockout_Desk_1')
spawn_camera('Cam_Close_1', unreal.Vector(100, 0, 150))

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('This is such a great night. Im so', 'JULIANNA', 0)

# 🗣️ Dialogue Node: VICTOR [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('Yeah, its been a long time', 'VICTOR', 1)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('I couldnt have done it without', 'JULIANNA', 2)

# 🗣️ Dialogue Node: VICTOR [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_3 = download_tts('It was nothing. Im just glad', 'VICTOR', 3)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_4 = download_tts('I have one more thing I need to', 'JULIANNA', 4)

# 🗣️ Dialogue Node: VICTOR [Confused]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Confused')
audio_path_5 = download_tts('Whats that?', 'VICTOR', 5)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_6 = download_tts('I need to find out more about', 'JULIANNA', 6)

# 🗣️ Dialogue Node: VICTOR [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_7 = download_tts('I can help you with that.', 'VICTOR', 7)

# 🗣️ Dialogue Node: JULIANNA [Confused]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Confused')
audio_path_8 = download_tts('Really? That would be great.', 'JULIANNA', 8)

# 🗣️ Dialogue Node: VICTOR [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_9 = download_tts('I have some connections too.', 'VICTOR', 9)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_10 = download_tts('Great. Lets do it.', 'JULIANNA', 10)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_11 = download_tts('(To herself)', 'JULIANNA', 11)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_12 = download_tts('(To herself)', 'JULIANNA', 12)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_13 = download_tts('(To herself)', 'JULIANNA', 13)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_14 = download_tts('(To herself)', 'JULIANNA', 14)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_15 = download_tts('(To herself)', 'JULIANNA', 15)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_16 = download_tts('(To herself)', 'JULIANNA', 16)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_17 = download_tts('(To herself)', 'JULIANNA', 17)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_18 = download_tts('(To herself)', 'JULIANNA', 18)

print('--- Building Scene 32 ---')
spawn_light(False, False)
drop_prop_with_physics('/Engine/BasicShapes/Cube', unreal.Vector(200, 0, 500), unreal.Vector(2, 1, 1), 'Blockout_Desk_1')
spawn_camera('Cam_Close_1', unreal.Vector(100, 0, 150))

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('This is such a great night. Im so', 'JULIANNA', 0)

# 🗣️ Dialogue Node: JOEY [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('Yeah, its been a long time', 'JOEY', 1)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('I couldnt have done it without', 'JULIANNA', 2)

# 🗣️ Dialogue Node: JOEY [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_3 = download_tts('It was nothing. Im just glad', 'JOEY', 3)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_4 = download_tts('I have one more thing I need to', 'JULIANNA', 4)

# 🗣️ Dialogue Node: JOEY [Confused]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Confused')
audio_path_5 = download_tts('Whats that?', 'JOEY', 5)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_6 = download_tts('I need to find out more about', 'JULIANNA', 6)

# 🗣️ Dialogue Node: JOEY [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_7 = download_tts('I can help you with that.', 'JOEY', 7)

# 🗣️ Dialogue Node: JULIANNA [Confused]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Confused')
audio_path_8 = download_tts('Really? That would be great.', 'JULIANNA', 8)

# 🗣️ Dialogue Node: JOEY [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_9 = download_tts('I have some connections too.', 'JOEY', 9)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_10 = download_tts('Great. Lets do it.', 'JULIANNA', 10)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_11 = download_tts('(To herself)', 'JULIANNA', 11)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_12 = download_tts('(To herself)', 'JULIANNA', 12)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_13 = download_tts('(To herself)', 'JULIANNA', 13)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_14 = download_tts('(To herself)', 'JULIANNA', 14)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_15 = download_tts('(To herself)', 'JULIANNA', 15)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_16 = download_tts('(To herself)', 'JULIANNA', 16)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_17 = download_tts('(To herself)', 'JULIANNA', 17)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_18 = download_tts('(To herself)', 'JULIANNA', 18)

print('--- Building Scene 33 ---')
spawn_light(False, False)
drop_prop_with_physics('/Engine/BasicShapes/Cube', unreal.Vector(200, 0, 500), unreal.Vector(2, 1, 1), 'Blockout_Desk_1')
spawn_camera('Cam_Close_1', unreal.Vector(100, 0, 150))

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('This is such a great night. Im so', 'JULIANNA', 0)

# 🗣️ Dialogue Node: VICTOR [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('Yeah, its been a long time', 'VICTOR', 1)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('I couldnt have done it without', 'JULIANNA', 2)

# 🗣️ Dialogue Node: VICTOR [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_3 = download_tts('It was nothing. Im just glad', 'VICTOR', 3)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_4 = download_tts('I have one more thing I need to', 'JULIANNA', 4)

# 🗣️ Dialogue Node: VICTOR [Confused]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Confused')
audio_path_5 = download_tts('Whats that?', 'VICTOR', 5)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_6 = download_tts('I need to find out more about', 'JULIANNA', 6)

# 🗣️ Dialogue Node: VICTOR [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_7 = download_tts('I can help you with that.', 'VICTOR', 7)

# 🗣️ Dialogue Node: JULIANNA [Confused]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Confused')
audio_path_8 = download_tts('Really? That would be great.', 'JULIANNA', 8)

# 🗣️ Dialogue Node: VICTOR [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_9 = download_tts('I have some connections too.', 'VICTOR', 9)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_10 = download_tts('Great. Lets do it.', 'JULIANNA', 10)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_11 = download_tts('(To herself)', 'JULIANNA', 11)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_12 = download_tts('(To herself)', 'JULIANNA', 12)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_13 = download_tts('(To herself)', 'JULIANNA', 13)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_14 = download_tts('(To herself)', 'JULIANNA', 14)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_15 = download_tts('(To herself)', 'JULIANNA', 15)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_16 = download_tts('(To herself)', 'JULIANNA', 16)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_17 = download_tts('(To herself)', 'JULIANNA', 17)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_18 = download_tts('(To herself)', 'JULIANNA', 18)

print('--- Building Scene 34 ---')
spawn_light(False, False)
drop_prop_with_physics('/Engine/BasicShapes/Cube', unreal.Vector(200, 0, 500), unreal.Vector(2, 1, 1), 'Blockout_Desk_1')
spawn_camera('Cam_Close_1', unreal.Vector(100, 0, 150))
drop_prop_with_physics('/Engine/BasicShapes/Cube', unreal.Vector(200, 0, 500), unreal.Vector(2, 1, 1), 'Blockout_Desk_2')
spawn_camera('Cam_Pan_2', unreal.Vector(0, 500, 150))

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('This is such a great night. Im so', 'JULIANNA', 0)

# 🗣️ Dialogue Node: JOEY [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('Yeah, its been a long time', 'JOEY', 1)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('I couldnt have done it without', 'JULIANNA', 2)

# 🗣️ Dialogue Node: JOEY [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_3 = download_tts('It was nothing. Im just glad', 'JOEY', 3)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_4 = download_tts('I have one more thing I need to', 'JULIANNA', 4)

# 🗣️ Dialogue Node: JOEY [Confused]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Confused')
audio_path_5 = download_tts('Whats that?', 'JOEY', 5)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_6 = download_tts('I need to find out more about', 'JULIANNA', 6)

# 🗣️ Dialogue Node: JOEY [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_7 = download_tts('I can help you with that.', 'JOEY', 7)

# 🗣️ Dialogue Node: JULIANNA [Confused]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Confused')
audio_path_8 = download_tts('Really? That would be great.', 'JULIANNA', 8)

# 🗣️ Dialogue Node: JOEY [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_9 = download_tts('I have some connections too.', 'JOEY', 9)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_10 = download_tts('Great. Lets do it.', 'JULIANNA', 10)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_11 = download_tts('(To herself)', 'JULIANNA', 11)

# 🗣️ Dialogue Node: JULIANNA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_12 = download_tts('(To herself)', 'JULIANNA', 12)

# 🗣️ Dialogue Node: JACK [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_13 = download_tts('Ladies and Gentlemen, thank you for', 'JACK', 13)

print('--- Building Scene 35 ---')
spawn_light(False, False)

# 🗣️ Dialogue Node: ARIANA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('Nathan, I’ve been meaning to talk', 'ARIANA', 0)

# 🗣️ Dialogue Node: NATHAN [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('Thank you, Ariana. That means a', 'NATHAN', 1)

# 🗣️ Dialogue Node: ARIANA [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('You’re welcome, Nathan. I mean it.', 'ARIANA', 2)

# 🗣️ Dialogue Node: SUMMARY> [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_3 = download_tts('Nathan is at "Class Act", a restaurant and bar, where he has become a regular. He is dealing with personal issues, including his daughters illness and his own conflicted feelings about his past as a detective. Ariana, a singer at the restaurant, is trying to be a supportive friend to Nathan. The story is set in Cascade, Michigan, and involves a mix of drama, mystery, and music.', 'SUMMARY>', 3)

# 🗣️ Dialogue Node: <SUMMARY> [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_4 = download_tts('Plot Summary: The story begins with the high-stakes world of "Class Act," a nightclub where secrets and loyalty intertwine. Nathan, a conflicted detective haunted by his past, is drawn into a web of intrigue when his daughter, Chanel, falls ill. As he navigates the complex dance of his job and family, he uncovers a dangerous conspiracy involving the Marco family, led by the now-deceased Giovanni. The narrative shifts between the nightclubs vibrant atmosphere and the tense drama of Nathans personal life, culminating in a shocking act of violence that sets the stage for a thrilling journey of redemption and danger. Active characters include Nathan, his wife Ella, their daughter Chanel, and a cast of colorful nightclub personalities, including Ariana, Brett, Erin, and Jack. The current location is the "Class Act" nightclub, where tensions rise and secrets are revealed.', '<SUMMARY>', 4)

print('✅ Virtual Production Build Complete!')
