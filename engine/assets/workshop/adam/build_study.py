import bpy, math, json, hashlib
from pathlib import Path
from mathutils import Vector
ROOT=Path('C:/AI-BS');OUT=ROOT/'engine/out/warm_beginning/adam-study';MASTER=ROOT/'engine/assets/workshop/adam'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
parts=[]
def mat(name,c):
 m=bpy.data.materials.new(name);m.diffuse_color=(*c,1);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*c,1);p.inputs['Metallic'].default_value=0;p.inputs['Roughness'].default_value=1;return m
skin=mat('Skin study',(.64,.39,.29));hair=mat('Short dark hair',(.024,.018,.014));cream=mat('Cream overshirt',(.65,.59,.45));teal=mat('Teal undershirt',(.015,.25,.20));pants=mat('Provisional dark trousers',(.035,.05,.065));shoe=mat('Provisional shoes',(.028,.025,.022));ink=mat('Abstract fabric marks',(.18,.16,.12));white=mat('Eye ivory',(.74,.73,.65));iris=mat('Eye detail',(.065,.037,.018));lip=mat('Mouth study',(.28,.105,.075));beard=mat('Light beard study',(.15,.10,.073))
def shape(name,loc,scale,material,bone,box=False):
 if box:bpy.ops.mesh.primitive_cube_add(size=2,location=loc)
 else:bpy.ops.mesh.primitive_uv_sphere_add(segments=20,ring_count=12,location=loc)
 o=bpy.context.object;o.name=name;o.scale=scale;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(material)
 for p in o.data.polygons:p.use_smooth=not box
 g=o.vertex_groups.new(name=bone);g.add(list(range(len(o.data.vertices))),1,'REPLACE');parts.append(o);return o
shape('Torso teal', (0,0,1.19),(.245,.12,.255),teal,'chest')
for sign in (-1,1):
 shape('Open overshirt panel',(sign*.15,-.055,1.20),(.115,.09,.25),cream,'chest',True)
 for k in range(6):shape('Abstract print bar',(sign*.15,-.148,1.03+k*.065),(.07,.002,.006),ink,'chest',True)
 shape('Collar',(sign*.085,-.14,1.415),(.063,.024,.052),cream,'chest',True)
 side='L' if sign>0 else 'R'
 shape('Overshirt sleeve',(sign*.295,0,1.24),(.095,.10,.19),cream,'upper_'+side)
 shape('Sleeve forearm',(sign*.375,0,1.015),(.069,.078,.16),cream,'fore_'+side)
 shape('Hand',(sign*.40,-.012,.835),(.061,.045,.095),skin,'hand_'+side)
 shape('Trouser upper',(sign*.115,0,.735),(.103,.11,.235),pants,'thigh_'+side)
 shape('Trouser lower',(sign*.115,0,.32),(.082,.088,.22),pants,'shin_'+side)
 shape('Shoe',(sign*.115,-.065,.065),(.09,.16,.065),shoe,'foot_'+side)
shape('Hip',(0,0,.92),(.23,.12,.11),pants,'hips')
shape('Neck',(0,0,1.465),(.065,.062,.09),skin,'neck')
shape('Head volume',(0,-.006,1.615),(.108,.096,.139),skin,'head')
shape('Jaw volume',(0,-.015,1.535),(.088,.083,.063),skin,'head')
shape('Hair cap',(0,.005,1.714),(.11,.095,.064),hair,'head')
shape('Hair back',(0,.053,1.661),(.105,.058,.10),hair,'head')
for sign in (-1,1):
 shape('Ear',(sign*.108,0,1.616),(.019,.022,.037),skin,'head')
 shape('Eye',(sign*.041,-.094,1.649),(.027,.010,.012),white,'head')
 shape('Iris',(sign*.041,-.104,1.649),(.010,.003,.010),iris,'head')
 shape('Brow',(sign*.041,-.096,1.671),(.032,.008,.007),hair,'head')
 shape('Beard side',(sign*.076,-.051,1.548),(.016,.022,.045),beard,'head')
