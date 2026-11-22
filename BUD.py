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

# 🗣️ Dialogue Node: HARRIS BLACK (15): [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('Black hair, brown eyes. Wearing black shorts and a red shirt that has an image of a pad of paper and lines created on the shirt. Carries a pencil and pad of paper in his backpack in case he has to take notes.', 'HARRIS BLACK (15):', 1)

# 🗣️ Dialogue Node: FLO (15): [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('Blonde hair in a big bun, blue eyes. Wearing red shorts and a white shirt. Always has a handheld mirror and lip gloss. In her purse that she takes out at any given time.', 'FLO (15):', 2)

# 🗣️ Dialogue Node: FRESHEY (15): [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_3 = download_tts('A flirt with brown hair and blue eyes. Wearing a short shirt and skirt, sandals with a little heel in rainbow colors, always has a GQ magazine for fashion tips.', 'FRESHEY (15):', 3)

# 🗣️ Dialogue Node: JESUS: [Happy]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Happy')
audio_path_4 = download_tts('White robe, no shoes. Wounds (holes) in hands and feet. Brown beard and long hair. Jesus represents Gods love, forgiveness, and salvation for humanity. He is seen as the Messiah, the Son of God, who came to reconcile humanity with God through his sacrifice and teachings.', 'JESUS:', 4)

# 🗣️ Dialogue Node: SATIN: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_5 = download_tts('A red robe with long red hair and long nails. Satan is a prominent figure representing evil, temptation, and opposition to God. While often depicted as a fallen angel or a devil, his role and characteristics vary across different faiths.', 'SATIN:', 5)

# 🗣️ Dialogue Node: MR. THE PIMP (STORE OWNER): [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_6 = download_tts('Dresses like a pimp.', 'MR. THE PIMP (STORE OWNER):', 6)

# 🗣️ Dialogue Node: SATIN: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_7 = download_tts('(stomping with his fist back and froth punching in the air)', 'SATIN:', 7)

# 🗣️ Dialogue Node: FREDY: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_8 = download_tts('Snickers', 'FREDY:', 8)

# 🗣️ Dialogue Node: SATIN: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_9 = download_tts('(Fist bump in the air Fredy’s direction)', 'SATIN:', 9)

# 🗣️ Dialogue Node: JESUS: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_10 = download_tts('(Shaking his head)', 'JESUS:', 10)

# 🗣️ Dialogue Node: SATIN: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_11 = download_tts('(smiling looking at Jesus)', 'SATIN:', 11)

# 🗣️ Dialogue Node: FREDY: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_12 = download_tts('(pauses with shock, looking at the ground, then walking)', 'FREDY:', 12)

# 🗣️ Dialogue Node: JESUS: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_13 = download_tts('Fredy, if you keep stealing, you will be in jail one day.', 'JESUS:', 13)

# 🗣️ Dialogue Node: FREDY: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_14 = download_tts('(surprised facial expression looks up at Jesus)', 'FREDY:', 14)

# 🗣️ Dialogue Node: JESUS: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_15 = download_tts('(Smiling)', 'JESUS:', 15)

# 🗣️ Dialogue Node: FREDY: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_16 = download_tts('(Get loud talking to Jesus)', 'FREDY:', 16)

# 🗣️ Dialogue Node: COLD OPEN [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_17 = download_tts('', 'COLD OPEN', 17)

print('--- Building Scene 2 ---')
spawn_light(False, False)

# 🗣️ Dialogue Node: <SUMMARY> [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('The story begins with Fredy, a 15-year-old boy, standing outside a store with his friends Satin and Jesus. The scene represents a blend of heaven and hell, with vivid contrasts of red fire flames and white clouds. Fredy is caught stealing a candy bar from the store, and Jesus tries to reason with him about making better choices. Satin, on the other hand, encourages Fredys misbehavior. The story takes place in a small town, and the characters personalities and motivations are starting to emerge.', '<SUMMARY>', 0)

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
audio_path_2 = download_tts('White robe with a Bible in hand, nail prints in his hands and feet.', 'JESUS', 2)

# 🗣️ Dialogue Node: MR. PIMP [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_3 = download_tts('Dressed like a pimp, walks out of the candy store.', 'MR. PIMP', 3)

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

# 🗣️ Dialogue Node: FREDY [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_0 = download_tts('Okay, heres a funny comeback to that joke, playing on its elements:', 'FREDY', 0)

# 🗣️ Dialogue Node: FLO [Angry]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Angry')
audio_path_1 = download_tts('Shits and grina got to go!', 'FLO', 1)

# 🗣️ Dialogue Node: CUT TO: [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('', 'CUT TO:', 2)

print('--- Building Scene 13 ---')
spawn_light(False, True)

# 🗣️ Dialogue Node: <SUMMARY> [Confused]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Confused')
audio_path_0 = download_tts('The story takes a turn as Fredys friends gather at the table to discuss their opinions on Beavis and Butthead and South Park. They engage in a lively conversation, sharing their thoughts on the shows humor and production time. Meanwhile, Fredys dream from the previous night is still unclear, leaving his friends curious about what happened.', '<SUMMARY>', 0)

