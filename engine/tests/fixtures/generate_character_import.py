"""Generate synthetic glTF/GLB fixtures and a source-space skinning oracle.

No family references, Blender install, network or third-party Python dependency.
The oracle evaluates original column-vector joint globals and inverse binds;
it does not reproduce the engine import's bind-shape/reordering conversion.
"""
from pathlib import Path
import copy, json, math, struct, zlib

HERE = Path(__file__).resolve().parent / 'character_import'

def identity(): return [[float(r == c) for c in range(4)] for r in range(4)]
def mul(a,b): return [[sum(a[r][k]*b[k][c] for k in range(4)) for c in range(4)] for r in range(4)]
def inv(m):
    a=[m[r][:]+identity()[r] for r in range(4)]
    for c in range(4):
        pivot=max(range(c,4),key=lambda r:abs(a[r][c])); a[c],a[pivot]=a[pivot],a[c]
        d=a[c][c]; assert abs(d)>1e-12; a[c]=[x/d for x in a[c]]
        for r in range(4):
            if r != c:
                f=a[r][c]; a[r]=[x-f*y for x,y in zip(a[r],a[c])]
    return [row[4:] for row in a]
def trs(t=(0,0,0),s=(1,1,1),axis=2,angle=0):
    m=identity();c,q=math.cos(angle),math.sin(angle)
    if axis==2: m[0][0],m[0][1],m[1][0],m[1][1]=c,-q,q,c
    elif axis==1: m[0][0],m[0][2],m[2][0],m[2][2]=c,q,-q,c
    else:m[1][1],m[1][2],m[2][1],m[2][2]=c,-q,q,c
    for r in range(3):
        for col in range(3):m[r][col]*=s[col]
        m[r][3]=t[r]
    return m
def flat(m):return [m[r][c] for c in range(4) for r in range(4)]
def point(m,p):return [sum(m[r][c]*p[c] for c in range(3))+m[r][3] for r in range(3)]
def normal(m,n):
    a=inv(m);return [sum(a[c][r]*n[c] for c in range(3)) for r in range(3)]

class Fixture:
    def __init__(self):
        self.bin=bytearray(); self.views=[];self.accessors=[]
        self.positions=[[-.7,-.7,3],[-.7,.7,3],[.7,.7,3],[.7,-.7,3]]
        self.pos=self.accessor([x for p in self.positions for x in p],'f','VEC3',3,bounds=True)
        self.normal=self.accessor([0,0,-1]*4,'f','VEC3',3)
        self.joints=self.accessor([0]*16,'H','VEC4',4)
        self.weights=self.accessor([1,0,0,0]*4,'f','VEC4',4)
        self.indices=self.accessor([0,1,2,0,2,3],'I','SCALAR',1)
        self.doc={'asset':{'version':'2.0'},'scene':0,'scenes':[{'nodes':[0,1]}],
                  'nodes':[{'mesh':0,'skin':0},{}], 'skins':[{'joints':[1]}],
                  'materials':[{'doubleSided':True,'pbrMetallicRoughness':{'metallicFactor':0,'roughnessFactor':1}}],
                  'meshes':[{'primitives':[]}], 'animations':[], 'images':[], 'textures':[], 'samplers':[]}
        self.primitive()
    def accessor(self,values,fmt,shape,components,normalized=False,bounds=False):
        while len(self.bin)%4:self.bin.append(0)
        packed=struct.pack('<'+fmt*len(values),*values)
        view=len(self.views);self.views.append({'buffer':0,'byteOffset':len(self.bin),'byteLength':len(packed)})
        self.bin.extend(packed)
        a={'bufferView':view,'componentType':{'f':5126,'B':5121,'H':5123,'I':5125}[fmt],
           'count':len(values)//components,'type':shape}
        if normalized:a['normalized']=True
        if bounds:a.update(min=[min(values[c::components]) for c in range(components)],max=[max(values[c::components]) for c in range(components)])
        self.accessors.append(a);return len(self.accessors)-1
    def primitive(self,extra=None):
        attributes={'POSITION':self.pos,'NORMAL':self.normal,'JOINTS_0':self.joints,'WEIGHTS_0':self.weights}
        attributes.update(extra or {})
        self.doc['meshes'][0]['primitives']=[{'attributes':attributes,'indices':self.indices,'material':0}]
    def document(self,external=False):
        d=copy.deepcopy(self.doc);d.update(accessors=self.accessors,bufferViews=self.views,buffers=[{'byteLength':len(self.bin)}])
        if external:d['buffers'][0]['uri']='buffer.bin'
        return d
    def glb(self):
        text=json.dumps(self.document(),separators=(',',':'),allow_nan=False).encode()
        text+=b' '*((-len(text))%4); binary=bytes(self.bin)+b'\0'*((-len(self.bin))%4)
        return struct.pack('<III',0x46546c67,2,28+len(text)+len(binary))+struct.pack('<II',len(text),0x4e4f534a)+text+struct.pack('<II',len(binary),0x004e4942)+binary

def png(width,height,rgba):
    def chunk(name,body):return struct.pack('>I',len(body))+name+body+struct.pack('>I',zlib.crc32(name+body)&0xffffffff)
    scan=b''.join(b'\0'+bytes(rgba[y*width*4:(y+1)*width*4]) for y in range(height))
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(scan))+chunk(b'IEND',b'')

