import json,pathlib,sys,tempfile,unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from model_runtime import interpreter,worker_path,execute,prepare_environment
from model_worker import execute as model_execute
from semantic_tools import _encode

class FakeProcess:
 returncode=0
 stdout=json.dumps({"vectors":[[0.5,0.5]]})
 stderr=""

class ExternalAIWorkerTests(unittest.TestCase):
 def test_packaged_worker_is_found(self):
  with tempfile.TemporaryDirectory() as folder:
   root=pathlib.Path(folder); (root/"model_worker.py").write_text("# worker")
   with patch.object(sys,"_MEIPASS",str(root),create=True):
    self.assertEqual(worker_path(),root/"model_worker.py")
 def test_offline_execution_contract(self):
  with tempfile.TemporaryDirectory() as folder:
   root=pathlib.Path(folder);(root/"model_worker.py").write_text("# worker")
   with patch("model_runtime.interpreter",return_value="python"):
    with patch("model_runtime.worker_path",return_value=root/"model_worker.py"):
     with patch("model_runtime.subprocess.run",return_value=FakeProcess()) as process:
      result=execute(root,"embed",{"model":"fake","texts":["hello"]})
   self.assertEqual(result["vectors"],[[0.5,0.5]])
   self.assertEqual(process.call_args.args[0][1],"-I")
   self.assertEqual(process.call_args.kwargs["env"]["HF_HUB_OFFLINE"],"1")
 def test_external_embed_dispatch_from_frozen_app(self):
  with tempfile.TemporaryDirectory() as folder:
   root=pathlib.Path(folder)
   (root/"model").mkdir()
   with patch.object(sys,"frozen",True,create=True):
    with patch("model_runtime.execute",return_value={"vectors":[[1.0,0.0]]}) as remote:
     values,error=_encode(root,"model",["test"])
   self.assertEqual(values,[[1.0,0.0]])
   self.assertIsNone(error)
   self.assertEqual(remote.call_args.args[1],"embed")
 def test_worker_rejects_missing_local_model(self):
  with self.assertRaises(ValueError):
   model_execute({"operation":"image","model":"/missing-model","prompt":"a landscape",
                  "target":"/tmp/file.png"})
 def test_optional_package_install_rejected_without_consent(self):
  with tempfile.TemporaryDirectory() as folder:
   root=pathlib.Path(folder)
   self.assertEqual(prepare_environment(root,["embedding"],lambda _:False),
                    {"cancelled":True})
   self.assertFalse((root/".ai-venv").exists())
   with self.assertRaises(ValueError):
    prepare_environment(root,["unknown-module"],lambda _:True)
 def test_unknown_operation_never_executes(self):
  with tempfile.TemporaryDirectory() as folder:
   with self.assertRaises(ValueError):model_execute({"operation":"shell","model":folder})
if __name__=="__main__":unittest.main()
