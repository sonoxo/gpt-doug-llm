from pathlib import Path
import tempfile
import unittest

from zyra_lang.compiler import ZyraCompileError, compile_file, compile_source, parse_source


SOURCE = '''app DemoApp {
  strict true
  verbatim true

  build verbatim """
Build the requested application.
- live chat
- viewer count
Do not rename live chat.
Never remove viewer count.
"""
}
'''


class ZyraLanguageTests(unittest.TestCase):
    def test_parse_preserves_verbatim_intent(self):
        program = parse_source(SOURCE)
        self.assertEqual(program.app_name, "DemoApp")
        self.assertTrue(program.strict)
        self.assertTrue(program.verbatim)
        self.assertEqual(program.required, ("live chat", "viewer count"))
        self.assertIn("Do not rename live chat.", program.forbidden_changes)
        self.assertEqual(program.source_text, SOURCE)

    def test_compile_emits_typescript_and_manifest(self):
        result = compile_source(SOURCE)
        self.assertEqual(result["manifest"]["verbatim_score_target"], 100)
        self.assertIn("export const zyraBuildSpec", result["typescript"])
        self.assertIn("viewer count", result["typescript"])

    def test_verbatim_requires_build_block(self):
        with self.assertRaises(ZyraCompileError):
            parse_source("app Broken { strict true verbatim true }")

    def test_compile_file_writes_outputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "demo.zyra"
            output_path = Path(temp_dir) / "build"
            source_path.write_text(SOURCE, encoding="utf-8")

            outputs = compile_file(source_path, output_path)

            self.assertTrue(Path(outputs["manifest"]).exists())
            self.assertTrue(Path(outputs["typescript"]).exists())


if __name__ == "__main__":
    unittest.main()
