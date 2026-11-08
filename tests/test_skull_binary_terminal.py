from __future__ import annotations
import contextlib
import importlib.util
import io
import json
import math
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('skull_terminal', Path(__file__).resolve().parent.parent / 'scripts' / 'skull_binary_terminal.py')
sk = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sk)


def build_glb():
    positions=[]
    for i in range(20):
        for j in range(20):
            a=2*math.pi*i/20; b=math.pi*j/20
            x=math.cos(a)*math.sin(b)
            y=math.cos(b)
            z=math.sin(a)*math.sin(b)
            positions.extend([x,y,z])
    raw=struct.pack('<%df' % len(positions), *positions)
    cfg={"asset":{"version":"2.0"},"buffers":[{"byteLength":len(raw)}],
         "bufferViews":[{"buffer":0,"byteOffset":0,"byteLength":len(raw)}],
         "accessors":[{"bufferView":0,"componentType":5126,"count":len(positions)//3,"type":"VEC3"}],
         "meshes":[{"primitives":[{"attributes":{"POSITION":0}}]}],
         "nodes":[{"mesh":0,"translation":[0,0.25,0]}],"scenes":[{"nodes":[0]}],"scene":0}
    j=json.dumps(cfg,separators=(',', ':')).encode()
    j+=b' ' * ((-len(j))%4)
    raw+=b'\x00' * ((-len(raw))%4)
    size=12+8+len(j)+8+len(raw)
    return struct.pack('<4sII',b'glTF',2,size)+struct.pack('<II',len(j),0x4e4f534a)+j+struct.pack('<II',len(raw),0x004e4942)+raw


class BinaryTerminalTests(unittest.TestCase):
    def test_parses_real_glb_format_and_scene_transform(self):
        data=build_glb()
        cfg,buf=sk.parse_glb(data)
        self.assertEqual(len(cfg['meshes']),1)
        points=sk.load_vertices(data)
        self.assertGreater(len(points),100)
        self.assertLess(max(abs(x) for p in points for x in p),1.1)
        self.assertIsInstance(buf,memoryview)

    def test_invalid_glb_rejected(self):
        for raw in (b'',b'not a GLB',build_glb()[:-1]):
            with self.assertRaises(ValueError):sk.parse_glb(raw)
        data=bytearray(build_glb());data[0]=0
        with self.assertRaises(ValueError):sk.parse_glb(bytes(data))

    def test_binary_frame_and_rotation(self):
        points=sk.load_vertices(build_glb())
        canvas=sk.SkullCanvas(points,width=72,height=26)
        frame=canvas.dashboard(color=False)
        self.assertIn('TRUE 3D',frame)
        self.assertIn('VERTICES',frame)
        self.assertIn('1',frame)
        self.assertIn('0',frame)
        self.assertEqual(frame.count('\n'),31)
        self.assertNotIn('\x1b',frame)
        canvas.yaw=0.9
        self.assertNotEqual(frame,canvas.dashboard(color=False))
        canvas.mode='BONE'
        self.assertNotEqual(frame,canvas.dashboard(color=False))

    def test_run_once_with_only_local_glb(self):
        with tempfile.TemporaryDirectory() as d:
            file=Path(d)/'skull.glb';file.write_bytes(build_glb())
            out=io.StringIO()
            with patch.object(sk.shutil,'get_terminal_size',return_value=os.terminal_size((90, 36))):
                with contextlib.redirect_stdout(out):
                    self.assertEqual(sk.run(['--once','--no-color','--model',str(file)]),0)
            self.assertIn('BINARY',out.getvalue())
            self.assertIn('0',out.getvalue())
            self.assertIn('1',out.getvalue())
            self.assertNotIn('\x1b',out.getvalue())

    def test_errors_stop_and_no_network_without_model(self):
        with tempfile.TemporaryDirectory() as d:
            missing=str(Path(d)/'missing.glb')
            with patch.object(sk.urllib.request,'urlopen',side_effect=AssertionError('network used')):
                with contextlib.redirect_stderr(io.StringIO()) as err:
                    self.assertEqual(sk.run(['--model',missing,'--once']),2)
                self.assertIn('does not exist',err.getvalue())

    def test_bounds(self):
        for args in [['--fps','0'],['--width','500'],['--frames','4000']]:
            with self.assertRaises(SystemExit):
                sk.run(args)

if __name__ == '__main__': unittest.main()