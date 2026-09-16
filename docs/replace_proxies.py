"""
===============================================================================
AI-BS ASSET REPLACEMENT SCRIPT
Run this script inside Unreal Engine 5.8 Python Console:
  exec(open("C:/AI-BS/replace_proxies.py").read())
===============================================================================
"""

import unreal

# ==============================================================================
# 1. FILL IN YOUR ASSET PATHS HERE
# ==============================================================================
# How to get the path:
# 1. Right-click your MetaHuman Blueprint or Static Mesh in the Content Browser.
# 2. Click "Copy Reference".
# 3. Paste it below inside the quotes. 
# NOTE FOR METAHUMANS: You MUST add "_C" to the very end of the path for it to load as a class!

METAHUMAN_MAPPINGS = {
    # Example: "CharProxy_John_Galveston": "/Game/MetaHumans/John/BP_John.BP_John_C",
    "CharProxy_Kirt_Stehouwer": "",
    "CharProxy_Julie_Stehouwer": "",
    "CharProxy_Sophie_Stehouwer": "",
    "CharProxy_Emma_Stehouwer": "",
    "CharProxy_Amelia_Stehouwer": "",
    "CharProxy_Kyle_Stehouwer": "",
    "CharProxy_John_Galveston": "",
    "CharProxy_Principal_Gabrielle": "",
    "CharProxy_Mr_Steve": "",
    "CharProxy_Jayden_Miller": "",
    "CharProxy_Officer_Malcolm": ""
}

STATIC_MESH_MAPPINGS = {
    # Example: "Proxy_PoolHouse_Sofa": "/Game/Megascans/3D_Assets/Sofa/SM_Sofa.SM_Sofa",
    "Proxy_Porch_Steps": "",
    "Proxy_PoolHouse_Sofa": "",
    "Proxy_Julie_Mansion_Structure": "",
    "Proxy_Swan_Water_Fountain": "",
    "Proxy_Gold_SUV": "",
    "Proxy_Porsche_Convertible": "",
    "Proxy_Mini_Rolls_Royce_Kid": "",
    "Proxy_Tennis_Court": "",
    "Proxy_Luxury_Swimming_Pool": "",
    "Proxy_Sophie_Bed": "",
    "Proxy_Emma_Bed": "",
    "Proxy_Amelia_Bed": "",
    "Proxy_Toy_RC_Car": "",
    "Proxy_Sophie_Notebook": "",
    "Proxy_Wall_TV_Screen": ""
}

def main():
    print("🔄 Starting Asset Replacement Script...")
    
    editor_level_lib = unreal.EditorLevelLibrary
    all_actors = editor_level_lib.get_all_level_actors()
    
    replacements_made = 0

    for actor in all_actors:
        actor_label = actor.get_actor_label()
        
        # ---------------------------------------------------------
        # METAHUMAN REPLACEMENT
        # ---------------------------------------------------------
        if actor_label in METAHUMAN_MAPPINGS:
            bp_path = METAHUMAN_MAPPINGS[actor_label]
            if not bp_path or bp_path == "":
                continue # User hasn't filled this one out yet
                
            # Clean up the "Blueprint'" wrapper if the user accidentally pasted it
            bp_path = bp_path.replace("Blueprint'", "").replace("'", "")
            if not bp_path.endswith("_C"):
                bp_path += "_C"
                
            bp_class = unreal.EditorAssetLibrary.load_blueprint_class(bp_path)
            if bp_class:
                transform = actor.get_actor_transform()
                new_mh = editor_level_lib.spawn_actor_from_class(bp_class, transform.translation, transform.rotation.rotator())
                
                if new_mh:
                    new_mh.set_actor_label(actor_label.replace("CharProxy_", ""))
                    new_mh.set_folder_path("JuliesPlace/Characters")
                    actor.destroy_actor() # Delete the proxy point
                    print(f"✅ Replaced {actor_label} with MetaHuman!")
                    replacements_made += 1
            else:
                print(f"⚠️ Error: Could not load MetaHuman at path: {bp_path}")

        # ---------------------------------------------------------
        # STATIC MESH REPLACEMENT
        # ---------------------------------------------------------
        elif actor_label in STATIC_MESH_MAPPINGS:
            mesh_path = STATIC_MESH_MAPPINGS[actor_label]
            if not mesh_path or mesh_path == "":
                continue
                
            mesh_path = mesh_path.replace("StaticMesh'", "").replace("'", "")
            mesh_asset = unreal.EditorAssetLibrary.load_asset(mesh_path)
            
            if mesh_asset and type(mesh_asset) == unreal.StaticMesh:
                if actor.get_class() == unreal.StaticMeshActor.static_class():
                    actor.static_mesh_component.set_static_mesh(mesh_asset)
                    actor.set_actor_label(actor_label.replace("Proxy_", ""))
                    print(f"✅ Swapped mesh for {actor_label}")
                    replacements_made += 1
            else:
                 print(f"⚠️ Error: Could not load StaticMesh at path: {mesh_path}")

    print(f"\n=======================================================")
    print(f"🎉 SUCCESS! Replaced {replacements_made} assets.")
    print(f"=======================================================\n")

if __name__ == "__main__":
    main()
