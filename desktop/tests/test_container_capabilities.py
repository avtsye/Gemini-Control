import os,pathlib,sys,tempfile,unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from capability_workshop import CapabilityWorkshop
from container_capabilities import run_plugin

class ContainerTests(unittest.TestCase):
 def test_missing_docker_fails_closed(self):
  with tempfile.TemporaryDirectory() as temp:
   root=pathlib.Path(temp)
   source=root/"main.py"
   source.write_text("def run(payload, output_dir): return {}")
   with patch("container_capabilities.shutil.which",return_value=None):
    result=run_plugin(source,root/"out",{})
    self.assertIn("error",result)
 def test_runtime_does_not_fallback_to_host(self):
  with tempfile.TemporaryDirectory() as temp:
   root=pathlib.Path(temp)
   workshop=CapabilityWorkshop(root/"cap")
   ident=workshop.draft("Test","","def run(payload, output_dir): return {'ok': True}")
   workshop.activate(ident,True)
   with patch.dict(os.environ,{"GEMINI_CONTROL_PLUGIN_RUNTIME":"docker"}):
    with patch("container_capabilities.shutil.which",return_value=None):
     self.assertIn("error",workshop.run(ident,{},lambda _:True))
if __name__=="__main__":unittest.main()
