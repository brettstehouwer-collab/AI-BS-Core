"""Create-only Blender 5.3 Prop01 variant; invoke using --background --disable-autoexec.

Export: -- --source EXISTING_CLEAN_MASTER --output NEW_ABSOLUTE_DIRECTORY
        [--coordinate-convention legacy-rotation|dx12-left-handed]
Fresh-process QA: -- --verify EXISTING_VARIANT_DIRECTORY

No preferences, startup files, original masters, maps, addons or services are
written. Existing physical scale is retained: the clean master already applied
the old builder's 0.1 normalization. Legacy default maps (x,y,z)->(x,z,-y).
The explicit DX12 left-handed variant maps (x,y,z)->(x,z,y) and reverses each
triangle's corner order, retaining each corner's own UV and normal reference.
Native albedo/emission is separate from Blender's normal/roughness/metallic use.
API reference: https://docs.blender.org/api/current/bpy.ops.wm.html
"""
from collections import Counter
from datetime import datetime, timezone
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import struct
import sys
import uuid

import bpy
from mathutils import Vector

SOURCE = Path(r'D:\AI-BS-Game-Resources\Prop01_Implementation_20261104_v01\asset_v01\Prop01_Clean_Game_Master.blend')
MAPS = ('Prop01_Albedo_2048.png', 'Prop01_Albedo_1024.png',
        'Prop01_Normal_2048.png', 'Prop01_Roughness_1024.png', 'Prop01_Metallic_1024.png')
LOW, HIGH = (-.0068, -.0068, -.00085), (.0068, .0068, .00825)
MESH_NAME = 'Prop01_Game_Capacitor'


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def plain(path):
    for part in (path, *path.parents):
        if part.exists():
            info = part.lstat()
            require(not part.is_symlink() and not getattr(info, 'st_file_attributes', 0) & 0x400,
                    'Linked/reparse storage is not admitted')


def pin(path):
    plain(path)
    with path.open('rb') as stream:
        raw = stream.read(64 * 1024 * 1024 + 1)
    require(len(raw) <= 64 * 1024 * 1024, 'Artifact exceeds bounded fingerprint input')
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def write_json(path, value):
    with path.open('x', encoding='utf8', newline='\n') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def bounds(points):
    return [[min(p[i] for p in points) for i in range(3)],
            [max(p[i] for p in points) for i in range(3)]]


def native(value, convention='legacy-rotation'):
    require(convention in ('legacy-rotation', 'dx12-left-handed'), 'Unknown coordinate convention')
    return value[0], value[2], -value[1] if convention == 'legacy-rotation' else value[1]


def png_dimensions(path):
    with path.open('rb') as stream:
        header = stream.read(24)
    require(header[:8] == b'\x89PNG\r\n\x1a\n' and header[12:16] == b'IHDR', 'Authored map must be PNG')
    width, height = struct.unpack('>II', header[16:24])
    require(0 < width <= 2048 and 0 < height <= 2048, 'Authored map exceeds bounded dimensions')
    return [width, height]


