"""Generate original procedural OBJ/material source; no downloaded art or CAD.

Coordinates are meters with +Y up, centered in X/Z within a 12x12x8 envelope.
The fixture is deliberately stylized teaching geometry, not a hardware replica.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

ASSET_ID = '8b2bc31a-3ec4-4f8f-bd4a-2ed1d69c8264'
MATERIALS = '''AIBMAT 1
pcb 0.025 0.19 0.085 0
copper 0.65 0.22 0.065 0
gold 0.83 0.57 0.13 0
aluminum 0.60 0.64 0.69 0
steel 0.22 0.25 0.29 0
plastic 0.025 0.035 0.05 0
ceramic 0.18 0.22 0.27 0
power_trace 0.20 0.70 0.40 0.65
'''
LICENSE = '''Original AI-BS procedural motherboard teaching fixture

This stylized source mesh and material declaration were authored procedurally
for AI-BS. They contain no downloaded mesh, texture, CAD, photograph, trademark
logo, protected product blueprint, personal source material, or model weights.
They are a fictional teaching assembly, not an ASUS, NVIDIA or other hardware
manufacturer's CAD model or assertion of exact physical dimensions.

MIT License

Copyright (c) 2026 AI-BS contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this source geometry, material data and associated documentation files
(the "Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to permit
persons to whom the Software is furnished to do so, subject to the following
conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
'''


class Mesh:
    def __init__(self):
        self.vertices = []
        self.faces = []

    def triangle(self, a, b, c, material):
        cross = tuple((b[(i+1)%3]-a[(i+1)%3])*(c[(i+2)%3]-a[(i+2)%3]) -
                      (b[(i+2)%3]-a[(i+2)%3])*(c[(i+1)%3]-a[(i+1)%3]) for i in range(3))
        if sum(value*value for value in cross) < 1e-14:
            raise ValueError('Generated degenerate triangle')
        start = len(self.vertices)+1
        self.vertices.extend((a, b, c))
        self.faces.append((material, (start, start+1, start+2)))

    def quad(self, a, b, c, d, material):
        self.triangle(a, b, c, material)
        self.triangle(a, c, d, material)

    def box(self, center, extent, material, angle=0):
        cosine, sine = math.cos(angle), math.sin(angle)
        def point(x, y, z):
            x, y, z = x*extent[0], y*extent[1], z*extent[2]
            return center[0]+x*cosine+z*sine, center[1]+y, center[2]-x*sine+z*cosine
        p = [point(*corner) for corner in ((-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),
                                             (-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1))]
        for face in ((0,3,2,1),(4,5,6,7),(0,4,7,3),(1,2,6,5),(3,7,6,2),(0,1,5,4)):
            self.quad(*(p[index] for index in face), material)

    def cylinder(self, x, z, bottom, top, radius, material, segments=16):
        for index in range(segments):
            a, b = math.tau*index/segments, math.tau*(index+1)/segments
            low_a = x+radius*math.cos(a), bottom, z+radius*math.sin(a)
            low_b = x+radius*math.cos(b), bottom, z+radius*math.sin(b)
            high_a, high_b = (low_a[0],top,low_a[2]), (low_b[0],top,low_b[2])
            self.quad(low_a, high_a, high_b, low_b, material)
            self.triangle((x,bottom,z), low_a, low_b, material)
            self.triangle((x,top,z), high_b, high_a, material)

    def ring(self, x, z, bottom, top, inner, outer, material, segments=32):
        for index in range(segments):
            a, b = math.tau*index/segments, math.tau*(index+1)/segments
            def p(radius, height, theta):
                return x+radius*math.cos(theta), height, z+radius*math.sin(theta)
            self.quad(p(outer,bottom,a),p(outer,top,a),p(outer,top,b),p(outer,bottom,b),material)
            self.quad(p(inner,bottom,b),p(inner,top,b),p(inner,top,a),p(inner,bottom,a),material)
            self.quad(p(inner,top,a),p(inner,top,b),p(outer,top,b),p(outer,top,a),material)
            self.quad(p(inner,bottom,b),p(inner,bottom,a),p(outer,bottom,a),p(outer,bottom,b),material)

    def obj(self):
        def value(number):
            number = round(number, 6)
            return '0' if number == 0 else f'{number:.6f}'.rstrip('0').rstrip('.')
        lines = ['# Original procedural AI-BS teaching mesh; meters, +Y up; no external material/texture lookup',
                 '# asset-id '+ASSET_ID, '# License: motherboard-LICENSE.txt']
        lines.extend('v '+' '.join(value(v) for v in point) for point in self.vertices)
        active = None
        for material, face in self.faces:
            if material != active:
                lines.append('usemtl '+material)
                active = material
            lines.append('f '+' '.join(map(str, face)))
        return '\n'.join(lines)+'\n'


def make_mesh():
    mesh = Mesh()
    mesh.box((0,0.15,0),(5.9,0.15,5.9),'pcb')
    # Layered socket, package lid and a tall, finely segmented cooling assembly.
    mesh.box((0,0.48,0),(2.15,0.18,2.15),'plastic')
    mesh.box((0,0.76,0),(1.85,0.10,1.85),'steel')
    mesh.box((0,1.03,0),(1.55,0.17,1.55),'aluminum')
    mesh.box((0,1.34,0),(1.90,0.14,1.90),'copper')
    for index in range(17):
        mesh.box((-1.76+index*0.22,3.15,0),(0.045,1.67,1.75),'aluminum')
    mesh.ring(0,0,4.95,5.35,1.58,1.94,'plastic')
    mesh.cylinder(0,0,4.93,5.43,0.43,'steel',24)
    mesh.cylinder(0,0,5.43,5.50,0.31,'aluminum',24)
    for index in range(9):
        angle = math.tau*index/9
        mesh.box((1.03*math.cos(angle),5.17,1.03*math.sin(angle)),(0.64,0.055,0.16),
                 'plastic', -angle-0.35)
    for x in (-2.05,2.05):
        for z in (-2.05,2.05):
            mesh.cylinder(x,z,0.32,5.42,0.12,'steel',12)
            mesh.cylinder(x,z,5.42,5.52,0.18,'aluminum',12)
            mesh.box((x,5.535,z),(0.13,0.015,0.025),'plastic')
    # Capacitor banks use actual round multi-triangle geometry.
    for side in (-1,1):
        for index in range(6):
            x, z = side*3.0, -2.5+index
            mesh.cylinder(x,z,0.3,1.45,0.30,'steel',16)
            mesh.cylinder(x,z,1.45,1.51,0.28,'aluminum',16)
            mesh.box((x,1.525,z),(0.20,0.015,0.025),'plastic')
    # Chokes/MOSFETs and four slotted RAM connectors with separate gold contacts.
    for index in range(7):
        mesh.box((-2.7+index*0.9,0.65,-3.7),(0.32,0.35,0.34),'ceramic')
        mesh.box((-2.7+index*0.9,0.42,-4.5),(0.28,0.12,0.25),'plastic')
    for index in range(4):
        x = 3.8+index*0.47
        mesh.box((x,0.65,0),(0.17,0.35,2.2),'plastic')
        mesh.box((x,1.08,-2.1),(0.20,0.15,0.18),'steel')
        mesh.box((x,1.08,2.1),(0.20,0.15,0.18),'steel')
        for contact in range(10):
            mesh.box((x,1.015,-1.8+contact*0.4),(0.10,0.015,0.075),'gold')
    for index in range(19):
        mesh.box((-4.65+index*0.5,0.34,5.48),(0.15,0.035,0.32),'gold')
    # Copper/power tracks have geometric width and independent material IDs.
    for index in range(9):
        z = -5.30+index*0.19
        mesh.box((0,0.32,z),(4.5,0.02,0.035),'copper' if index%2 else 'power_trace')
    for index in range(8):
        x = -5.40+index*0.20
        mesh.box((x,0.33,0),(0.035,0.025,4.9),'copper')
    # Fictional edge connectors and screw-mounted board spacers.
    for index in range(3):
        mesh.box((-4.55,0.87,-2.5+index*2.2),(0.72,0.57,0.72),'steel')
        mesh.box((-5.29,0.83,-2.5+index*2.2),(0.04,0.31,0.47),'plastic')
    for x in (-5.3,5.3):
        for z in (-5.1,4.6):
            mesh.cylinder(x,z,0.3,0.60,0.23,'gold',16)
            mesh.cylinder(x,z,0.60,0.77,0.17,'steel',16)
            mesh.box((x,0.78,z),(0.12,0.01,0.025),'plastic')
    for point in mesh.vertices:
        if not (-6 <= point[0] <= 6 and 0 <= point[1] <= 8 and -6 <= point[2] <= 6):
            raise ValueError('Fixture exceeds declared 12x12x8 envelope')
    if not 2500 <= len(mesh.faces) <= 10000:
        raise ValueError('Detailed fixture triangle budget unexpectedly changed')
    return mesh


def generate(output):
    mesh = make_mesh()
    output.mkdir(parents=True, exist_ok=True)
    contents = {'motherboard.obj': mesh.obj(), 'motherboard.aibmat': MATERIALS,
                'motherboard-LICENSE.txt': LICENSE}
    rows = []
    for filename, content in contents.items():
        path = output/filename
        encoded = content.encode('utf-8')
        path.write_bytes(encoded)
        rows.append({'path': str(path), 'bytes': len(encoded), 'sha256': hashlib.sha256(encoded).hexdigest()})
    return {'asset_id': ASSET_ID, 'triangles': len(mesh.faces), 'source_vertices': len(mesh.vertices),
            'materials': 8, 'bounds': {'x': [-6,6], 'y': [0,8], 'z': [-6,6]}, 'files': rows}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=Path(__file__).resolve().parents[1]/'assets/source')
    args = parser.parse_args()
    print(json.dumps(generate(args.output_dir), indent=2))
