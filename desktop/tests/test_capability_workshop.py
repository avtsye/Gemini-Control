import pathlib,sys,tempfile,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from capability_workshop import CapabilityWorkshop

class CapabilityWorkshopTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  self.w=CapabilityWorkshop(pathlib.Path(self.tmp.name)/"capabilities")
 def tearDown(self):self.tmp.cleanup()
 def test_draft_disabled_and_source_available(self):
  id=self.w.draft("Example","description","def run(payload, output_dir):\n return {'ok':True}\n")
  self.assertEqual(self.w.inspect(id)["status"],"draft")
  self.assertIn("def run(",self.w.source(id))
  with self.assertRaises(PermissionError):self.w.run(id,{},lambda _:False)
 def test_reject_invalid_source(self):
  for source in ("print('not a plugin')","def run(:","def run(payload): return {}"):
   with self.subTest(source=source),self.assertRaises((ValueError,SyntaxError)):
    self.w.draft("Bad","",source)
 def test_activation_requires_approval(self):
  id=self.w.draft("Test","","def run(payload, output_dir):\n return {}")
  with self.assertRaises(PermissionError):self.w.activate(id,False)
  self.assertEqual(self.w.inspect(id)["status"],"draft")
 def test_execute_only_with_approval(self):
  id=self.w.draft("Test","","def run(payload, output_dir):\n return {'echo':payload.get('x')}")
  self.w.activate(id,True)
  self.assertEqual(self.w.run(id,{"x":"ok"},lambda _:False),{"cancelled":True})
  actual=self.w.run(id,{"x":"ok"},lambda _:True)
  self.assertEqual(actual["result"]["echo"],"ok")
 def test_sensitive_import_is_flagged(self):
  id=self.w.draft("Sensitive","","import subprocess\ndef run(payload, output_dir):\n return {}")
  self.assertTrue(any("subprocess" in x for x in self.w.inspect(id)["findings"]))
if __name__=="__main__":unittest.main()