def export(source, output, coordinate_convention):
    source = source.resolve(strict=True)
    require(source == SOURCE.resolve(strict=True), 'Only the reviewed existing clean Prop01 master is admitted')
    require(output.is_absolute() and output.parent.is_dir() and not output.exists(),
            'Output must be a new absolute child of an existing directory')
    plain(output)
    require(not output.is_relative_to(source.parent), 'Do not write a variant inside retained original asset evidence')
    inputs = [source, *(source.parent / 'exports' / name for name in (*MAPS, 'LICENSE.txt'))]
    before = {str(path): pin(path) for path in inputs}
    require(before[str(source)]['bytes'] <= 32 * 1024 * 1024, 'Unexpected master size')
    output.mkdir()
    try:
        bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False)
        meshes = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
        require(len(meshes) == 1 and meshes[0].name == MESH_NAME, 'Unexpected clean-master mesh set')
        obj = meshes[0]
        require(not obj.modifiers, 'Do not apply unreviewed modifiers')
        require(all(abs(obj.matrix_world[i][j] - (1 if i == j else 0)) < 1e-8
                    for i in range(4) for j in range(4)), 'Unexpected master object transform')
        mesh = obj.data
        mesh.calc_loop_triangles()
        require(len(mesh.vertices) == 6842 and len(mesh.loop_triangles) == 13500 and
                len(mesh.loops) == 40500 and all(len(p.vertices) == 3 for p in mesh.polygons),
                'The intended authored game geometry changed')
        require('GameUV' in mesh.uv_layers, 'Expected authored GameUV is missing')
        source_bounds = bounds([tuple(v.co) for v in mesh.vertices])
        require(all(abs(source_bounds[a][i] - expected[i]) < 1e-7
                    for a, expected in enumerate((LOW, HIGH)) for i in range(3)),
                'Physical clean-master bounds changed; never apply scale twice')
        texture_info = {}
        for name in MAPS:
            original = source.parent / 'exports' / name
            require(original.stat().st_size <= 32 * 1024 * 1024, 'Unexpected source texture size')
            texture_info[name] = {'dimensions': png_dimensions(original),
                                  'colour_space_intended': 'sRGB' if 'Albedo' in name else 'linear data'}
            shutil.copyfile(original, output / name)
        shutil.copyfile(source.parent / 'exports/LICENSE.txt', output / 'LICENSE.txt')
        # Preserve SourceUV and material graphs. Rebind only the known authored
        # images to copied files, leaving source geometry and all UVs intact.
        active_images = {node.image for material in mesh.materials if material and material.use_nodes
                         for node in material.node_tree.nodes if node.type == 'TEX_IMAGE' and node.image}
        for image in active_images:
            name = Path(bpy.path.abspath(image.filepath)).name
            require(name in MAPS, 'Material graph references an unreviewed texture')
        for image in bpy.data.images:
            name = Path(bpy.path.abspath(image.filepath)).name if image.filepath else ''
            if name in MAPS:
                image.filepath = str(output / name)
                if image.packed_file:
                    # REMOVE drops only this in-memory packed copy; copied source
                    # PNG remains byte-identical and no original is rewritten.
                    image.unpack(method='REMOVE')
                image.filepath = str(output / name)
        uv = mesh.uv_layers['GameUV'].data
        left_handed = coordinate_convention == 'dx12-left-handed'
        transform = lambda value: native(value, coordinate_convention)
        lines = ['# AI-BS owned Prop01 variant: metres; +Y up; explicit convention ' + coordinate_convention,
                 'mtllib Prop01.mtl', 'o ' + MESH_NAME]
        lines += ['v ' + ' '.join(format(x, '.9g') for x in transform(v.co)) for v in mesh.vertices]
        lines += ['vt ' + ' '.join(format(x, '.9g') for x in uv[loop.index].uv) for loop in mesh.loops]
        lines += ['vn ' + ' '.join(format(x, '.9g') for x in transform(n.vector)) for n in mesh.corner_normals]
        require(len(mesh.corner_normals) == len(mesh.loops), 'Corner normals must be complete')
        lines.append('usemtl prop01_surface')
        for triangle in mesh.loop_triangles:
            loops = (triangle.loops[0], triangle.loops[2], triangle.loops[1]) if left_handed else triangle.loops
            lines.append('f ' + ' '.join(f'{mesh.loops[i].vertex_index+1}/{i+1}/{i+1}' for i in loops))
        obj_path = output / 'Prop01_Physical_YUp.obj'
        with obj_path.open('x', encoding='ascii', newline='\n') as stream:
            stream.write('\n'.join(lines) + '\n')
        require(obj_path.stat().st_size < 32 * 1024 * 1024, 'Native OBJ input byte budget exceeded')
        for label, name in (('Hero', MAPS[0]), ('Repeated', MAPS[1])):
            (output / ('Prop01_' + label + '.aibmat')).write_text(
                'AIBMAT 2\nprop01_surface 1 1 1 0 ' + name + '\n', encoding='ascii')
        (output / 'Prop01.mtl').write_text(
            'newmtl prop01_surface\nKd 1 1 1\nmap_Kd Prop01_Albedo_2048.png\n', encoding='ascii')
        scene = bpy.context.scene
        scene.unit_settings.system = 'METRIC'
        scene.unit_settings.scale_length = 1.0
        prefs = bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type = 'OPTIX'
        prefs.refresh_devices()
        devices = []
        for device in prefs.devices:
            device.use = device.type == 'OPTIX' and '4090' in device.name
            devices.append({'name': device.name, 'type': device.type, 'enabled': bool(device.use)})
        require(any(d['enabled'] for d in devices), 'Reviewed RTX4090 OptiX device unavailable')
        scene.render.engine = 'CYCLES'
        scene.cycles.device = 'GPU'
        scene.cycles.samples = 8
        scene.cycles.use_denoising = True
        scene.cycles.denoiser = 'OPTIX'
        scene.render.resolution_x = scene.render.resolution_y = 256
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = 'PNG'
        center = (Vector(source_bounds[0]) + Vector(source_bounds[1])) * .5
        extent = max(Vector(source_bounds[1]) - Vector(source_bounds[0]))
        camera_data = bpy.data.cameras.new('AI-BS variant review camera')
        camera = bpy.data.objects.new(camera_data.name, camera_data)
        scene.collection.objects.link(camera)
        camera_data.type, camera_data.ortho_scale = 'ORTHO', extent * 1.65
        camera_data.clip_start, camera_data.clip_end = extent * .001, extent * 20
        camera.location = center + Vector((1, -1.5, 1)).normalized() * extent * 3
        camera.rotation_euler = (center-camera.location).to_track_quat('-Z', 'Y').to_euler()
        scene.camera = camera
        inherited_lights = []
        for inherited in scene.objects:
            if inherited.type == 'LIGHT':
                inherited_lights.append({'name': inherited.name, 'energy': inherited.data.energy,
                                         'previously_hidden': inherited.hide_render})
                inherited.hide_render = True
        scene.world = bpy.data.worlds.new('AI-BS bounded variant review world')
        scene.world.use_nodes = True
        background = next(n for n in scene.world.node_tree.nodes if n.type == 'BACKGROUND')
        background.inputs['Color'].default_value = (.18, .18, .18, 1)
        background.inputs['Strength'].default_value = .15
        scene.view_settings.view_transform = 'AgX'
        scene.view_settings.exposure = 0
        for index, (offset, power) in enumerate((((1, -1, 2), 150), ((-1, -1, 1), 75), ((0, 2, 1.5), 50))):
            data = bpy.data.lights.new('AI-BS variant softbox ' + str(index), 'AREA')
            data.energy, data.shape, data.size = power * extent * extent, 'DISK', extent * 2
            light = bpy.data.objects.new(data.name, data)
            scene.collection.objects.link(light)
            light.location = center + Vector(offset) * extent * 2
            light.rotation_euler = (center-light.location).to_track_quat('-Z', 'Y').to_euler()
        scene.render.filepath = str(output / 'Prop01_RTX_Quarter.png')
        # Saving this new project never invokes save_userpref/save_homefile.
        bpy.ops.wm.save_as_mainfile(filepath=str(output / 'Prop01_RTX_Variant.blend'), compress=True)
        bpy.ops.render.render(write_still=True)
        require((output / 'Prop01_RTX_Quarter.png').is_file(), 'Representative GPU render missing')
        require(all(pin(Path(path)) == expected for path, expected in before.items()), 'Original input bytes changed')
        manifest = {'schema': 1, 'status': 'EXPORTED_AWAITING_FRESH_REIMPORT',
                    'utc': datetime.now(timezone.utc).isoformat(), 'blender': bpy.app.version_string,
                    'source': str(source), 'source_blend': str(source), 'source_inputs': before, 'originals_unchanged': True,
                    'master_blend': str(output / 'Prop01_RTX_Variant.blend'),
                    'native_obj': str(obj_path), 'hero_aibmat': str(output / 'Prop01_Hero.aibmat'),
                    'repeated_aibmat': str(output / 'Prop01_Repeated.aibmat'), 'license': str(output / 'LICENSE.txt'),
                    'hero_asset_id': str(uuid.uuid4()), 'repeated_asset_id': str(uuid.uuid4()),
                    'vertices': len(mesh.vertices), 'triangles': len(mesh.loop_triangles), 'uv_records': len(mesh.loops),
                    'source_zup_bounds_m': source_bounds,
                    'native_yup_bounds_m': bounds([transform(v.co) for v in mesh.vertices]),
                    'geometry_scale_applied': 1.0,
                    'coordinate_convention': coordinate_convention,
                    'native_axis_mapping': '(x,y,z)->(x,z,y)' if left_handed else '(x,y,z)->(x,z,-y)',
                    'coordinate_matrix': [[1,0,0],[0,0,1],[0,1 if left_handed else -1,0]],
                    'coordinate_matrix_determinant': -1 if left_handed else 1,
                    'triangle_winding': 'reversed i0,i2,i1 with attached UV/normal indices' if left_handed else 'source i0,i1,i2 retained',
                    'normal_mapping': 'Same orthogonal coordinate map as positions; source normal values retained',
                    'editable_master_coordinates': 'Original right-handed Z-up; no geometry/UV reflection applied to master',
                    'runtime_instance_scale_precedent': 100.0, 'obj_uv_set': 'GameUV only',
                    'editable_master_uv_sets': [layer.name for layer in mesh.uv_layers],
                    'handedness_caveat': 'Explicit new LH adapter requires actual native lettering/orientation acceptance; no old pack/schema/renderer change' if left_handed else 'Existing DX12 mirrored lettering caveat retained; legacy proper rotation is not a handedness conversion',
                    'native_shading_scope': 'AIBSurf2 albedo/emission; normal/roughness/metallic remain Blender source maps',
                    'textures': texture_info, 'artistic_approval': False,
                    'preview_scope': 'Technical representative render; lighting/clipping/lettering need separate visual review',
                    'render': {'device': 'GPU', 'backend': 'OPTIX', 'samples': 8,
                    'width': 256, 'height': 256, 'devices': devices,
                    'lighting_rig': 'Isolated neutral world strength .15; area powers150/75/50*extent^2; inherited lights hidden; AgX exposure0',
                    'inherited_lights_hidden': inherited_lights},
                    'artifacts': {p.name: pin(p) for p in output.iterdir() if p.is_file()}}
        write_json(output / 'variant_manifest.json', manifest)
        print('AI_BS_VARIANT_EXPORTED ' + json.dumps({'output': str(output), 'triangles': manifest['triangles']}))
    except BaseException as error:
        write_json(output / 'export_failure.json', {'status': 'FAILED', 'error_type': type(error).__name__, 'error': str(error)})
        raise


