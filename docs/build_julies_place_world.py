"""
===============================================================================
AI-BS UNREAL ENGINE WORLD & ANIMATION GENERATOR SCRIPT
Project: "Julie's Place" (S1E1 Pilot & S1E2 The Writing's On The Wall)
===============================================================================
Run this script inside Unreal Engine 5.8 Python Console:
  exec(open("C:/AI-BS/build_julies_place_world.py").read())
===============================================================================
"""

import unreal
import os
import urllib.request
import urllib.parse

def main():
    print("🚀 Starting AI-BS World Generation for 'Julie's Place' (S1E1 & S1E2)...")

    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    root_path = "/Game/JuliesPlace"
    cinematics_path = f"{root_path}/Cinematics"
    environments_path = f"{root_path}/Environments"

    for path in [root_path, cinematics_path, environments_path]:
        if not unreal.EditorAssetLibrary.does_directory_exist(path):
            unreal.EditorAssetLibrary.make_directory(path)

    # Create Master Level Sequence
    sequence_name = "JuliesPlace_S1E1_MasterSequence"
    sequence_full_path = f"{cinematics_path}/{sequence_name}"

    if unreal.EditorAssetLibrary.does_asset_exist(sequence_full_path):
        unreal.EditorAssetLibrary.delete_asset(sequence_full_path)

    level_sequence = asset_tools.create_asset(sequence_name, cinematics_path, unreal.LevelSequence, unreal.LevelSequenceFactoryNew())
    print(f"🎬 Created Master Level Sequence: {sequence_name}")

    def spawn_lighting(is_morning=True, is_exterior=True):
        if is_exterior:
            light = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 1500))
            if light:
                light.set_actor_label("Sun_DirectionalLight")
                try:
                    light.directional_light_component.set_editor_property("intensity", 120000.0)
                    light.directional_light_component.set_editor_property("light_color", unreal.LinearColor(1.0, 0.9, 0.8, 1.0))
                except Exception as e:
                    print(f"Lighting prop warn: {e}")
                light.set_actor_rotation(unreal.Rotator(-35.0, 45.0, 0.0), False)
                light.set_folder_path("JuliesPlace/Lighting")
            
            sky = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 1600))
            if sky:
                sky.set_actor_label("Sky_Light")
                try:
                    sky.sky_light_component.set_editor_property("intensity", 2.0)
                except Exception as e:
                    print(f"Sky prop warn: {e}")
                sky.set_folder_path("JuliesPlace/Lighting")
        else:
            light = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.PointLight, unreal.Vector(0, 0, 400))
            if light:
                light.set_actor_label("Interior_Warm_PointLight")
                try:
                    light.point_light_component.set_editor_property("intensity", 8000.0)
                    light.point_light_component.set_editor_property("light_color", unreal.LinearColor(1.0, 0.95, 0.9, 1.0))
                except Exception as e:
                    print(f"PointLight prop warn: {e}")
                light.set_folder_path("JuliesPlace/Lighting")

    def spawn_camera(name, location, rotation=unreal.Rotator(0, 0, 0)):
        camera = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.CineCameraActor, location)
        if camera:
            camera.set_actor_label(name)
            camera.set_actor_rotation(rotation, False)
            camera.set_folder_path("JuliesPlace/Cameras")
            print(f"🎥 Camera Created: {name}")
        return camera

    def spawn_prop(mesh_path, location, scale=unreal.Vector(1, 1, 1), name="Prop"):
        obj = unreal.EditorAssetLibrary.load_asset(mesh_path)
        if obj:
            actor = unreal.EditorLevelLibrary.spawn_actor_from_object(obj, location)
            if actor:
                actor.set_actor_label(name)
                actor.set_actor_scale3d(scale)
                actor.set_folder_path("JuliesPlace/Props")
                print(f"📦 Spawned Prop: {name}")
                return actor
        else:
            actor = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.StaticMeshActor, location)
            if actor:
                actor.set_actor_label(f"Proxy_{name}")
                actor.set_actor_scale3d(scale)
                actor.set_folder_path("JuliesPlace/Props")
                print(f"📦 Spawned Proxy Prop: {name}")
                return actor

    def spawn_character_proxy(name, location, rotation=unreal.Rotator(0, 0, 0)):
        actor = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.TargetPoint, location)
        if actor:
            actor.set_actor_label(f"CharProxy_{name}")
            actor.set_actor_rotation(rotation, False)
            actor.set_folder_path("JuliesPlace/Characters")
            print(f"👤 Anchor: {name}")
        return actor

    def download_and_bind_tts(character, line_text, line_index):
        try:
            safe_text = urllib.parse.quote(line_text)
            safe_char = urllib.parse.quote(character)
            url = f"http://127.0.0.1:8080/api/screenwriting/tts?text={safe_text}&character={safe_char}"
            save_dir = os.path.join(unreal.SystemLibrary.get_project_directory(), "Content", "JuliesPlace_Audio")
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
            file_path = os.path.join(save_dir, f"S1E1_{character}_{line_index}.wav")
            urllib.request.urlretrieve(url, file_path)
            print(f"🎙️ Audio Generated [{character}]")
            return file_path
        except Exception:
            return None

    # SCENE 1
    spawn_lighting(is_morning=True, is_exterior=True)
    spawn_camera("Cam_S01_Mansion_Wide", unreal.Vector(-1500, 0, 300), unreal.Rotator(-10, 0, 0))
    spawn_prop("/Engine/BasicShapes/Cube", unreal.Vector(0, 0, 250), unreal.Vector(15, 20, 8), "Julie_Mansion_Structure")
    spawn_prop("/Engine/BasicShapes/Cylinder", unreal.Vector(-600, -300, 40), unreal.Vector(3, 3, 1), "Swan_Water_Fountain")
    spawn_prop("/Engine/BasicShapes/Cube", unreal.Vector(-800, 200, 50), unreal.Vector(4, 2, 1.5), "Gold_SUV")
    spawn_prop("/Engine/BasicShapes/Cube", unreal.Vector(-800, 400, 40), unreal.Vector(3.5, 1.8, 1.2), "Porsche_Convertible")
    
    # SCENE 2
    spawn_camera("Cam_S02_Backyard_Tennis_Pool", unreal.Vector(800, -1000, 200), unreal.Rotator(-5, 45, 0))
    spawn_prop("/Engine/BasicShapes/Cube", unreal.Vector(1200, -800, 5), unreal.Vector(12, 8, 0.1), "Tennis_Court")
    spawn_prop("/Engine/BasicShapes/Cube", unreal.Vector(800, -400, 0), unreal.Vector(8, 5, 0.2), "Luxury_Swimming_Pool")

    # SCENE 3
    spawn_lighting(is_morning=True, is_exterior=False)
    spawn_camera("Cam_S03_Triplets_Bedroom_Medium", unreal.Vector(200, 200, 120), unreal.Rotator(0, -135, 0))
    spawn_prop("/Engine/BasicShapes/Cube", unreal.Vector(0, 0, 30), unreal.Vector(2, 1.2, 0.6), "Sophie_Bed")
    spawn_prop("/Engine/BasicShapes/Cube", unreal.Vector(0, 150, 30), unreal.Vector(2, 1.2, 0.6), "Emma_Bed")
    spawn_prop("/Engine/BasicShapes/Cube", unreal.Vector(0, 300, 30), unreal.Vector(2, 1.2, 0.6), "Amelia_Bed")
    spawn_character_proxy("Kirt_Stehouwer", unreal.Vector(80, 0, 0))
    spawn_character_proxy("Sophie_Stehouwer", unreal.Vector(0, 0, 35))
    spawn_character_proxy("Emma_Stehouwer", unreal.Vector(0, 150, 35))
    spawn_character_proxy("Amelia_Stehouwer", unreal.Vector(0, 300, 35))

    download_and_bind_tts("KIRT", "Sophie, sweetheart, time for school.", 1)

    # SCENE 4
    spawn_camera("Cam_S04_Porch_Close", unreal.Vector(-300, 100, 80), unreal.Rotator(0, 30, 0))
    spawn_prop("/Engine/BasicShapes/Cube", unreal.Vector(-200, 100, 20), unreal.Vector(2, 3, 0.4), "Porch_Steps")
    spawn_character_proxy("Julie_Stehouwer", unreal.Vector(-200, 100, 40))

    # SCENE 5
    spawn_camera("Cam_S05_PoolHouse_Wide", unreal.Vector(600, -200, 100), unreal.Rotator(0, -90, 0))
    spawn_character_proxy("Kyle_Stehouwer", unreal.Vector(600, -250, 0))
    spawn_character_proxy("John_Galveston", unreal.Vector(600, -200, 0))

    # SCENE 6
    spawn_camera("Cam_S06_Principal_Office", unreal.Vector(2000, 0, 100), unreal.Rotator(0, 180, 0))
    spawn_camera("Cam_S07_Gym_Class", unreal.Vector(3000, 0, 150), unreal.Rotator(-15, 0, 0))
    spawn_character_proxy("Principal_Gabrielle", unreal.Vector(2000, -50, 0))
    spawn_character_proxy("Mr_Steve", unreal.Vector(3000, 0, 0))
    spawn_character_proxy("Jayden_Miller", unreal.Vector(2500, 0, 0))
    spawn_character_proxy("Officer_Malcolm", unreal.Vector(2800, 0, 0))

    # SCENE 7
    spawn_camera("Cam_S08_TV_BreakingNews", unreal.Vector(0, -600, 120), unreal.Rotator(0, 0, 0))
    spawn_prop("/Engine/BasicShapes/Cube", unreal.Vector(100, -600, 150), unreal.Vector(0.1, 4, 2.5), "Wall_TV_Screen")

    print("\n===============================================================================")
    print("🎉 SUCCESS! Julie's Place World Built.")
    print("===============================================================================")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        print(f"\n❌ AI-BS SCRIPT CRASHED:\n{e}\n")
        traceback.print_exc()

