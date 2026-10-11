import pathlib,sys,tempfile,unittest,zipfile,json
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from capability_workshop import CapabilityWorkshop

class CapabilityPackageTests(unittest.TestCase):
 def test_export_import_and_remove(self):
  with tempfile.TemporaryDirectory() as temp:
   root=pathlib.Path(temp)
   workshop=CapabilityWorkshop(root/"cap")
   identifier=workshop.draft("Exported","Testing",
     "def run(payload, output_dir):\n return {'answer':payload.get('number',2)}")
   exported=workshop.export_package(identifier,root/"extension.zip")
   self.assertTrue(pathlib.Path(exported["exported"]).exists())
   result=workshop.import_package(root/"extension.zip")
   meta=workshop._manifest(workshop._path(result["id"]))
   self.assertEqual(meta["status"],"draft")
   self.assertTrue(meta["require_test"])
   self.assertIn("def run(",workshop.source(result["id"]))
   with self.assertRaises(PermissionError):workshop.remove(result["id"])
   self.assertEqual(workshop.remove(result["id"],True)["removed"],result["id"])
 def test_reject_unexpected_archive_entries(self):
  with tempfile.TemporaryDirectory() as temp:
   root=pathlib.Path(temp)
   workshop=CapabilityWorkshop(root/"cap")
   with zipfile.ZipFile(root/"bad.zip","w") as bundle:
    bundle.writestr("manifest.json",json.dumps({"name":"Bad","package_version":1}))
    bundle.writestr("main.py","def run(payload,output_dir): return {}")
    bundle.writestr("../unsafe.txt","unsafe")
   with self.assertRaises(ValueError):workshop.import_package(root/"bad.zip")
if __name__=="__main__":unittest.main()
