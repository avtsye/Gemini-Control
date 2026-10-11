import pathlib
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from workspace_archives import compare_files, create_zip, extract_zip

class WorkspaceArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.temp.name)
        (self.root / "one.txt").write_text("a\nb\n", encoding="utf-8")
        (self.root / "two.txt").write_text("a\nc\n", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_compare(self):
        diff = compare_files(self.root, "one.txt", "two.txt", lambda _: True)
        self.assertFalse(diff["identical"])
        self.assertIn("+c", diff["diff"])

    def test_create_extract(self):
        created = create_zip(self.root, ["one.txt"], "bundle.zip", lambda _: True)
        self.assertEqual(created["files"], 1)
        result = extract_zip(self.root, "bundle.zip", "extract", lambda _: True)
        self.assertEqual(result["extracted"], 1)
        self.assertEqual((self.root / "extract" / "one.txt").read_text(), "a\nb\n")

    def test_reject_traversal(self):
        with zipfile.ZipFile(self.root / "evil.zip", "w") as z:
            z.writestr("../outside.txt", "nope")
        with self.assertRaises(ValueError):
            extract_zip(self.root, "evil.zip", "folder", lambda _: True)
        self.assertFalse((self.root / "outside.txt").exists())

    def test_never_overwrite_extract(self):
        (self.root / "extract").mkdir()
        (self.root / "extract" / "one.txt").write_text("original")
        create_zip(self.root, ["one.txt"], "bundle.zip", lambda _: True)
        with self.assertRaises(FileExistsError):
            extract_zip(self.root, "bundle.zip", "extract", lambda _: True)
        self.assertEqual((self.root / "extract" / "one.txt").read_text(), "original")

    def test_rejected_approval(self):
        self.assertEqual(create_zip(self.root, ["one.txt"], "bundle.zip", lambda _: False), {"cancelled": True})
        self.assertFalse((self.root / "bundle.zip").exists())

if __name__ == "__main__":
    unittest.main()
