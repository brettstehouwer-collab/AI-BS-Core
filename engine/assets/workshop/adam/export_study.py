import bpy,json
from pathlib import Path
root=Path('C:/AI-BS');bpy.ops.wm.open_mainfile(filepath=str(root/'engine/assets/workshop/adam/adam-study-v01.blend'))
bpy.ops.object.select_all(action='DESELECT')
for n in ('Adam_study_v01','Adam_study_rig'):bpy.data.objects[n].select_set(True)
bpy.context.view_layer.objects.active=bpy.data.objects['Adam_study_rig']
bpy.ops.export_scene.gltf(filepath=str(root/'engine/out/warm_beginning/adam-study/adam-study-v01.glb'),export_format='GLB',use_selection=True,export_animation_mode='ACTIONS',export_force_sampling=True,export_optimize_animation_size=False,export_frame_range=False,export_materials='EXPORT')

