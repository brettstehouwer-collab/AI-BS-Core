import bpy, math, json, random, hashlib
from pathlib import Path
from mathutils import Vector
OUT=Path(__file__).resolve().parent
SOURCE=Path('C:/AI-BS/engine/assets/workshop/adam/adam-naturalistic-fit-v01.blend')
bpy.ops.wm.open_mainfile(filepath=str(SOURCE));assert not bpy.data.libraries
head=bpy.data.objects['GEO-head_animation_realistic']
# Reference-driven but provisional adjustments; not a recovered facial scan.
for v in head.data.vertices:
 x,y,z=v.co;front=max(0,min(1,(-y-.015)/.065))
 cheek=math.exp(-((z-.245)/.052)**2);jaw=math.exp(-((z-.175)/.035)**2)
 v.co.x=x*(1+front*(.10*cheek+.075*jaw))
 v.co.y=y-front*.007*cheek*min(1,abs(x)/.04)
 # A small, neutral-to-warm mouth corner lift; no speech or inferred performance.
 mouth=math.exp(-((abs(x)-.035)/.015)**2-((z-.200)/.025)**2)
 v.co.z=z+.003*front*mouth
head.data.update()
# Dense anatomical surface supports smooth scalp geometry rather than a cap primitive.
for mod in list(head.modifiers):head.modifiers.remove(mod)
sub=head.modifiers.new('Anatomical surface','SUBSURF');sub.levels=2;sub.render_levels=2
bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get();evaluated=head.evaluated_get(deps);surface=evaluated.to_mesh()
verts=[v.co.copy() for v in surface.vertices];normals=[v.normal.copy() for v in surface.vertices]
def threshold(p):
 # Short frontal fringe, temple recession and lower hair at the back.
 front=max(0,min(1,(-p.y+.01)/.10))
 side=max(0,min(1,(abs(p.x)-.075)/.045))
 return .262+front*.087-side*.017+.0025*math.sin(p.x*730)
chosen=[tuple(f.vertices) for f in surface.polygons if all(verts[i].z>threshold(verts[i]) for i in f.vertices)]
used=sorted({i for f in chosen for i in f});remap={i:k for k,i in enumerate(used)}
points=[]
for i in used:
 p=verts[i];noise=.004+.012*max(0,min(1,(p.z-.35)/.05))+.0007*math.sin(p.x*1400+p.y*250)+.0005*math.sin(p.z*1700)
 points.append(tuple(p+normals[i]*noise))
data=bpy.data.meshes.new('Reference short hair');data.from_pydata(points,[],[[remap[i] for i in f] for f in chosen]);data.update();hair=bpy.data.objects.new('Short dark hair - provisional hairline',data);bpy.context.collection.objects.link(hair)
for f in data.polygons:f.use_smooth=True
evaluated.to_mesh_clear()
def material(name,color):
 m=bpy.data.materials.new(name);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Metallic'].default_value=0;p.inputs['Roughness'].default_value=1;p.inputs['Specular IOR Level'].default_value=0;return m
hairmat=material('Dark brown hair',(.018,.012,.009));hair.data.materials.append(hairmat)
# Per-corner linear colors: source photographs remain read-only and unembedded.
colors=head.data.color_attributes.new(name='SkinStudy',type='FLOAT_COLOR',domain='CORNER')
for loop in head.data.loops:
 p=head.data.vertices[loop.vertex_index].co;x,y,z=p
 front=max(0,min(1,(-y-.015)/.07))
 jaw=math.exp(-((z-.170)/.033)**2)*min(1,abs(x)/.045)
 chin=math.exp(-((z-.145)/.023)**2-(x/.047)**2)
 moustache=math.exp(-((z-.218)/.009)**2-(x/.042)**4)
 density=max(jaw*.60,chin*.65,moustache*.25)*front
 grain=.80+.20*math.sin(x*4900+z*3200)
 density*=grain
 base=(.34,.15,.105);beard=(.08,.045,.025)
 c=tuple(base[k]*(1-density)+beard[k]*density for k in range(3))
 colors.data[loop.index].color=(*c,1)
skin=material('Reference skin and light stubble - study',(.43,.215,.15));attribute=skin.node_tree.nodes.new('ShaderNodeVertexColor');attribute.layer_name='SkinStudy';skin.node_tree.links.new(attribute.outputs['Color'],skin.node_tree.nodes['Principled BSDF'].inputs['Base Color']);head.data.materials.clear();head.data.materials.append(skin)
for f in head.data.polygons:f.material_index=0
# Brows follow the actual evaluated brow ridge with small opaque tapered strands.
bpy.context.view_layer.update();surface_obj=head.evaluated_get(bpy.context.evaluated_depsgraph_get())
for side in (-1,1):
 for j in range(120):
  t=(j%40)/39;layer=j//40;x=side*(.015+.049*t);z=.296+.003*math.sin(t*math.pi)-.003*t+layer*.0015
  hit,point,normal,index=surface_obj.ray_cast(Vector((x,-.5,z)),Vector((0,1,0)))
  if not hit:continue
  curve=bpy.data.curves.new('Brow strand','CURVE');curve.dimensions='3D';curve.bevel_depth=.00045;curve.bevel_resolution=1
  spline=curve.splines.new('POLY');spline.points.add(2)
  for k in range(3):
   p=point+normal*.0015+Vector((side*k*.0015,0,k*.0012));spline.points[k].co=(*p,1)
  obj=bpy.data.objects.new('Brow strand',curve);bpy.context.collection.objects.link(obj);curve.materials.append(hairmat)
# Distinct dark pupils sit on the source iris geometry; they are authored graphics.
pupil=material('Pupil',(.002,.0015,.001))
for o in list(bpy.context.scene.objects):
 if o.type=='MESH' and '.iris.' in o.name:
  center=sum((v.co for v in o.data.vertices),Vector())/len(o.data.vertices)
  o.data.materials.clear();o.data.materials.append(material('Warm brown iris',(.09,.041,.018)));o.data.materials.append(pupil)
  for f in o.data.polygons:
   c=sum((o.data.vertices[i].co for i in f.vertices),Vector())/len(f.vertices)
   f.material_index=1 if math.hypot(c.x-center.x,c.z-center.z)<.0032 else 0
scene=bpy.context.scene;scene.view_settings.exposure=-.8;scene.cycles.samples=48
camera=scene.camera;camera.data.ortho_scale=.49
camera.location=(0,-1.2,.27)
def aim():camera.rotation_euler=(Vector((0,-.025,.245))-camera.location).to_track_quat('-Z','Y').to_euler()
aim();bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'adam-naturalistic-fit-v02.blend'))
for label,location in [('front',(0,-1.2,.27)),('three-quarter',(.55,-1.0,.30)),('profile',(.95,-.32,.28))]:
 camera.location=location;aim();scene.render.filepath=str(OUT/(label+'.png'));bpy.ops.render.render(write_still=True)
report={'status':'reference_fit_study','likeness_approved':False,'reference_images_embedded':False,'source_blend_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'head_vertices':len(head.data.vertices),'hair_vertices':len(hair.data.vertices),'libraries':len(bpy.data.libraries),'changes':['broader cheek/jaw study','short dark scalp-following hair','brows on anatomical surface','subtle stubble pigment','pupils and controlled portrait exposure'],'remaining':['reference-matched nose/lips/asymmetry and skin detail','clothed body and rig','native hologram and animation validation']}
(OUT/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
