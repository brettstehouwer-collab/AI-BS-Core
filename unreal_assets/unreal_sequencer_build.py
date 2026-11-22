import unreal
# Auto-generated AI-BS Native Studio Unreal Engine 5.8 Virtual Production Sequencer Builder
# Execution Target: Unreal Engine Python API / Remote Control

asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
package_name = '/Game/Cinematics'
seq_asset = asset_tools.create_asset('Master_Screenplay_Seq', package_name, unreal.LevelSequence, unreal.LevelSequenceFactoryNew())

# Spawn Directional Light & Cinematic Atmosphere
sun = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 1000), unreal.Rotator(-45, 30, 0))
if sun: sun.set_actor_label('Sun_KeyLight')

# --- Scene 1: EXT. SUBURBAN NEIGHBORHOOD - DAY ---
cam_1 = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.CineCameraActor, unreal.Vector(0, -450, 160), unreal.Rotator(0, 15, 0))
if cam_1:
    cam_1.set_actor_label('CineCam_Scene_001')
    cam_comp = cam_1.get_cine_camera_component()
    cam_comp.current_focal_length = 35.0

# --- Scene 2: INT. SUBURBAN LIVING ROOM - DAY ---
cam_2 = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.CineCameraActor, unreal.Vector(600, -450, 160), unreal.Rotator(0, 15, 0))
if cam_2:
    cam_2.set_actor_label('CineCam_Scene_002')
    cam_comp = cam_2.get_cine_camera_component()
    cam_comp.current_focal_length = 50.0

# --- Scene 3: EXT. SUBURBAN STREET - DAY ---
cam_3 = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.CineCameraActor, unreal.Vector(1200, -450, 160), unreal.Rotator(0, 15, 0))
if cam_3:
    cam_3.set_actor_label('CineCam_Scene_003')
    cam_comp = cam_3.get_cine_camera_component()
    cam_comp.current_focal_length = 35.0

# --- Scene 4: INT. CAR - DAY ---
cam_4 = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.CineCameraActor, unreal.Vector(1800, -450, 160), unreal.Rotator(0, 15, 0))
if cam_4:
    cam_4.set_actor_label('CineCam_Scene_004')
    cam_comp = cam_4.get_cine_camera_component()
    cam_comp.current_focal_length = 50.0

# --- Scene 5: EXT. SUBURBAN STREET - CONTINUOUS ---
cam_5 = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.CineCameraActor, unreal.Vector(2400, -450, 160), unreal.Rotator(0, 15, 0))
if cam_5:
    cam_5.set_actor_label('CineCam_Scene_005')
    cam_comp = cam_5.get_cine_camera_component()
    cam_comp.current_focal_length = 35.0

# --- Scene 6: INT. CAR - DAY ---
cam_6 = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.CineCameraActor, unreal.Vector(3000, -450, 160), unreal.Rotator(0, 15, 0))
if cam_6:
    cam_6.set_actor_label('CineCam_Scene_006')
    cam_comp = cam_6.get_cine_camera_component()
    cam_comp.current_focal_length = 50.0

# --- Scene 7: EXT. DAD'S HOUSE - DAY ---
cam_7 = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.CineCameraActor, unreal.Vector(3600, -450, 160), unreal.Rotator(0, 15, 0))
if cam_7:
    cam_7.set_actor_label('CineCam_Scene_007')
    cam_comp = cam_7.get_cine_camera_component()
    cam_comp.current_focal_length = 35.0

# --- Scene 8: INT. DAD'S LIVING ROOM - DAY ---
cam_8 = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.CineCameraActor, unreal.Vector(4200, -450, 160), unreal.Rotator(0, 15, 0))
if cam_8:
    cam_8.set_actor_label('CineCam_Scene_008')
    cam_comp = cam_8.get_cine_camera_component()
    cam_comp.current_focal_length = 50.0

# --- Scene 9: EXT. DUPLEX NEXT DOOR - DAY ---
cam_9 = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.CineCameraActor, unreal.Vector(4800, -450, 160), unreal.Rotator(0, 15, 0))
if cam_9:
    cam_9.set_actor_label('CineCam_Scene_009')
    cam_comp = cam_9.get_cine_camera_component()
    cam_comp.current_focal_length = 35.0

# --- Scene 10: INT. DAD'S HOUSE - EVENING ---
cam_10 = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.CineCameraActor, unreal.Vector(5400, -450, 160), unreal.Rotator(0, 15, 0))
if cam_10:
    cam_10.set_actor_label('CineCam_Scene_010')
    cam_comp = cam_10.get_cine_camera_component()
    cam_comp.current_focal_length = 50.0

# --- Scene 11: EXT. SUBURBAN STREET - SUNSET ---
cam_11 = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.CineCameraActor, unreal.Vector(6000, -450, 160), unreal.Rotator(0, 15, 0))
if cam_11:
    cam_11.set_actor_label('CineCam_Scene_011')
    cam_comp = cam_11.get_cine_camera_component()
    cam_comp.current_focal_length = 35.0

# --- Scene 12: INT. JESSICA'S HOUSE - NIGHT ---
cam_12 = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.CineCameraActor, unreal.Vector(6600, -450, 160), unreal.Rotator(0, 15, 0))
if cam_12:
    cam_12.set_actor_label('CineCam_Scene_012')
    cam_comp = cam_12.get_cine_camera_component()
    cam_comp.current_focal_length = 50.0

# Save Level & Sequence
unreal.EditorLoadingAndSavingUtils.save_current_level()
print('✅ [AI-BS] Master Screenplay Sequencer and Virtual Production cameras initialized successfully.')