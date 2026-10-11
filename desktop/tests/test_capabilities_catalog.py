import pathlib,sys,tempfile,unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from capabilities_catalog import CAPABILITIES,catalog
from ocr_tools import ocr_engines,ocr_image
from openai_agent import TOOLS

class CatalogAndOCRTests(unittest.TestCase):
 def test_exact_35_families_and_executable_native_tools(self):
  self.assertEqual(len(CAPABILITIES),35)
  self.assertEqual(len({row[0] for row in CAPABILITIES}),35)
  records=catalog(TOOLS)
  self.assertEqual(len(records),35)
  for record in records:
   self.assertTrue(set(record["tools"]).issubset(TOOLS))
   self.assertIn(record["status"],{"missing","partial","complete"})
 def test_no_ocr_engine_gracefully_unavailable(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=pathlib.Path(tmp)
   (root/"scan.png").write_bytes(b"dummy")
   with patch("ocr_tools.shutil.which",return_value=None):
    self.assertFalse(ocr_engines()["available"])
    result=ocr_image(root,"scan.png","out.txt",lambda _:True)
    self.assertIn("unavailable",result)
    self.assertFalse((root/"out.txt").exists())
 def test_ocr_path_confinement(self):
  with tempfile.TemporaryDirectory() as tmp:
   with self.assertRaises(ValueError):
    ocr_image(tmp,"../scan.png","out.txt",lambda _:True)

if __name__=="__main__":unittest.main()
