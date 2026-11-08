#!/usr/bin/env python3
"""SKULL // REAL MESH BINARY TERMINAL

Render a genuine CC0 human skull GLB as terminal 0/1 glyphs using a CPU z-buffer.
No browser, paid keys, third-party Python packages or installed Git checkout.
Source: KhronosGroup/glTF-Sample-Assets/Models/ScatteringSkull (CC0).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import select
import shutil
import struct
import sys
import time
import urllib.error
import urllib.request

MODEL_URL = (
    "https://raw.githubusercontent.com/KhronosGroup/glTF-Sample-Assets/"
    "main/Models/ScatteringSkull/glTF-Binary/ScatteringSkull.glb"
)
CACHE_PATH = Path.home() / ".cache" / "gpt-doug-skull" / "ScatteringSkull.glb"
MAX_MODEL_BYTES = 30 * 1024 * 1024
COMPONENTS = {5120: ('b', 1), 5121: ('B', 1), 5122: ('h', 2),
              5123: ('H', 2), 5125: ('I', 4), 5126: ('f', 4)}
VECTORS = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}


def parse_glb(data: bytes):
    """Decode the geometry-bearing chunks of a GLB v2; reject remote buffers."""
    if len(data) < 28 or len(data) > MAX_MODEL_BYTES:
        raise ValueError("GLB missing or exceeds 30 MiB limit")
    magic, version, total = struct.unpack_from('<4sII', data)
    if magic != b'glTF' or version != 2 or total != len(data):
        raise ValueError("Not a valid complete GLB v2 file")
    cursor = 12
    config = None
    binary = None
    while cursor < len(data):
        if cursor + 8 > len(data):
            raise ValueError("Truncated GLB chunk header")
        chunk_len, kind = struct.unpack_from('<II', data, cursor)
        cursor += 8
        if chunk_len % 4 or cursor + chunk_len > len(data):
            raise ValueError("Corrupt GLB chunk size")
        chunk = memoryview(data)[cursor: cursor + chunk_len]
        if kind == 0x4E4F534A and config is None:
            if chunk_len > 2 * 1024 * 1024:
                raise ValueError("Oversized GLB metadata")
            config = json.loads(bytes(chunk).decode('utf8').rstrip(' \x00'))
        elif kind == 0x004E4942 and binary is None:
            binary = chunk
        cursor += chunk_len
    if not isinstance(config, dict) or binary is None or not config.get('meshes'):
        raise ValueError("GLB contains no geometric mesh")
    if set(config.get('extensionsRequired', ())) & {
        'KHR_draco_mesh_compression', 'EXT_meshopt_compression'
    }:
        raise ValueError("Compressed mesh unsupported; use uncompressed GLB")
    for buffer in config.get('buffers', ()):
        if 'uri' in buffer:
            raise ValueError("External GLB buffers are disabled")
    return config, binary


def read_accessor(config, binary, accessor_id):
    """Decode scalar/vec3 glTF accessors with strides and offsets."""
    accessor = config['accessors'][accessor_id]
    if 'sparse' in accessor:
        raise ValueError('Sparse glTF accessor unsupported')
    view_id = accessor.get('bufferView')
    if view_id is None:
        raise ValueError('GLB accessor missing bufferView')
    view = config['bufferViews'][view_id]
    if view.get('buffer', 0) != 0:
        raise ValueError('Only embedded GLB buffer zero is supported')
    dtype, size = COMPONENTS[accessor['componentType']]
    elements = VECTORS[accessor['type']]
    num = accessor['count']
    if num < 0 or num > 5_000_000:
        raise ValueError('Invalid GLB accessor count')
    stride = view.get('byteStride', size * elements)
    if stride < size * elements:
        raise ValueError('Accessor stride is undersized')
    at = view.get('byteOffset', 0) + accessor.get('byteOffset', 0)
    end_of_view = view.get('byteOffset', 0) + view['byteLength']
    if at < 0 or (num and at + stride * (num - 1) + size * elements > min(len(binary), end_of_view)):
        raise ValueError('Out-of-bounds GLB accessor')
    unpack = struct.Struct('<' + dtype * elements).unpack_from
    return [unpack(binary, at + stride * i) for i in range(num)]


def quaternion_rotate(p, quaternion):
    x, y, z = p
    qx, qy, qz, qw = quaternion
    # v' = v + 2*(qw*(q.xyz x v) + q.xyz x (q.xyz x v))
    tx, ty, tz = 2 * (qy*z-qz*y), 2 * (qz*x-qx*z), 2 * (qx*y-qy*x)
    return (x + qw*tx + qy*tz - qz*ty,
            y + qw*ty + qz*tx - qx*tz,
            z + qw*tz + qx*ty - qy*tx)


def mat4_vec(p, matrix):
    x, y, z = p
    return (matrix[0]*x + matrix[4]*y + matrix[8]*z + matrix[12],
            matrix[1]*x + matrix[5]*y + matrix[9]*z + matrix[13],
            matrix[2]*x + matrix[6]*y + matrix[10]*z + matrix[14])


def node_local(node, point):
    if 'matrix' in node:
        return mat4_vec(point, node['matrix'])
    px, py, pz = point
    scale = node.get('scale', (1, 1, 1))
    v = quaternion_rotate((px*scale[0], py*scale[1], pz*scale[2]),
                          node.get('rotation', (0, 0, 0, 1)))
    t = node.get('translation', (0, 0, 0))
    return v[0]+t[0], v[1]+t[1], v[2]+t[2]


def load_vertices(data: bytes, *, limit: int = 70000):
    """Sample real POSITION vertices from every mesh; maintain node transforms."""
    config, binary = parse_glb(data)
    # Cache decoded accessors (many meshes instantiate the same primitive).
    accessors = {}
    def accessor(i):
        if i not in accessors:
            accessors[i] = read_accessor(config, binary, i)
        return accessors[i]

    geometries = []
    for mesh in config['meshes']:
        all_points = []
        for prim in mesh.get('primitives', []):
            if prim.get('mode', 4) != 4 or 'POSITION' not in prim.get('attributes', {}):
                continue
            all_points.extend(accessor(prim['attributes']['POSITION']))
        geometries.append(all_points)
    nodes = config.get('nodes', ())
    scenes = config.get('scenes', ())
    result = []
    if scenes:
        roots = scenes[config.get('scene', 0)].get('nodes', ())
    elif nodes:
        children = {child for node in nodes for child in node.get('children', ())}
        roots = [i for i in range(len(nodes)) if i not in children]
    else:
        roots = []

    def visit(index, parents, depth=0):
        if depth > 64:
            raise ValueError('Nested GLB scene graph too deep')
        if index < 0 or index >= len(nodes) or index in parents:
            raise ValueError('Cyclic/invalid GLB scene graph')
        node = nodes[index]
        chain = [node] + parents
        mesh_id = node.get('mesh')
        if mesh_id is not None:
            if mesh_id < 0 or mesh_id >= len(geometries):
                raise ValueError('Invalid GLB mesh reference')
            pts = geometries[mesh_id]
            step = max(1, math.ceil(len(pts) / max(1000, limit // max(1, len(geometries)))))
            for p in pts[::step]:
                v = p[:3]
                for n in chain:
                    v = node_local(n, v)
                if all(math.isfinite(a) for a in v):
                    result.append(v)
        for child in node.get('children', ()):
            visit(child, chain, depth + 1)

    if roots:
        for root in roots:
            visit(root, [])
    else:
        for points in geometries:
            result.extend(p[:3] for p in points[::max(1, math.ceil(len(points)/max(1,limit//len(geometries))))])
    if len(result) < 50:
        raise ValueError('GLB mesh contains too few vertices for a skull')
    # Uniform sampling across all instantiated meshes, for predictable frame time.
    if len(result) > limit:
        step = len(result) / limit
        result = [result[int(i * step)] for i in range(limit)]
    mins = [min(v[j] for v in result) for j in range(3)]
    maxs = [max(v[j] for v in result) for j in range(3)]
    center = [(mins[j] + maxs[j]) / 2 for j in range(3)]
    radius = max((maxs[j] - mins[j]) / 2 for j in range(3))
    if not 1e-7 < radius < 1e10:
        raise ValueError('GLB geometry has invalid scale')
    result = [((v[0]-center[0])/radius, (v[1]-center[1])/radius, (v[2]-center[2])/radius) for v in result]
    return tuple(result)


def get_model(path: str | None, offline: bool = False):
    target = Path(path).expanduser() if path else CACHE_PATH
    if target.is_file():
        content = target.read_bytes()
        parse_glb(content)
        return content, str(target)
    if path:
        raise FileNotFoundError('The given GLB file does not exist: ' + str(target))
    if offline:
        raise FileNotFoundError('No cached skull model; first run without --offline')
    print('\nSKULL // Downloading open CC0 skull mesh from Khronos (8.9 MB)...', flush=True)
    request = urllib.request.Request(MODEL_URL, headers={'User-Agent': 'GPT-DOUG-SKULL-TERMINAL/1.0'})
    try:
        with urllib.request.urlopen(request, timeout=35) as response:
            if response.url.split(':', 1)[0] != 'https':
                raise ValueError('Non-HTTPS model redirect rejected')
            content = response.read(MAX_MODEL_BYTES + 1)
        parse_glb(content)
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
        raise RuntimeError('Could not retrieve the CC0 skull GLB. Download '+ MODEL_URL +
                           ' and rerun with --model ~/Downloads/ScatteringSkull.glb. Cause: ' + str(exc)) from exc
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix('.tmp')
    try:
        with tmp.open('xb') as stream:
            stream.write(content)
        tmp.replace(target)
    finally:
        tmp.unlink(missing_ok=True)
    return content, str(target)


class SkullCanvas:
    def __init__(self, points, width=100, height=38):
        self.points = points
        self.width, self.height = width, height
        self.yaw = 0.08
        self.pitch = -0.03
        self.zoom = 1.0
        self.spin = True
        self.mode = 'BINARY'
        self.tint = 'CYAN'
        self.frame = 0
        self.orientation = 1

    def render(self, color=True):
        w, h = self.width, self.height
        zbuf = [-99.0] * (w*h)
        # intensity stores lighting + depth, no fabricated telemetry.
        ink = [0] * (w*h)
        cy, sy = math.cos(self.yaw), math.sin(self.yaw)
        cp, sp = math.cos(self.pitch), math.sin(self.pitch)
        cx, cy_screen = w/2, h/2
        scale = min(w * 0.70, h * 2.55) * self.zoom
        for idx, (xx, yy, zz) in enumerate(self.points):
            # Y-axis turntable + X-axis tilt.
            x = cy*xx + sy*zz
            z = -sy*xx + cy*zz
            y = cp*yy - sp*z
            z = sp*yy + cp*z
            # Camera has a genuine perspective term, with z-buffer occlusion.
            depth = 2.75-z
            if depth < 0.5:
                continue
            col = int(cx + (x/depth)*scale)
            row = int(cy_screen - (y/depth)*scale*0.47)
            if not (0 <= col < w and 0 <= row < h):
                continue
            at = row*w + col
            if z <= zbuf[at]:
                continue
            zbuf[at] = z
            # Intensity varies over the surface and rotation, not random bits.
            light = 0.25 + 0.24 * (x + 1) + 0.32 * (z + 1)/2 - 0.08*y
            ink[at] = max(1, min(7, int(light * 6)))
        palette = {
            'CYAN': (62, 225, 220), 'BONE': (229, 224, 202),
            'AMBER': (255, 169, 65), 'GREEN': (123, 244, 136),
        }
        r, g, b = palette[self.tint]
        lines = []
        last_color = -1
        for row in range(h):
            cells = []
            for col in range(w):
                at = row*w + col
                if ink[at] == 0:
                    ch, bright = ' ', 0
                else:
                    ch = ('1' if (col + row * 7 + self.frame // 3) % 3 else '0') if self.mode == 'BINARY' else ('@#Xx+*.')[ink[at]-1]
                    bright = ink[at]
                if color:
                    if bright != last_color:
                        last_color = bright
                        if bright:
                            factor = 0.22 + 0.11*bright
                            cells.append('\x1b[38;2;%d;%d;%dm' % (int(r*factor), int(g*factor), int(b*factor)))
                        else:
                            cells.append('\x1b[0m')
                cells.append(ch)
            lines.append(''.join(cells) + ('\x1b[0m' if color else ''))
        return '\n'.join(lines)

    def dashboard(self, color=True):
        w = self.width
        header = 'SKULL // GPT-DOUG-LLM   |   TRUE 3D VERTEX Z-BUFFER   |   TERMINAL ONLY'
        stats = ('SOURCE: CC0 HUMAN SKULL | %d VERTICES | %s | %s | YAW %03d' %
                 (len(self.points), self.mode, self.tint, int(math.degrees(self.yaw)) % 360))
        controls = ' A/D ORBIT  W/S TILT  +/- ZOOM  P PAUSE  1 FRONT  2 ANGLE  3 PROFILE  B BINARY  C COLOR  Q QUIT '
        return ('\x1b[1;36m' if color else '') + header[:w].ljust(w) + ('\x1b[0m' if color else '') + '\n' + \
               stats[:w].ljust(w) + '\n' + '='*w + '\n' + self.render(color=color) + '\n' + \
               '='*w + '\n' + controls[:w].ljust(w) + '\n' + \
               'NOTE: NO CL1 HARDWARE CONNECTED. GEOMETRY IS FROM A REAL 3D MESH.'


def run(argv=None):
    parser = argparse.ArgumentParser(description='Rotating 3D CC0 skull in 0/1 binary terminal glyphs; no browser.')
    parser.add_argument('--model', help='Use an existing local GLB file')
    parser.add_argument('--offline', action='store_true', help='Use cached model only')
    parser.add_argument('--once', action='store_true', help='Print one frame and exit')
    parser.add_argument('--frames', type=int, default=0, help='Stop after N frames (0 = interactive)')
    parser.add_argument('--width', type=int, default=0, help='Character width (36..160)')
    parser.add_argument('--fps', type=int, default=10, help='1..20; software terminal framerate')
    parser.add_argument('--no-color', action='store_true', help='Plain binary output, useful for files')
    args = parser.parse_args(argv)
    if args.width and not 36 <= args.width <= 160:
        parser.error('width must be 36..160')
    if not 1 <= args.fps <= 20 or not 0 <= args.frames <= 3600:
        parser.error('FPS 1..20; frames 0..3600')
    try:
        data, provenance = get_model(args.model, offline=args.offline)
        points = load_vertices(data)
    except (OSError, RuntimeError, ValueError, KeyError, IndexError, TypeError) as exc:
        print('SKULL ERROR: ' + str(exc), file=sys.stderr)
        return 2
    sys.stdout.write('SKULL // %d anatomical 3D points loaded from %s\n' % (len(points), provenance))
    sys.stdout.flush()
    width, rows = shutil.get_terminal_size((105, 48))
    width = args.width or max(50, min(130, width-2))
    rows = max(27, min(60, rows))
    render_h = max(20, rows-8)
    canvas = SkullCanvas(points, width=width, height=render_h)
    interactive = sys.stdout.isatty() and sys.stdin.isatty() and args.frames == 0 and not args.once
    n = 1 if args.once or (not interactive and args.frames == 0) else args.frames
    prev = None
    try:
        if interactive:
            import termios, tty
            fd = sys.stdin.fileno()
            prev = termios.tcgetattr(fd)
            tty.setcbreak(fd)
            sys.stdout.write('\x1b[?25l\x1b[2J')
        frame = 0
        while True:
            started = time.monotonic()
            if interactive:
                # Responsive terminals; do not exceed a bounded point/grid count.
                new_w, new_h = shutil.get_terminal_size((width, rows))
                canvas.width = args.width or max(50, min(130, new_w-2))
                canvas.height = max(20, min(54, new_h-8))
                sys.stdout.write('\x1b[H')
            output = canvas.dashboard(color=not args.no_color and sys.stdout.isatty())
            sys.stdout.write(output + ('\x1b[0m' if interactive and not args.no_color else '') + '\n')
            sys.stdout.flush()
            frame += 1
            canvas.frame = frame
            if n and frame >= n:
                break
            if canvas.spin:
                canvas.yaw += 0.040
            pause = max(0, 1/args.fps - (time.monotonic()-started))
            if interactive:
                ready, _, _ = select.select([sys.stdin], [], [], pause)
                if ready:
                    key = sys.stdin.read(1).lower()
                    if key in ('q', '\x03'):
                        break
                    if key == 'a': canvas.yaw -= 0.18
                    if key == 'd': canvas.yaw += 0.18
                    if key == 'w': canvas.pitch = max(-1.2, canvas.pitch - 0.13)
                    if key == 's': canvas.pitch = min(1.2, canvas.pitch + 0.13)
                    if key in ('+', '='): canvas.zoom = min(2.0, canvas.zoom + 0.12)
                    if key in ('-', '_'): canvas.zoom = max(0.55, canvas.zoom - 0.12)
                    if key == 'p': canvas.spin = not canvas.spin
                    if key == '1': canvas.yaw, canvas.pitch = 0, 0
                    if key == '2': canvas.yaw, canvas.pitch = 0.65, 0
                    if key == '3': canvas.yaw, canvas.pitch = 1.57, 0
                    if key == 'b': canvas.mode = 'BONE' if canvas.mode == 'BINARY' else 'BINARY'
                    if key == 'c':
                        options = ['CYAN', 'BONE', 'AMBER', 'GREEN']
                        canvas.tint = options[(options.index(canvas.tint)+1) % len(options)]
            else:
                time.sleep(pause)
    except KeyboardInterrupt:
        return 130
    finally:
        if prev is not None:
            import termios
            termios.tcsetattr(fd, termios.TCSADRAIN, prev)
            sys.stdout.write('\x1b[0m\x1b[?25h\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(run())