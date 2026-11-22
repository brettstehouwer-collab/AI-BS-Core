"""Render a create-only Prop01 lighting review; never rewrite a source or profile.

Blender5.3 --background --factory-startup --disable-autoexec --python-exit-code1
--python THIS_FILE -- --variant EXISTING_VARIANT --output NEW_REVIEW_DIRECTORY
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

import bpy
from mathutils import Vector


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def plain(path):
    for item in (path, *path.parents):
        if item.exists():
            require(not item.is_symlink() and not item.lstat().st_file_attributes & 0x400,
                    'Linked review storage is not supported')


def pin(path):
    plain(path)
    with path.open('rb') as stream:
        data = stream.read(64 * 1024 * 1024 + 1)
    require(len(data) <= 64 * 1024 * 1024, 'Review input exceeds64MiB')
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def main():
    require(bpy.app.background and bpy.app.version[:2] == (5, 3), 'Use Blender5.3 background mode')
    require('--disable-autoexec' in sys.argv, 'Automatic embedded scripts must be disabled')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--variant', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    variant, output = args.variant.resolve(strict=True), args.output.absolute()
    plain(variant)
    plain(output)
    require(output.parent.is_dir() and not output.exists() and not output.is_relative_to(variant),
            'Use a new review directory outside the retained variant')
    manifest = json.loads((variant / 'variant_manifest.json').read_text(encoding='utf8'))
    before = {}
    for name, expected in manifest['artifacts'].items():
        require(Path(name).name == name, 'Invalid artifact basename')
        before[name] = pin(variant / name)
        require(before[name] == expected, 'Retained variant changed since export')
    output.mkdir()
    try:
        bpy.ops.wm.open_mainfile(filepath=str(variant / 'Prop01_RTX_Variant.blend'), load_ui=False)
        scene = bpy.context.scene
        objects = [obj for obj in scene.objects if obj.type == 'MESH']
        require(len(objects) == 1, 'Review requires the existing single authored mesh')
        mesh = objects[0].data
        mesh.calc_loop_triangles()
        require(len(mesh.vertices) == 6842 and len(mesh.loop_triangles) == 13500,
                'Authored geometry changed')
        # Copy the existing authored maps and redirect the new in-memory scene.
        maps = manifest['textures']
        for name in maps:
            require(Path(name).name == name, 'Invalid map basename')
            shutil.copyfile(variant / name, output / name)
        for image in bpy.data.images:
            if image.filepath:
                name = Path(bpy.path.abspath(image.filepath)).name
                if name in maps:
                    require(not image.packed_file, 'Unexpected packed map in reviewed variant')
                    image.filepath = str(output / name)
        inherited = []
        for obj in scene.objects:
            if obj.type == 'LIGHT':
                inherited.append({'name': obj.name, 'energy': obj.data.energy,
                                  'location': list(obj.location), 'previously_hidden': obj.hide_render})
                obj.hide_render = True
        # An independent calibrated review rig avoids additive inherited lights.
        world = bpy.data.worlds.new('AI-BS bounded review world')
        world.use_nodes = True
        world.node_tree.nodes.get('Background').inputs['Color'].default_value = (.18, .18, .18, 1)
        world.node_tree.nodes.get('Background').inputs['Strength'].default_value = .15
        scene.world = world
        points = [obj.matrix_world @ vertex.co for obj in objects for vertex in obj.data.vertices]
        low = Vector(tuple(min(point[i] for point in points) for i in range(3)))
        high = Vector(tuple(max(point[i] for point in points) for i in range(3)))
        center, extent = (low + high) * .5, max(high - low)
        require(0 < extent < .02, 'Unexpected physical bounds; do not rescale geometry')
        for index, (position, power) in enumerate((((1, -1, 2), 150), ((-1, -1, 1), 75), ((0, 2, 1.5), 50))):
            light = bpy.data.lights.new('AI-BS review softbox ' + str(index), 'AREA')
            light.energy, light.shape, light.size = power * extent * extent, 'DISK', extent * 2
            obj = bpy.data.objects.new(light.name, light)
            scene.collection.objects.link(obj)
            obj.location = center + Vector(position) * extent * 2
            obj.rotation_euler = (center - obj.location).to_track_quat('-Z', 'Y').to_euler()
        prefs = bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type = 'OPTIX'
        prefs.refresh_devices()
        devices = []
        for device in prefs.devices:
            device.use = device.type == 'OPTIX' and '4090' in device.name
            devices.append({'name': device.name, 'type': device.type, 'enabled': bool(device.use)})
        require(any(row['enabled'] for row in devices), 'RTX4090 OptiX unavailable')
        scene.render.engine, scene.cycles.device = 'CYCLES', 'GPU'
        scene.cycles.samples, scene.cycles.use_denoising, scene.cycles.denoiser = 16, True, 'OPTIX'
        scene.render.resolution_x = scene.render.resolution_y = 512
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = 'PNG'
        scene.render.film_transparent = False
        scene.view_settings.view_transform = 'AgX'
        scene.view_settings.exposure = 0
        camera_data = bpy.data.cameras.new('AI-BS lighting review camera')
        camera = bpy.data.objects.new(camera_data.name, camera_data)
        scene.collection.objects.link(camera)
        camera_data.type, camera_data.ortho_scale = 'ORTHO', extent * 1.65
        camera_data.clip_start, camera_data.clip_end = extent * .001, extent * 20
        scene.camera = camera
        for name, direction in (('quarter', (1, -1.5, 1)), ('top', (0, 0, 1))):
            camera.location = center + Vector(direction).normalized() * extent * 3
            camera.rotation_euler = (center - camera.location).to_track_quat('-Z', 'Y').to_euler()
            scene.render.filepath = str(output / ('review_' + name + '.png'))
            bpy.ops.render.render(write_still=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(output / 'Prop01_Lighting_Review.blend'), compress=True)
        require(all(pin(variant / name) == expected for name, expected in before.items()),
                'Retained variant bytes changed')
        report = {'status': 'RENDERED_AWAITING_VISUAL_REVIEW', 'blender': bpy.app.version_string,
                  'source_variant_unchanged': True, 'geometry_edited': False,
                  'inherited_lights_disabled_only_in_review': inherited, 'devices': devices,
                  'samples': 16, 'resolution': [512, 512], 'view_transform': 'AgX',
                  'exposure': 0, 'native_render_or_art_approval_claimed': False,
                  'artifacts': {p.name: pin(p) for p in output.iterdir() if p.is_file()}}
        with (output / 'review_receipt.json').open('x', encoding='utf8') as stream:
            json.dump(report, stream, indent=2)
        print('AI_BS_LIGHTING_REVIEW_RENDERED')
    except BaseException as error:
        with (output / 'review_failure.json').open('x', encoding='utf8') as stream:
            json.dump({'status': 'FAILED', 'failure_class': type(error).__name__, 'message': str(error)}, stream)
        raise


if __name__ == '__main__':
    main()
