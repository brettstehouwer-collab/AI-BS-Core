import bpy,math,json
from pathlib import Path
from mathutils import Vector
root=Path('C:/AI-BS');out=root/'engine/out/warm_beginning/adam-naturalistic';out.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(root/'engine/assets/workshop/adam/adam-naturalistic-base.blend'))
assert not bpy.data.libraries
head=bpy.data.objects['GEO-head_animation_realistic']
eyes=[o for o in bpy.context.scene.objects if 'sclera' in o.name]
centers=[sum((v.co for v in o.data.vertices),Vector())/len(o.data.vertices) for o in eyes]
assert abs(centers[0].x-centers[1].x)>.05 and all(.20<c.z<.35 for c in centers)
def mat(n,c):
 m=bpy.data.materials.new(n);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*c,1);p.inputs['Roughness'].default_value=1;return m
skin=mat('Skin base - awaiting surface paint',(.53,.32,.24));white=mat('Sclera',(.65,.64,.59));iris=mat('Iris',(.08,.036,.016))
for o in list(bpy.context.scene.objects):
 m=iris if 'iris' in o.name else white if 'sclera' in o.name else skin;o.data.materials.clear();o.data.materials.append(m)
 # Smooth broad jaw/cheek edits in object coordinates, keeping both eye sets aligned.
 for v in o.data.vertices:
  x,y,z=v.co;lower=math.exp(-((z-.19)/.075)**2)
  v.co.x=x*(1+.10*lower);v.co.z=z*.97
  if 'iris' in o.name:v.co.y-=.008
 if o==head:
  mod=o.modifiers.new('Sculpt preview subdivision','SUBSURF');mod.levels=1;mod.render_levels=2
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=32;scene.world=bpy.data.worlds.new('Portrait world');scene.world.color=(.10,.10,.10)
def aim(o,p):o.rotation_euler=(Vector(p)-o.location).to_track_quat('-Z','Y').to_euler()
for loc,power,size in [((.4,-.7,.9),45,.6),((-.5,-.4,.5),20,.5),((.1,.4,.8),40,.5)]:
 bpy.ops.object.light_add(type='AREA',location=loc);light=bpy.context.object;light.data.energy=power;light.data.size=size;aim(light,(0,0,.24))
bpy.ops.object.camera_add(location=(0,-1.2,.27));cam=bpy.context.object;scene.camera=cam;cam.data.type='ORTHO';cam.data.ortho_scale=.49;aim(cam,(0,-.025,.24));scene.render.resolution_x=900;scene.render.resolution_y=900;scene.render.resolution_percentage=100
bpy.ops.wm.save_as_mainfile(filepath=str(root/'engine/assets/workshop/adam/adam-naturalistic-fit-v01.blend'))
scene.render.filepath=str(out/'front.png');bpy.ops.render.render(write_still=True)
cam.location=(.65,-1.0,.30);aim(cam,(0,-.025,.24));scene.render.filepath=str(out/'three-quarter.png');bpy.ops.render.render(write_still=True)
(out/'verification.json').write_text(json.dumps({'status':'fit_study','likeness_approved':False,'eye_separation':abs(centers[0].x-centers[1].x),'original_reference_images_embedded':False,'libraries':0,'next':'Hair/brows/lips and reference landmark refinement, then natural clothing and body/rig'},indent=2))