def generate():
    HERE.mkdir(parents=True,exist_ok=True)
    def save(name,f): (HERE/(name+'.glb')).write_bytes(f.glb())
    def bad(name,f,change):
        f=copy.deepcopy(f);change(f);save('bad-'+name,f)
    base=Fixture();save('basic',base)
    (HERE/'external.gltf').write_text(json.dumps(base.document(True),separators=(',',':')))
    (HERE/'buffer.bin').write_bytes(base.bin)
    bad('accessor-count',base,lambda f:f.accessors[0].update(count=999999999))
    bad('accessor-range',base,lambda f:f.views[0].update(byteLength=1))
    bad('accessor-stride',base,lambda f:f.views[0].update(byteStride=3))
    bad('accessor-offset',base,lambda f:f.accessors[0].update(byteOffset=1))
    bad('position-bound-missing',base,lambda f:f.accessors[0].pop('min'))
    bad('position-bound-mismatch',base,lambda f:f.accessors[0]['min'].__setitem__(0,-.5))
    bad('component',base,lambda f:f.accessors[0].update(componentType=5123))
    bad('sparse',base,lambda f:f.accessors[0].update(sparse={'count':1,'indices':{'bufferView':0,'componentType':5121},'values':{'bufferView':0}}))
    bad('required-extension',base,lambda f:f.doc.update(extensionsRequired=['KHR_unknown']))
    bad('second-influences',base,lambda f:f.doc['meshes'][0]['primitives'][0]['attributes'].update(JOINTS_1=f.joints))
    bad('cycle',base,lambda f:f.doc['nodes'][1].update(children=[1]))
    bad('long-cycle',base,lambda f:f.doc.update(nodes=[{'mesh':0,'skin':0},{'children':[2]},{'children':[1]}]))
    bad('multiple-parents',base,lambda f:f.doc.update(nodes=[{'mesh':0,'skin':0},{'children':[2]},{},{'children':[2]}],scenes=[{'nodes':[0,1,3]}]))
    bad('quaternion',base,lambda f:f.doc['nodes'][1].update(rotation=[0,0,0,0]))
    bad('singular-joint',base,lambda f:f.doc['nodes'][1].update(scale=[0,1,1]))
    bad('reflected-joint',base,lambda f:f.doc['nodes'][1].update(scale=[-1,1,1]))
    bad('sheared-joint',base,lambda f:f.doc['nodes'][1].update(matrix=flat([[1,.5,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]])))
    bad('matrix-and-trs',base,lambda f:f.doc['nodes'][1].update(matrix=flat(identity()),translation=[0,0,0]))
    bad('pbr',base,lambda f:f.doc['materials'][0]['pbrMetallicRoughness'].update(metallicFactor=1))
    bad('blend',base,lambda f:f.doc['materials'][0].update(alphaMode='BLEND'))
    bad('multiple-meshes',base,lambda f:f.doc.update(nodes=[{'mesh':0,'skin':0},{},{'mesh':0,'skin':0}],scenes=[{'nodes':[0,1,2]}]))
    bad('zero-weights',base,lambda f:f.bin.__setitem__(slice(f.views[f.weights]['byteOffset'],f.views[f.weights]['byteOffset']+16),struct.pack('<ffff',0,0,0,0)))
    bad('bad-weights',base,lambda f:f.bin.__setitem__(slice(f.views[f.weights]['byteOffset'],f.views[f.weights]['byteOffset']+16),struct.pack('<ffff',.5,.5,.5,.5)))
    bad('nan-position',base,lambda f:f.bin.__setitem__(slice(0,4),struct.pack('<f',float('nan'))))
    bad('index',base,lambda f:f.bin.__setitem__(slice(f.views[f.indices]['byteOffset'],f.views[f.indices]['byteOffset']+4),struct.pack('<I',99)))
    bad('index-stride',base,lambda f:f.views[f.indices].update(byteStride=4))
    shared=copy.deepcopy(base)
    shared.bin[:48]=struct.pack('<'+'f'*12,*([0,0,-1]*4))
    shared.accessors[shared.normal]['bufferView']=0
    save('bad-shared-vertex-view',shared)
    one_sided=copy.deepcopy(base);one_sided.doc['materials'][0]['doubleSided']=False;save('one-sided',one_sided)
    reflected_bind=Fixture();a=reflected_bind.accessor(flat(trs(s=(-1,1,1))),'f','MAT4',16)
    reflected_bind.doc['skins'][0]['inverseBindMatrices']=a;save('reflected-bind-shape',reflected_bind)

    # 64 shuffled skin joints, nonjoint helper ancestry and a nonidentity bind
    # shape. The ignored mesh transform includes a reflection/nonuniform scale.
    asym=Fixture(); B=trs((.15,-.08,.2),(1.2,.8,1.1),1,.17)
    nodes=[{'mesh':0,'skin':0,'translation':[9,4,2],'scale':[-2,3,.5]},
           {'translation':[.3,0,.1],'children':[2]},
           {'matrix':flat(trs((.2,.1,0),(1.1,.9,1),2,.12)),'children':[3]},
           {'translation':[0,.25,0],'children':list(range(4,67))}]
    globals=[identity() for _ in range(67)];globals[1]=trs((.3,0,.1));globals[2]=mul(globals[1],trs((.2,.1,0),(1.1,.9,1),2,.12));globals[3]=mul(globals[2],trs((0,.25,0)))
    for n in range(4,67):
        t=((n-4)*.002,.01*(n%3),0);nodes.append({'translation':list(t)});globals[n]=mul(globals[3],trs(t))
    order=list(range(66,3,-1))+[2]
    ibm=[mul(inv(globals[n]),B) for n in order]
    ia=asym.accessor([x for m in ibm for x in flat(m)],'f','MAT4',16)
    asym.doc.update(nodes=nodes,skins=[{'joints':order,'inverseBindMatrices':ia}])
    asym.joints=asym.accessor([0,31,62,63]*4,'H','VEC4',4)
    asym.weights=asym.accessor([.1,.2,.3,.4]*4,'f','VEC4',4);asym.primitive()
    time=asym.accessor([0,1],'f','SCALAR',1)
    rot=asym.accessor([0,0,0,1,0,math.sin(.15),0,math.cos(.15)],'f','VEC4',4)
    helper=asym.accessor([0,.25,0,0,.35,0],'f','VEC3',3)
    ignored=asym.accessor([9,4,2,99,88,77],'f','VEC3',3)
    asym.doc['animations']=[{'samplers':[{'input':time,'output':a} for a in (rot,helper,ignored)],
                             'channels':[{'sampler':0,'target':{'node':66,'path':'rotation'}},{'sampler':1,'target':{'node':3,'path':'translation'}},{'sampler':2,'target':{'node':0,'path':'translation'}}]}]
    save('asymmetric',asym)
    alternate=copy.deepcopy(asym);alternate.doc['nodes'][0].update(translation=[-900,50,700],scale=[3,-1,2]);save('ignored-mesh-transform',alternate)
    # A genuine ancestor animation must survive the import; this helper drives
    # all child joints while the actual skeleton root remains in place.
    oracle=[]
    for frame in (0,5,15,30):
        t=frame/30;g=copy.deepcopy(globals);g[3]=mul(g[2],trs((0,.25+.1*t,0)))
        for n in range(4,67):g[n]=mul(g[3],trs(((n-4)*.002,.01*(n%3),0),(1,1,1),1,.3*t if n==66 else 0))
        for vertex,p in enumerate(asym.positions):
            position=[0.,0.,0.];n=[0.,0.,0.]
            for raw,w in zip((0,31,62,63),(.1,.2,.3,.4)):
                deform=mul(g[order[raw]],ibm[raw]);v=point(deform,p);q=normal(deform,(0,0,-1))
                for axis in range(3):position[axis]+=w*v[axis];n[axis]+=w*q[axis]
            position=[-position[0]*1.2+2,position[1]*.8+.2,position[2]*1.1+1]
            n=[-n[0]/1.2,n[1]/.8,n[2]/1.1];length=math.sqrt(sum(x*x for x in n));n=[x/length for x in n]
            oracle.append([frame,vertex,*position,*n])
    (HERE/'source-oracle.txt').write_text('\n'.join(' '.join(format(x,'.17g') for x in row) for row in oracle)+'\n')
    bad('incoherent-bind',asym,lambda f:f.bin.__setitem__(slice(f.views[ia]['byteOffset'],f.views[ia]['byteOffset']+4),struct.pack('<f',4)))
    bad('inverse-bind-stride',asym,lambda f:f.views[ia].update(byteStride=64))

    # Late first key must stay held from0..1, not be shifted back to0.
    late=Fixture(); ti=late.accessor([1,2],'f','SCALAR',1); ro=late.accessor([0,0,0,1,0,0,math.sin(.25),math.cos(.25)],'f','VEC4',4)
    late.doc['animations']=[{'samplers':[{'input':ti,'output':ro}], 'channels':[{'sampler':0,'target':{'node':1,'path':'rotation'}}]}]
    save('late-key',late)
    loop=copy.deepcopy(late)
    loop.bin[loop.views[ro]['byteOffset']:loop.views[ro]['byteOffset']+32]=struct.pack('<ffffffff',0,0,0,1,0,0,0,-1)
    save('antipodal-loop',loop)
    subtle=copy.deepcopy(late)
    subtle.bin[subtle.views[ro]['byteOffset']:subtle.views[ro]['byteOffset']+32]=struct.pack('<ffffffff',0,0,0,1,0,0,math.sin(.005),math.cos(.005))
    save('small-loop-seam',subtle)
    boundary=copy.deepcopy(loop)
    boundary.bin[boundary.views[ti]['byteOffset']:boundary.views[ti]['byteOffset']+8]=struct.pack('<ff',0,136.5)
    save('frame-boundary',boundary)
    over=copy.deepcopy(boundary);over.bin[over.views[ti]['byteOffset']:over.views[ti]['byteOffset']+8]=struct.pack('<ff',0,136.501)
    save('bad-animation-frame-bound',over)
    bad('step-animation',late,lambda f:f.doc['animations'][0]['samplers'][0].update(interpolation='STEP'))
    bad('cubic-animation',late,lambda f:f.doc['animations'][0]['samplers'][0].update(interpolation='CUBICSPLINE'))
    bad('duplicate-channel',late,lambda f:f.doc['animations'][0]['channels'].append(copy.deepcopy(f.doc['animations'][0]['channels'][0])))
    bad('nonincreasing-time',late,lambda f:f.bin.__setitem__(slice(f.views[ti]['byteOffset'],f.views[ti]['byteOffset']+8),struct.pack('<ff',1,1)))
    bad('animation-stride',late,lambda f:f.views[ti].update(byteStride=4))
    bad('zero-duration',late,lambda f:f.bin.__setitem__(slice(f.views[ti]['byteOffset'],f.views[ti]['byteOffset']+8),struct.pack('<ff',0,0)))
    root=Fixture(); ti=root.accessor([0,1],'f','SCALAR',1); tr=root.accessor([0,0,0,1,0,0],'f','VEC3',3)
    root.doc['animations']=[{'samplers':[{'input':ti,'output':tr}], 'channels':[{'sampler':0,'target':{'node':1,'path':'translation'}}]}]
    save('bad-root-motion',root)

    textured=Fixture();uv=textured.accessor([0,0,0,1,1,1,1,0],'f','VEC2',2);color=textured.accessor([1,1,1,0]*4,'f','VEC4',4);textured.primitive({'TEXCOORD_0':uv,'COLOR_0':color})
    primitive=copy.deepcopy(textured.doc['meshes'][0]['primitives'][0]);seam=textured.accessor([1,0,1,1,0,1,0,0],'f','VEC2',2);primitive['attributes']['TEXCOORD_0']=seam;primitive['material']=1;textured.doc['meshes'][0]['primitives'].append(primitive)
    rgba=[255,0,0,0,0,0,255,255] # Red hidden alpha must still contribute in OPAQUE.
    image=png(2,1,rgba)
    while len(textured.bin)%4:textured.bin.append(0)
    image_view=len(textured.views);textured.views.append({'buffer':0,'byteOffset':len(textured.bin),'byteLength':len(image)});textured.bin.extend(image)
    textured.doc['images']=[{'bufferView':image_view,'mimeType':'image/png'}]
    textured.doc['samplers']=[{'magFilter':9729,'minFilter':9987,'wrapS':10497,'wrapT':10497}]
    textured.doc['textures']=[{'source':0,'sampler':0}]
    textured.doc['materials'][0]['pbrMetallicRoughness'].update(baseColorTexture={'index':0},baseColorFactor=[.8,.9,1,.2])
    textured.doc['materials'].append(copy.deepcopy(textured.doc['materials'][0]));textured.doc['materials'][1]['pbrMetallicRoughness']['baseColorFactor']=[1,.5,.25,1]
    save('textured-seams',textured)
    bad('sampler',textured,lambda f:f.doc['samplers'][0].update(wrapS=33071))
    bad('texture-transform',textured,lambda f:f.doc['materials'][0]['pbrMetallicRoughness']['baseColorTexture'].update(extensions={'KHR_texture_transform':{'offset':[.2,0]}}))
    bad('non-png-image',textured,lambda f:f.doc['images'][0].update(mimeType='image/jpeg'))
    bad('image-stride',textured,lambda f:f.views[image_view].update(byteStride=4))
    quantized=Fixture();quantized.weights=quantized.accessor([64,64,64,64]*4,'B','VEC4',4,True);quantized.primitive();save('quantized-weights',quantized)
    interleaved=Fixture()
    while len(interleaved.bin)%4:interleaved.bin.append(0)
    start=len(interleaved.bin);values=[]
    for p in interleaved.positions:values.extend([*p,0,0,-1])
    packed=struct.pack('<'+'f'*len(values),*values);interleaved.bin.extend(packed)
    view=len(interleaved.views);interleaved.views.append({'buffer':0,'byteOffset':start,'byteLength':len(packed),'byteStride':24})
    interleaved.accessors[interleaved.pos]['bufferView']=view
    interleaved.accessors[interleaved.normal].update(bufferView=view,byteOffset=12)
    save('interleaved',interleaved)
    padding=Fixture();padding.bin.append(0);bad_padding=bytearray(padding.glb());bad_padding[-1]=1
    (HERE/'bad-bin-padding.glb').write_bytes(bad_padding)
    (HERE/'README.md').write_text('Synthetic generated import fixtures. Rebuild with generate_character_import.py. No family/media references. source-oracle.txt independently evaluates original source joint globals and inverse binds at bake samples, followed by LH and nonidentity world placement.\n')
    print(json.dumps({'fixtures':len(list(HERE.glob('*.glb'))),'bytes':sum(p.stat().st_size for p in HERE.iterdir() if p.is_file())}))

if __name__=='__main__':generate()
