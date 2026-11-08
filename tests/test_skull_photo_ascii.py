"""Offline regression tests for the photographic anatomical ASCII bootstrap."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SKULL_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "skull_ascii_ultra.py"


@unittest.skipUnless(importlib.util.find_spec("PIL"), "Pillow optional image dependency")
class SkullPhotoAsciiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PIL import Image, ImageDraw
        cls.Image = Image
        cls.ImageDraw = ImageDraw
        spec = importlib.util.spec_from_file_location("skull_ascii_photo", SKULL_SCRIPT)
        assert spec and spec.loader
        cls.renderer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.renderer)

    def make_photo(self, path):
        im = self.Image.new("RGB", (480, 620), "white")
        draw = self.ImageDraw.Draw(im)
        draw.ellipse((45, 45, 430, 560), fill=(228, 213, 177))
        draw.ellipse((110, 230, 220, 355), fill=(28, 24, 20))
        draw.ellipse((260, 230, 370, 355), fill=(28, 24, 20))
        draw.polygon([(240, 350), (208, 460), (280, 460)], fill=(30, 26, 22))
        for x in range(115, 365, 40):
            draw.rectangle((x, 465, x + 29, 510), fill=(250, 247, 225),
                           outline=(42, 38, 31), width=5)
        im.save(path)

    def test_white_background_matted_to_black_but_bone_preserved(self):
        im = self.Image.new("RGB", (24, 24), (255, 255, 255))
        im.putpixel((12, 12), (230, 210, 170))
        im.putpixel((10, 12), (28, 24, 20))
        result = self.renderer._background_to_black(im)
        self.assertEqual(result.getpixel((0, 0)), 0)
        self.assertGreater(result.getpixel((12, 12)), 80)
        self.assertLess(result.getpixel((10, 12)), 70)

    def test_high_density_plaintext_and_cli_save(self):
        with tempfile.TemporaryDirectory() as tmp:
            img = Path(tmp) / "sample.png"
            out = Path(tmp) / "anatomy.txt"
            self.make_photo(img)
            art, raster = self.renderer.ascii_image(img, width=82)
            self.assertEqual(raster.width, 82)
            self.assertGreater(len(art.splitlines()), 35)
            self.assertGreater(len(set(art) - {" ", "\n"}), 8)
            with contextlib.redirect_stdout(io.StringIO()):
                code = self.renderer.main([str(img), "--width", "82",
                                           "--color", "bone", "--save", str(out)])
            self.assertEqual(code, 0)
            self.assertTrue(out.is_file())
            self.assertEqual(out.read_text().strip(), art.strip())

    def test_demo_download_is_opt_in_and_cached(self):
        class Response:
            status = 200
            def __init__(self, contents):
                self.contents = contents
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self, limit):
                return self.contents

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.png"
            self.make_photo(source)
            with patch.object(self.renderer.Path, "home", return_value=Path(tmp)):
                with patch.object(self.renderer, "urlopen",
                                  return_value=Response(source.read_bytes())) as network:
                    photo = self.renderer.demo_image()
                    self.assertTrue(photo.is_file())
                    self.assertIn("Xerto", photo.with_name("PHOTO-LICENSE.txt").read_text())
                    self.assertEqual(self.renderer.demo_image(), photo)
                    network.assert_called_once()
            self.assertGreater(photo.stat().st_size, 1024)

    def test_missing_input_is_explicit_not_silent(self):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as err:
            code = self.renderer.main([])
        self.assertEqual(code, 2)
        self.assertIn("Supply an image or --demo", err.getvalue())


if __name__ == "__main__":
    unittest.main()