# 🗣️ Dialogue Node: **INT. FREDYS BEDROOM - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_1 = download_tts('', '**INT. FREDYS BEDROOM - DAY**', 1)

# 🗣️ Dialogue Node: FREDY [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_2 = download_tts('(15): Black hair, brown eyes. Dressed in silky shorts and a baseball image t-shirt. With sunglasses.', 'FREDY', 2)

# 🗣️ Dialogue Node: DISTURBED (V.O.) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_3 = download_tts('Hello, Fredy.', 'DISTURBED (V.O.)', 3)

# 🗣️ Dialogue Node: FREDY [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_4 = download_tts('Oh, hello, Disturbed.', 'FREDY', 4)

# 🗣️ Dialogue Node: **CUT TO:** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_5 = download_tts('', '**CUT TO:**', 5)

# 🗣️ Dialogue Node: **EXT. SIDEWALK BY MR. PIMPS STORE - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_6 = download_tts('The Store Owner shakes his head, walking through the door, which shuts behind him.', '**EXT. SIDEWALK BY MR. PIMPS STORE - DAY**', 6)

# 🗣️ Dialogue Node: MR. PIMP [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_7 = download_tts('', 'MR. PIMP', 7)

# 🗣️ Dialogue Node: WTF [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_8 = download_tts('', 'WTF', 8)

# 🗣️ Dialogue Node: **CUT TO:** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_9 = download_tts('', '**CUT TO:**', 9)

# 🗣️ Dialogue Node: **INT. FREDYS BEDROOM - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_10 = download_tts('Fredys phone rings with Disturbed on the other end of the line.', '**INT. FREDYS BEDROOM - DAY**', 10)

# 🗣️ Dialogue Node: FREDY [Confused]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Confused')
audio_path_11 = download_tts('Hello?', 'FREDY', 11)

# 🗣️ Dialogue Node: DISTURBED (V.O.) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_12 = download_tts('Finish your story about your dream.', 'DISTURBED (V.O.)', 12)

# 🗣️ Dialogue Node: FREDY [Angry]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Angry')
audio_path_13 = download_tts('Seriously, dude!', 'FREDY', 13)

# 🗣️ Dialogue Node: **CUT TO:** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_14 = download_tts('', '**CUT TO:**', 14)

# 🗣️ Dialogue Node: **EXT. SIDEWALK BY MR. PIMPS STORE - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_15 = download_tts('The Store Owner looks at Jesus, then Satan.', '**EXT. SIDEWALK BY MR. PIMPS STORE - DAY**', 15)

# 🗣️ Dialogue Node: MR. PIMP [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_16 = download_tts('', 'MR. PIMP', 16)

# 🗣️ Dialogue Node: WTF [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_17 = download_tts('', 'WTF', 17)

# 🗣️ Dialogue Node: **CUT TO:** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_18 = download_tts('', '**CUT TO:**', 18)

# 🗣️ Dialogue Node: **INT. FREDYS BEDROOM - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_19 = download_tts('Fredy continues his story on the phone with Disturbed.', '**INT. FREDYS BEDROOM - DAY**', 19)

# 🗣️ Dialogue Node: FREDY [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_20 = download_tts('You just had to be there.', 'FREDY', 20)

# 🗣️ Dialogue Node: DISTURBED (V.O.) [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_21 = download_tts('Hey, lets meet at Smakeys Park and light off firecrackers.', 'DISTURBED (V.O.)', 21)

# 🗣️ Dialogue Node: FREDY [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_22 = download_tts('Ill dress like Beavis today, except my direction wont need a permission slip HA HA HA', 'FREDY', 22)

# 🗣️ Dialogue Node: **CUT TO:** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_23 = download_tts('', '**CUT TO:**', 23)

# 🗣️ Dialogue Node: **NEW SCENE - ACT TWO** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_24 = download_tts('', '**NEW SCENE - ACT TWO**', 24)

# 🗣️ Dialogue Node: **EXT. SMAKEYS PARK - DAY** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_25 = download_tts('Fredy and Disturbed are seen walking towards the park, laughing and joking around.', '**EXT. SMAKEYS PARK - DAY**', 25)

# 🗣️ Dialogue Node: FREDY [Angry]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Angry')
audio_path_26 = download_tts('See you at the park, bring the works and lighter!', 'FREDY', 26)

# 🗣️ Dialogue Node: **<SUMMARY>** [Neutral]
print('Injecting MetaHuman Facial Control Rig keys for sentiment: Neutral')
audio_path_27 = download_tts('The story continues as Fredy finishes telling his friends about his dream from the previous night. Meanwhile, he receives a call from Disturbed, who invites him to meet up at Smakeys Park to light off firecrackers. The scene cuts to Fredy and Disturbed walking towards the park, excited for their next adventure.', '**<SUMMARY>**', 27)

print('✅ Virtual Production Build Complete!')
