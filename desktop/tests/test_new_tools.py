import pathlib,sys,tempfile,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from image_tools import image_info,convert_image,edit_image
from capability_workshop import CapabilityWorkshop

class NewToolsTests(unittest.TestCase):
 def test_image_read_convert(self):
  from PIL import Image
  with tempfile.TemporaryDirectory() as t:
   root=pathlib.Path(t)
   Image.new("RGB",(32,24),"white").save(root/"source.png")
   self.assertEqual(image_info(root,"source.png",lambda _:True)["width"],32)
   result=convert_image(root,"source.png","new.webp",lambda _:True,16,16)
   self.assertEqual(result["width"],16)
   with self.assertRaises(FileExistsError):
    convert_image(root,"source.png","new.webp",lambda _:True)
 def test_non_destructive_image_editing(self):
  from PIL import Image
  with tempfile.TemporaryDirectory() as t:
   root=pathlib.Path(t)
   Image.new("RGB",(40,30),"white").save(root/"source.png")
   result=edit_image(root,"source.png","edited.png",lambda _:True,rotate=90,
                      brightness=1.2,contrast=1.1,crop=[0,0,20,10],grayscale=True)
   self.assertEqual((result["width"],result["height"]),(10,20))
   self.assertTrue((root/"source.png").exists())
   self.assertEqual(Image.open(root/"edited.png").mode,"L")
   with self.assertRaises(ValueError):
    edit_image(root,"source.png","bad.png",lambda _:True,crop=[0,0,100,200])
 def test_capability_smoke_and_denial(self):
  with tempfile.TemporaryDirectory() as t:
   w=CapabilityWorkshop(pathlib.Path(t)/"caps")
   identifier=w.draft("Echo","","def run(payload, output_dir):\n return {'echo':payload.get('value')}")
   self.assertEqual(w.test_capability(identifier,{"value":1},lambda _:False),{"cancelled":True})
   result=w.test_capability(identifier,{"value":1},lambda _:True)
   self.assertTrue(result["passed"])
   self.assertTrue(w._manifest(w._path(identifier))["last_test"]["passed"])
if __name__=="__main__":unittest.main()