shape('Nose bridge',(0,-.098,1.621),(.017,.020,.032),skin,'head')
shape('Nose tip',(0,-.119,1.600),(.025,.018,.018),skin,'head')
shape('Mouth',(0,-.097,1.567),(.040,.006,.009),lip,'head')
shape('Lower lip',(0,-.100,1.559),(.031,.005,.006),skin,'head')
shape('Chin beard',(0,-.070,1.514),(.046,.012,.018),beard,'head')
bpy.ops.object.select_all(action='DESELECT')
for o in parts:o.select_set(True)
bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();mesh=bpy.context.object;mesh.name='Adam_study_v01';bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
bpy.ops.object.armature_add();rig=bpy.context.object;rig.name='Adam_study_rig';bpy.ops.object.mode_set(mode='EDIT');rig.data.edit_bones.remove(rig.data.edit_bones[0])
spec=[('root',(0,0,0),(0,0,.15),None),('hips',(0,0,.90),(0,0,1.02),'root'),('chest',(0,0,1.02),(0,0,1.41),'hips'),('neck',(0,0,1.41),(0,0,1.49),'chest'),('head',(0,0,1.49),(0,0,1.75),'neck')]
for sign,side in [(1,'L'),(-1,'R')]:
 spec += [('upper_'+side,(sign*.23,0,1.37),(sign*.35,0,1.10),'chest'),('fore_'+side,(sign*.35,0,1.10),(sign*.40,0,.90),'upper_'+side),('hand_'+side,(sign*.40,0,.90),(sign*.40,0,.79),'fore_'+side),('thigh_'+side,(sign*.115,0,.92),(sign*.115,0,.52),'hips'),('shin_'+side,(sign*.115,0,.52),(sign*.115,0,.12),'thigh_'+side),('foot_'+side,(sign*.115,0,.12),(sign*.115,-.16,.06),'shin_'+side)]
for n,h,t,parent in spec:
 b=rig.data.edit_bones.new(n);b.head=h;b.tail=t
 if parent:b.parent=rig.data.edit_bones[parent]
bpy.ops.object.mode_set(mode='OBJECT');modifier=mesh.modifiers.new('Skin','ARMATURE');modifier.object=rig;mesh.parent=rig
rig.animation_data_create()
for name,amp in [('idle',.025),('walk',.35),('catchup',.55),('guidance',.14)]:
 action=bpy.data.actions.new(name);action.use_fake_user=True;rig.animation_data.action=action
 for f in range(1,32):
  phase=(f-1)/30*2*math.pi
  for b in rig.pose.bones:
   b.rotation_mode='XYZ';b.rotation_euler=(0,0,0)
   if b.name.startswith(('thigh','upper')):
    side=1 if b.name.endswith('L') else -1;b.rotation_euler.x=math.sin(phase)*amp*side*(-1 if b.name.startswith('upper') else 1)
   if name=='guidance' and b.name=='fore_L':b.rotation_euler.x=math.sin((f-1)/30*math.pi)*.4
   b.keyframe_insert('rotation_euler',frame=f,group=b.name)
 rig.animation_data.action=None
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24;scene.render.resolution_percentage=100;scene.world.color=(.15,.15,.15)
def aim(o,p):o.rotation_euler=(Vector(p)-o.location).to_track_quat('-Z','Y').to_euler()
for loc,power,size in [((2,-3,4),400,3),((-2,-1,2),200,2),((0,2,3),500,2)]:
 bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.data.energy=power;o.data.shape='DISK';o.data.size=size;aim(o,(0,0,1.1))
bpy.ops.object.camera_add(location=(2,-4,2));camera=bpy.context.object;scene.camera=camera;camera.data.type='ORTHO';camera.data.ortho_scale=2.1;aim(camera,(0,0,.93));scene.render.resolution_x=700;scene.render.resolution_y=900
bpy.ops.wm.save_as_mainfile(filepath=str(MASTER/'adam-study-v01.blend'))
scene.render.filepath=str(OUT/'full-body.png');bpy.ops.render.render(write_still=True)
camera.location=(.38,-1.5,1.70);camera.data.ortho_scale=.43;aim(camera,(0,-.015,1.635));scene.render.resolution_x=900;scene.render.resolution_y=900;scene.render.filepath=str(OUT/'face.png');bpy.ops.render.render(write_still=True)
(OUT/'study.json').write_text(json.dumps({'status':'prototype','recognizable_likeness_approved':False,'bones':len(rig.data.bones),'vertices':len(mesh.data.vertices),'actions':[a.name for a in bpy.data.actions],'references':['20151016_120823.jpg','AdamMainPic.jpg'],'reference_images_embedded':False,'provisional_choices':['1.8m reference height','dark trousers and shoes; podium view obscures lower clothing','simplified facial volumes and fabric print'],'master':str(MASTER/'adam-study-v01.blend')},indent=2))

