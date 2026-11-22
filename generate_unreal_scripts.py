import os

base_dir = r"C:\AI-BS\Unreal_Scripts"
if os.path.exists("E:\\"):
    base_dir = r"E:\AI_BS_Resources\Unreal_Scripts"

scripts_data = {
    "01_Level_Editor": {
        "spawn_actors.py": """import unreal

# Target: Scene assembly, actor placement, world composition.
# Python Directive: unreal.EditorLevelLibrary.get_selected_level_actors(), unreal.EditorLevelLibrary.spawn_actor_from_class()

def spawn_static_mesh(asset_path, location, rotation):
    actor_class = unreal.StaticMeshActor
    actor_location = unreal.Vector(location[0], location[1], location[2])
    actor_rotation = unreal.Rotator(rotation[0], rotation[1], rotation[2])
    
    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(actor_class, actor_location, actor_rotation)
    if actor:
        mesh_asset = unreal.EditorAssetLibrary.load_asset(asset_path)
        actor.static_mesh_component.set_static_mesh(mesh_asset)
        print(f"Spawned {actor.get_name()} at {location}")
    return actor

def get_selected():
    selected_actors = unreal.EditorLevelLibrary.get_selected_level_actors()
    for actor in selected_actors:
        print(actor.get_name())
    return selected_actors

if __name__ == '__main__':
    print("Level Editor Tools Loaded.")
"""
    },
    "02_Blueprint_Editor": {
        "create_blueprint.py": """import unreal

# Target: Node-based visual scripting, gameplay logic, object interactions.
# Python Directive: unreal.AssetToolsHelpers.get_asset_tools().create_asset(), unreal.BlueprintEditorLibrary

def create_blueprint_asset(asset_name, package_path):
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    factory = unreal.BlueprintFactory()
    factory.set_editor_property("ParentClass", unreal.Actor)
    
    new_asset = asset_tools.create_asset(asset_name, package_path, None, factory)
    if new_asset:
        print(f"Created Blueprint: {package_path}/{asset_name}")
    return new_asset

if __name__ == '__main__':
    print("Blueprint Editor Tools Loaded.")
"""
    },
    "03_Material_Editor": {
        "create_material.py": """import unreal

# Target: Shader authoring, surface properties, texture mapping.
# Python Directive: unreal.MaterialEditingLibrary.create_material_expression(), unreal.MaterialEditingLibrary.connect_material_property()

def create_base_material(asset_name, package_path):
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    factory = unreal.MaterialFactoryNew()
    
    material = asset_tools.create_asset(asset_name, package_path, None, factory)
    if material:
        # Create a base color vector parameter
        base_color_expr = unreal.MaterialEditingLibrary.create_material_expression(material, unreal.MaterialExpressionVectorParameter, -200, 0)
        base_color_expr.set_editor_property("parameter_name", "BaseColor")
        
        # Connect to BaseColor property
        unreal.MaterialEditingLibrary.connect_material_property(base_color_expr, "rgb", unreal.MaterialProperty.MP_BASE_COLOR)
        
        unreal.MaterialEditingLibrary.recompile_material(material)
        print(f"Created Material: {package_path}/{asset_name}")
    return material

if __name__ == '__main__':
    print("Material Editor Tools Loaded.")
"""
    },
    "04_Niagara_Editor": {
        "create_niagara_system.py": """import unreal

# Target: Particle systems, real-time visual effects, environmental simulations.
# Python Directive: unreal.NiagaraScript, unreal.AssetToolsHelpers.get_asset_tools()

def create_niagara_system(asset_name, package_path):
    # Note: Niagara asset creation via python requires specific factories depending on engine version.
    print(f"Preparing to create Niagara system at {package_path}/{asset_name}...")
    print("Use Niagara System Factory for instantiation.")

if __name__ == '__main__':
    print("Niagara Editor Tools Loaded.")
"""
    },
    "05_UMG_UI_Editor": {
        "create_widget.py": """import unreal

# Target: Head-up displays, menus, screen layouts.
# Python Directive: unreal.WidgetBlueprint, unreal.WidgetLayoutLibrary

def create_ui_widget(asset_name, package_path):
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    factory = unreal.WidgetBlueprintFactory()
    
    new_widget = asset_tools.create_asset(asset_name, package_path, None, factory)
    if new_widget:
        print(f"Created UMG Widget: {package_path}/{asset_name}")
    return new_widget

if __name__ == '__main__':
    print("UMG UI Editor Tools Loaded.")
"""
    },
    "06_Control_Rig": {
        "setup_control_rig.py": """import unreal

# Target: Skeletal retargeting, cinematic sequencing, inverse kinematics.
# Python Directive: unreal.ControlRigBlueprint, unreal.AnimSequence

def create_control_rig(asset_name, package_path):
    # Setup for Control Rig blueprint generation
    print(f"Initializing Control Rig at {package_path}/{asset_name}...")

if __name__ == '__main__':
    print("Control Rig Tools Loaded.")
"""
    },
    "07_Modeling_Mode": {
        "process_meshes.py": """import unreal

# Target: In-engine mesh creation, sculpting, UV unwrapping, boolean operations.
# Python Directive: unreal.MeshProcessingLibrary, unreal.ModelingToolsEditorLibrary

def optimize_mesh(static_mesh_asset):
    # Placeholder for mesh simplification logic using UE5 modeling tools API
    print(f"Optimizing mesh: {static_mesh_asset.get_name()}")

if __name__ == '__main__':
    print("Modeling Mode Tools Loaded.")
"""
    },
    "08_Behavior_Tree": {
        "setup_behavior_tree.py": """import unreal

# Target: Artificial intelligence decision-making hierarchies, NPC logic.
# Python Directive: unreal.BehaviorTree, unreal.BlackboardData

def create_ai_assets(base_name, package_path):
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    
    # Blackboard
    bb_factory = unreal.BlackboardDataFactory()
    bb_asset = asset_tools.create_asset(f"{base_name}_BB", package_path, None, bb_factory)
    
    # Behavior Tree
    bt_factory = unreal.BehaviorTreeFactory()
    bt_asset = asset_tools.create_asset(f"{base_name}_BT", package_path, None, bt_factory)
    
    if bt_asset and bb_asset:
        # bt_asset.blackboard_asset = bb_asset # Example linkage
        print(f"Created BT and Blackboard for {base_name}")

if __name__ == '__main__':
    print("Behavior Tree Tools Loaded.")
"""
    },
    "09_Physics_Asset": {
        "setup_physics.py": """import unreal

# Target: Ragdoll mechanics, rigid body dynamics, cloth simulation, destruction.
# Python Directive: unreal.PhysicsAsset, unreal.ChaosSolverActor

def get_physics_actors():
    actors = unreal.EditorLevelLibrary.get_all_level_actors()
    physics_actors = [a for a in actors if isinstance(a, unreal.ChaosSolverActor)]
    for pa in physics_actors:
        print(f"Found Chaos Solver: {pa.get_name()}")
    return physics_actors

if __name__ == '__main__':
    print("Physics Asset Tools Loaded.")
"""
    },
    "10_Audio_MetaSounds": {
        "create_metasound.py": """import unreal

# Target: Procedural sound design, node-based audio generation.
# Python Directive: unreal.MetaSoundBuilderSubsystem, unreal.SoundWave

def build_metasound():
    builder_subsystem = unreal.get_engine_subsystem(unreal.MetaSoundBuilderSubsystem)
    # builder = builder_subsystem.create_meta_sound_source_builder()
    print("MetaSound builder subsystem accessed.")

if __name__ == '__main__':
    print("Audio MetaSounds Tools Loaded.")
"""
    }
}

for folder, files in scripts_data.items():
    folder_path = os.path.join(base_dir, folder)
    os.makedirs(folder_path, exist_ok=True)
    for filename, code in files.items():
        file_path = os.path.join(folder_path, filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(code)

print(f"Generated 10 Unreal Python Tool categories in {base_dir}")