def obj_corners(path):
    vertices, uvs, result = [], [], []
    for line in path.read_text(encoding='ascii').splitlines():
        fields = line.split()
        if not fields:
            continue
        if fields[0] == 'v':
            vertices.append(tuple(map(float, fields[1:])))
        elif fields[0] == 'vt':
            uvs.append(tuple(map(float, fields[1:])))
        elif fields[0] == 'f':
            require(len(fields) == 4, 'Only exported triangles admitted')
            for token in fields[1:]:
                position, uv, normal = map(int, token.split('/'))
                require(position > 0 and uv > 0 and normal > 0, 'Only positive complete corner references admitted')
                result.append((*vertices[position-1], *uvs[uv-1]))
    return vertices, result


def verify(output, report_name):
    require(output.is_absolute() and output.is_dir(), 'Existing absolute variant directory required')
    plain(output)
    require(Path(report_name).name == report_name and report_name.endswith('.json') and
            report_name.startswith('fresh_reimport_verification') and len(report_name) <= 100 and
            all(char.isascii() and (char.isalnum() or char in '_.-') for char in report_name),
            'Verification report must be a bounded fresh_reimport_verification*.json basename')
    target = output / report_name
    require(not target.exists(), 'Do not overwrite an earlier reimport result')
    try:
        manifest = json.loads((output / 'variant_manifest.json').read_text(encoding='utf8'))
        for name, expected in manifest['artifacts'].items():
            require(Path(name).name == name and pin(output / name) == expected, 'Variant artifact pin mismatch')
        for path, expected in manifest['source_inputs'].items():
            require(pin(Path(path)) == expected, 'Original input bytes changed')
        bpy.ops.wm.open_mainfile(filepath=str(output / 'Prop01_RTX_Variant.blend'), load_ui=False)
        authored_images = []
        for obj in bpy.context.scene.objects:
            if obj.type != 'MESH':
                continue
            for material in obj.data.materials:
                if not material or not material.use_nodes:
                    continue
                for node in material.node_tree.nodes:
                    if node.type == 'TEX_IMAGE' and node.image:
                        path = Path(bpy.path.abspath(node.image.filepath)).resolve()
                        require(path.parent == output.resolve() and path.name in MAPS and path.is_file(),
                                'Saved variant material texture must resolve inside its own variant')
                        authored_images.append({'file': path.name, 'colour_space': node.image.colorspace_settings.name})
        require({row['file'] for row in authored_images} == set(MAPS) - {'Prop01_Albedo_1024.png'},
                'Saved variant must retain all four authored material maps')
        colour_space_matches = all(row['colour_space'] == ('sRGB' if 'Albedo' in row['file'] else 'Non-Color')
                                   for row in authored_images)
        # Explicit Y-forward/Z-up requests no axis conversion, allowing raw native
        # OBJ coordinates to be compared directly. This is data QA, not a new
        # Blender-to-engine handedness policy or artistic orientation approval.
        bpy.ops.wm.read_factory_settings(use_empty=True)
        props = bpy.ops.wm.obj_import.get_rna_type().properties
        require(all(name in props for name in ('filepath', 'forward_axis', 'up_axis', 'global_scale')),
                'Installed OBJ importer API lacks required explicit options')
        bpy.ops.wm.obj_import(filepath=str(output / 'Prop01_Physical_YUp.obj'), forward_axis='Y',
                              up_axis='Z', global_scale=1.0, use_split_objects=False,
                              use_split_groups=False, validate_meshes=True)
        meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
        require(len(meshes) == 1, 'Fresh reimport must contain exactly one mesh')
        obj = meshes[0]
        mesh = obj.data
        mesh.calc_loop_triangles()
        require(len(mesh.vertices) == manifest['vertices'] and len(mesh.loop_triangles) == manifest['triangles'],
                'Fresh imported geometry count mismatch')
        require(len(mesh.uv_layers) == 1, 'Fresh import must contain only the exported UV set')
        imported = []
        uv = mesh.uv_layers.active.data
        for triangle in mesh.loop_triangles:
            for index in triangle.loops:
                imported.append((*tuple(obj.matrix_world @ mesh.vertices[mesh.loops[index].vertex_index].co), *tuple(uv[index].uv)))
        raw_vertices, expected = obj_corners(output / 'Prop01_Physical_YUp.obj')
        def canonical_float32(value):
            require(math.isfinite(value), 'Only finite geometry and UV values are admitted')
            return struct.unpack('<f', struct.pack('<f', value))[0]
        def triangle_corners(rows):
            require(len(rows) % 3 == 0, 'Complete triangle corners required')
            encoded = [tuple(canonical_float32(value) for value in row) for row in rows]
            # Cyclic start-corner rotation is allowed; reversed winding and
            # regrouping corners into different triangles are not. Nine-digit
            # OBJ decimals round-trip original IEEEfloat32 exactly. Decimal
            # round(...,6) buckets are unsuitable near half-boundaries.
            return Counter(min(tuple(encoded[index+offset:index+3] + encoded[index:index+offset])
                               for offset in range(3)) for index in range(0, len(encoded), 3))
        require(len(imported) == len(expected) == manifest['uv_records'] and
                triangle_corners(imported) == triangle_corners(expected),
                'Fresh import triangle positions/UVs/winding differ after exact IEEEfloat32 roundtrip')
        max_position_delta = max(abs(a[i]-b[i]) for a,b in zip(imported, expected) for i in range(3))
        max_uv_delta = max(abs(a[i]-b[i]) for a,b in zip(imported, expected) for i in (3,4))
        imported_bounds = bounds([tuple(obj.matrix_world @ vertex.co) for vertex in mesh.vertices])
        require(all(abs(imported_bounds[a][i] - manifest['native_yup_bounds_m'][a][i]) < 1e-7
                    for a in range(2) for i in range(3)), 'Fresh raw-coordinate bounds mismatch')
        image_paths = [Path(bpy.path.abspath(node.image.filepath)).resolve()
                       for material in mesh.materials if material and material.use_nodes
                       for node in material.node_tree.nodes if node.type == 'TEX_IMAGE' and node.image]
        require(image_paths and all(path.parent == output.resolve() and path.is_file() for path in image_paths),
                'Fresh import texture references must resolve inside the new variant')
        report = {'status': 'PASS', 'blender': bpy.app.version_string, 'process_id': __import__('os').getpid(),
                  'vertices': len(mesh.vertices), 'triangles': len(mesh.loop_triangles), 'uv_sets': len(mesh.uv_layers),
                  'corner_count': len(imported), 'position_uv_comparison': 'Exact IEEEfloat32 triangle-corner cyclic multiset; winding preserved',
                  'same_order_max_decimal_to_import_position_delta_m': max_position_delta,
                  'same_order_max_decimal_to_import_uv_delta': max_uv_delta,
                  'raw_native_coordinate_bounds_m': imported_bounds, 'texture_paths_local': True,
                  'original_source_pins_unchanged': True, 'variant_pins_unchanged': True,
                  'saved_variant_material_images': authored_images,
                  'authored_colour_spaces_match_intent': colour_space_matches,
                  'ordinary_gameplay_or_native_render_claimed': False}
        require(all(pin(output / name) == expected for name, expected in manifest['artifacts'].items()),
                'Fresh readback changed variant artifacts')
        write_json(target, report)
        print('AI_BS_FRESH_REIMPORT_PASS ' + json.dumps(report))
    except BaseException as error:
        write_json(target, {'status': 'FAILED', 'error_type': type(error).__name__, 'error': str(error)})
        raise


def main():
    require(bpy.app.background and tuple(bpy.app.version[:2]) == (5, 3), 'Use Blender5.3 background mode')
    require('--disable-autoexec' in sys.argv, 'Explicit --disable-autoexec is required')
    arguments = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--verify', type=Path)
    parser.add_argument('--verification-report', default='fresh_reimport_verification.json')
    parser.add_argument('--coordinate-convention', choices=('legacy-rotation', 'dx12-left-handed'), default='legacy-rotation')
    args = parser.parse_args(arguments)
    if args.verify:
        require(args.source is None and args.output is None, 'Verify mode accepts only --verify')
        verify(args.verify, args.verification_report)
    else:
        require(args.source is not None and args.output is not None, 'Export requires --source and --output')
        export(args.source, args.output, args.coordinate_convention)


if __name__ == '__main__':
    main()
