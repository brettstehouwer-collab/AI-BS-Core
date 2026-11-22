import unreal

import unreal

# Spawn a static mesh actor for the forest floor
forest_floor = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))
forest_floor.set_editor_property('static_mesh', unreal.EditorAssetLibrary.load_asset('/Game/Path/To/FloorMesh.FloorMesh'))
forest_floor.set_editor_property('label', 'ForestFloor')

# Spawn a static mesh actor for a tree
tree = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(100, 0, 50), unreal.Rotator(0, 90, 0))
tree.set_editor_property('static_mesh', unreal.EditorAssetLibrary.load_asset('/Game/Path/To/TreeMesh.TreeMesh'))
tree.set_editor_property('label', 'Tree')

# Save the current level
unreal.EditorLoadingAndSavingUtils.save_current_level()

import unreal

import unreal

# Spawn an actor at a specific location and rotation
actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
    unreal.StaticMeshActor,
    unreal.Vector(100.0, 200.0, 300.0),
    unreal.Rotator(0.0, 45.0, 90.0)
)

# Set the label of the actor
actor.set_editor_property('label', 'MyActor')

# Save the current level
unreal.EditorLoadingAndSavingUtils.save_current_level()

import unreal

import unreal

# Spawn a new actor at the origin
actor = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0, 0, 0), unreal.Rotator())

# Set the label of the actor
actor.set_editor_property('label', 'Cabin')

# Save the current level to persist changes
unreal.EditorLoadingAndSavingUtils.save_current_level()

