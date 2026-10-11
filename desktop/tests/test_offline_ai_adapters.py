import pathlib,sys,tempfile,unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from semantic_tools import embedding_status,build_semantic_index,semantic_search
from local_image_generation import image_model_status,generate_local_image

class OfflineAIAdapters(unittest.TestCase):
 def test_semantic_missing_model(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);(root/"Notes").mkdir()
   self.assertFalse(embedding_status(root,"Models/missing")["local_model_ready"])
   self.assertEqual(build_semantic_index(root,"Models/missing","Notes",lambda _:False),{"cancelled":True})
   self.assertIn("error",semantic_search(root,"query","Models/missing",lambda _:True))
 def test_image_missing_model_and_path_validation(self):
  with tempfile.TemporaryDirectory() as d:
   self.assertFalse(image_model_status(d,"missing")["model_ready"])
   self.assertIn("unavailable",generate_local_image(d,"a blue tree","missing","tree.png",lambda _:True))
   with self.assertRaises(ValueError):
    generate_local_image(d,"a blue tree","missing","../bad.png",lambda _:True)
 def test_no_execution_without_approval(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d)
   model=root/"Models"/"test";model.mkdir(parents=True)
   (model/"model_index.json").write_text("{}")
   with patch("local_image_generation.image_model_status",
              return_value={"diffusers_installed":True,"torch_installed":True}):
    self.assertEqual(generate_local_image(root,"a nice scene","Models/test","art.png",
         lambda _:False),{"cancelled":True})
   self.assertFalse((root/"art.png").exists())
if __name__=="__main__":unittest.main()
