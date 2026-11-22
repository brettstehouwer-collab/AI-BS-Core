"""Cook the owned Blender capacitor with texture data, then render its pack."""
from pathlib import Path
import sys, json, shutil, subprocess
ROOT=Path(__file__).resolve().parents[1]
def prepare_pack(cooker, output):
    output.mkdir(parents=True,exist_ok=True)
    source=ROOT/'assets/workshop/capacitor'
    shutil.copyfile(source/'capacitor.obj',output/'capacitor.obj')
    shutil.copyfile(ROOT/'tests/fixtures/image-checker.png',output/'checker.png')
    materials=(source/'capacitor.aibmat').read_text().splitlines()
    (output/'surface.aibmat').write_text('AIBMAT 2\n'+'\n'.join(line+' checker.png' for line in materials[1:] if line.strip())+'\n')
    shutil.copyfile(source/'LICENSE.txt',output/'LICENSE.txt')
    pack=output/'pack'
    asset_id='98210284-6be3-452d-9d1c-e16bd48d08f9'
    if not pack.exists():
        subprocess.run([str(cooker),'--cook-surface','--source',str(output/'capacitor.obj'),'--materials',str(output/'surface.aibmat'),'--asset-id',asset_id,'--name','Textured workshop capacitor','--license',str(output/'LICENSE.txt'),'--output',str(pack),'--uv-origin','bottom-left'],check=True,timeout=30)
    return pack,asset_id
def verify(cooker, player, output):
    pack,asset_id=prepare_pack(cooker,output)
    subprocess.run([str(player),'--asset-showcase','--asset-root',str(pack),'--asset-id',asset_id,'--self-test','--capture',str(output/'capture.bmp'),'--report',str(output/'verification.json')],check=True,timeout=45)
    r=json.loads((output/'verification.json').read_text());assert r['status']=='passed' and r['metrics']['debug_errors']==0 and r['metrics']['asset_gpu_bytes_changed']>100 and r['metrics']['material_gpu_bytes_changed']>100
    print('PASS typed cooked capacitor showcase and material GPU readback')
if __name__=='__main__':verify(*(Path(p).resolve() for p in sys.argv[1:]))
