import bpy,json
from pathlib import Path
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
source='D:/AI-BS-Game-Resources/Character_Sources/human_base_meshes_bundle.blend'
with bpy.data.libraries.load(source,link=False) as (s,d):d.objects=[n for n in s.objects if n.startswith('GEO-head_animation_realistic')]
for o in d.objects:
 if o:bpy.context.collection.objects.link(o)
bpy.context.view_layer.update()
origin=next(o.matrix_world.translation.copy() for o in d.objects if o.name=='GEO-head_animation_realistic')
records=[]
for o in d.objects:
 if o and o.type=='MESH':
  records.append((o.name,[tuple(o.matrix_world@v.co-origin) for v in o.data.vertices],[tuple(f.vertices) for f in o.data.polygons]))
bpy.ops.wm.read_factory_settings(use_empty=True)
for name,vertices,faces in records:
 data=bpy.data.meshes.new(name);data.from_pydata(vertices,[],faces);data.update();obj=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(obj)
 for face in data.polygons:face.use_smooth=True
assert not bpy.data.libraries
p=Path('C:/AI-BS/engine/assets/workshop/adam/adam-naturalistic-base.blend');bpy.ops.wm.save_as_mainfile(filepath=str(p))
r={'status':'anatomical_base_prepared','likeness_approved':False,'style':'Naturalistic face and clothing with subtle hologram glow','source_bundle':'human-base-meshes-bundle-v1.2.0.zip','source_sha256':'b7421350cbad8425dd1ba93c4248867a1c236cc8a3a3dc140d4c2a03144c4bad','source_url':'https://download.blender.org/demo/asset-bundles/human-base-meshes/human-base-meshes-bundle-v1.2.0.zip','license_source':'https://www.blender.org/download/demo-files/','source_license':'CC0 Blender Human Base Meshes bundle','objects':[{'name':o.name,'vertices':len(o.data.vertices)} for o in bpy.context.scene.objects if o.type=='MESH'],'next':'Fit head proportions and facial landmarks to supplied podium/front references, connected clothed body and skinning, then close-up/full-body and deformation previews','original_family_references_embedded':False}
Path('C:/AI-BS/engine/assets/workshop/adam/naturalistic-provenance.json').write_text(json.dumps(r,indent=2)+'\n')
