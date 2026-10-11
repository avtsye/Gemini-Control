import pathlib,sys,tempfile,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from capability_workshop import CapabilityWorkshop

class LifecycleTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  self.workshop=CapabilityWorkshop(pathlib.Path(self.tmp.name)/"cap")
  self.identifier=self.workshop.draft("Echo","", "def run(payload, output_dir):\n return {'version':1}")
 def tearDown(self): self.tmp.cleanup()
 def test_revise_rollback(self):
  new="def run(payload, output_dir):\n return {'version':2}"
  with self.assertRaises(PermissionError):
   self.workshop.revise(self.identifier,new)
  revised=self.workshop.revise(self.identifier,new,approved=True)
  self.assertEqual(revised["version"],2)
  self.assertEqual(self.workshop.versions(self.identifier),[1])
  rolled=self.workshop.rollback(self.identifier,1,approved=True)
  self.assertEqual(rolled["version"],3)
  self.assertIn("'version':1",self.workshop.source(self.identifier))
 def test_smoke_test_records_result(self):
  result=self.workshop.test_capability(self.identifier,{"number":2},lambda _:True)
  self.assertTrue(result["passed"])
  last=self.workshop._manifest(self.workshop._path(self.identifier))["last_test"]
  self.assertTrue(last["passed"])
  self.assertEqual(last["source_sha256"],self.workshop._manifest(self.workshop._path(self.identifier))["source_sha256"])
 def test_non_utf8_plugin_output_does_not_crash_reader(self):
  code="import sys\ndef run(payload, output_dir):\n sys.stderr.buffer.write(bytes([0xe3,0x28,0xa1]))\n raise RuntimeError('broken output')"
  ident=self.workshop.draft("Mixed encoding","",code)
  self.workshop.activate(ident,True)
  result=self.workshop.run(ident,{},lambda _:True)
  self.assertIn("error",result)
  self.assertIn("details",result)
 def test_dependency_validation(self):
  with self.assertRaises(PermissionError):self.workshop.set_dependencies(self.identifier,["Pillow==12.0.0"])
  with self.assertRaises(ValueError):self.workshop.set_dependencies(self.identifier,["--extra-index-url=https://bad.example"],True)
  result=self.workshop.set_dependencies(self.identifier,["Pillow==12.0.0"],True)
  self.assertEqual(result["installed"],False)
  self.assertFalse(self.workshop.dependency_status(self.identifier)["environment_ready"])
 def test_dependency_install_denied_without_running_pip(self):
  self.workshop.set_dependencies(self.identifier,["Pillow==12.0.0"],True)
  self.assertEqual(self.workshop.install_dependencies(self.identifier,lambda _:False),{"cancelled":True})
  self.assertFalse((self.workshop._path(self.identifier)/"venv").exists())
 def test_sensitive_import_cannot_activate(self):
  source="import subprocess\ndef run(payload, output_dir):\n return {}"
  self.workshop.revise(self.identifier,source,True)
  with self.assertRaises(PermissionError):self.workshop.activate(self.identifier,True)
 def test_disabled_after_revise(self):
  self.workshop.activate(self.identifier,True)
  self.assertEqual(self.workshop.revise(self.identifier,"def run(payload, output_dir):\n return {}",True)["status"],"disabled")

if __name__=="__main__":unittest.main()
