import bpy
import math
from mathutils import Vector
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
body=bpy.data.materials.new('capacitor_body');body.diffuse_color=(0.025,0.10,0.15,1)
metal=bpy.data.materials.new('metal_contacts');metal.diffuse_color=(0.65,0.7,0.72,1)
parts=[]
for name,radius,depth,location,material in (
 ('Capacitor shell',.30,.85,(0,0,.70),body),
 ('Top cap',.29,.035,(0,0,1.145),metal),
 ('Base collar',.32,.06,(0,0,.28),body),
 ('Positive lead',.025,.30,(-.12,0,.12),metal),
 ('Negative lead',.025,.30,(.12,0,.12),metal)):
 bpy.ops.mesh.primitive_cylinder_add(vertices=48,radius=radius,depth=depth,location=location)
 obj=bpy.context.object;obj.name=name;obj.data.materials.append(material);parts.append(obj)
bpy.ops.object.select_all(action='DESELECT')
for obj in parts:obj.select_set(True)
bpy.context.view_layer.objects.active=parts[0]
bpy.ops.wm.obj_export(filepath='D:/AI-BS-Game-Resources/workshop/capacitor/capacitor.obj',export_selected_objects=True,export_triangulated_mesh=True,export_materials=True,forward_axis='NEGATIVE_Z',up_axis='Y')
bpy.ops.object.camera_add(location=(2.4,-3.2,2.1))
camera=bpy.context.object;camera.rotation_euler=(Vector((0,0,.6))-camera.location).to_track_quat('-Z','Y').to_euler();bpy.context.scene.camera=camera
scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL'
scene.render.resolution_x=640;scene.render.resolution_y=640;scene.render.resolution_percentage=100
scene.render.filepath='D:/AI-BS-Game-Resources/workshop/capacitor/preview.png'
bpy.ops.wm.save_as_mainfile(filepath='D:/AI-BS-Game-Resources/workshop/capacitor/capacitor.blend')
bpy.ops.render.render(write_still=True)
print('AI-BS original capacitor exported and saved')
