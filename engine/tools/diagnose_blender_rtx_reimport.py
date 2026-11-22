"""One read-only OBJ reimport diagnostic; writes only a create-only JSON report."""
from collections import Counter
import argparse
import hashlib
import json
from pathlib import Path
import sys
import bpy


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert bpy.app.background and '--disable-autoexec' in sys.argv
    parser = argparse.ArgumentParser()
    parser.add_argument('--variant', required=True, type=Path)
    parser.add_argument('--report', required=True, type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    variant, report = args.variant.resolve(strict=True), args.report.absolute()
    assert report.parent == variant.parent and not report.exists()
    obj_path = variant / 'Prop01_Physical_YUp.obj'
    original_sha = digest(obj_path)
    vertices, uvs, normals, corners, faces = [], [], [], [], []
    for line in obj_path.read_text(encoding='ascii').splitlines():
        row = line.split()
        if not row:
            continue
        if row[0] == 'v': vertices.append(tuple(map(float,row[1:])))
        elif row[0] == 'vt': uvs.append(tuple(map(float,row[1:])))
        elif row[0] == 'vn': normals.append(tuple(map(float,row[1:])))
        elif row[0] == 'f':
            face = []
            for token in row[1:]:
                v,t,n = map(int,token.split('/'))
                corners.append((*vertices[v-1],*uvs[t-1]));face.append(v-1)
            faces.append(tuple(face))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.obj_import(filepath=str(obj_path), forward_axis='Y',up_axis='Z',global_scale=1.0,
                          use_split_objects=False,use_split_groups=False,validate_meshes=True)
    objects = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    assert len(objects)==1
    obj=objects[0];mesh=obj.data;mesh.calc_loop_triangles()
    imported=[]; imported_faces=[];layer=mesh.uv_layers.active.data
    for triangle in mesh.loop_triangles:
        imported_faces.append(tuple(mesh.loops[i].vertex_index for i in triangle.loops))
        for i in triangle.loops:
            imported.append((*tuple(obj.matrix_world @ mesh.vertices[mesh.loops[i].vertex_index].co),*tuple(layer[i].uv)))
    def quantize(rows, digits=6): return Counter(tuple(round(v,digits) for v in row) for row in rows)
    expected_q, actual_q=quantize(corners),quantize(imported)
    wrong_before,wrong_after=expected_q-actual_q,actual_q-expected_q
    equal_lengths=len(corners)==len(imported)
    deltas=([max(abs(a[i]-b[i]) for a,b in zip(corners,imported)) for i in range(5)]
            if equal_lengths else None)
    result={'blender':bpy.app.version_string,'vertices_before':len(vertices),'vertices_imported':len(mesh.vertices),
            'triangles_before':len(faces),'triangles_imported':len(mesh.loop_triangles),
            'corner_count_before':len(corners),'corner_count_imported':len(imported),
            'face_vertex_index_order_equal':faces==imported_faces,
            'same_order_max_absolute_delta_xyzuv':deltas,
            'quantized_missing_corners':sum(wrong_before.values()),
            'quantized_extra_corners':sum(wrong_after.values()),
            'first_missing_corners':list(wrong_before.items())[:6],
            'first_extra_corners':list(wrong_after.items())[:6],
            'import_object_matrix':[[float(x) for x in row] for row in obj.matrix_world],
            'first_exact_order_differences':[{'index':i,'expected':a,'actual':b} for i,(a,b) in
                enumerate(zip(corners,imported)) if a!=b][:6],
            'source_obj_unchanged':digest(obj_path)==original_sha,
            'source_obj_sha256':original_sha}
    with report.open('x',encoding='utf8') as stream:json.dump(result,stream,indent=2,allow_nan=False)
    print(json.dumps({key:result[key] for key in ('face_vertex_index_order_equal','same_order_max_absolute_delta_xyzuv',
          'quantized_missing_corners','quantized_extra_corners','source_obj_unchanged')}))


if __name__=='__main__':main()
