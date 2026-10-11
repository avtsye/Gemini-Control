import pathlib,sys,tempfile,unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from capability_workshop import CapabilityWorkshop

class FrozenRuntimeTests(unittest.TestCase):
 def test_runner_found_in_frozen_bundle(self):
  with tempfile.TemporaryDirectory() as folder:
   root=pathlib.Path(folder)
   (root/"capability_runner.py").write_text("# runner",encoding="utf-8")
   with patch.object(sys,"_MEIPASS",str(root),create=True):
    self.assertEqual(CapabilityWorkshop._runner_path(),root/"capability_runner.py")
 def test_frozen_exe_never_uses_self_as_python(self):
  with patch.object(sys,"frozen",True,create=True):
   with patch("capability_workshop.shutil.which",return_value="C:/Python/python.exe"):
    self.assertEqual(CapabilityWorkshop._system_python(),"C:/Python/python.exe")
   with patch("capability_workshop.shutil.which",return_value=None):
    with self.assertRaises(RuntimeError):CapabilityWorkshop._system_python()
 def test_external_runtime_used_for_installed_plugin(self):
  with tempfile.TemporaryDirectory() as folder:
   workshop=CapabilityWorkshop(pathlib.Path(folder)/"caps")
   identifier=workshop.draft("Dummy","", "def run(payload, output_dir): return {}")
   with patch.object(sys,"frozen",True,create=True):
    with patch("capability_workshop.shutil.which",return_value="C:/Python/python.exe"):
     self.assertEqual(workshop._interpreter(workshop._path(identifier)),"C:/Python/python.exe")
if __name__=="__main__":unittest.main()
