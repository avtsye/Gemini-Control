import pathlib,sys,tempfile,unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from media_tools import engines,probe_media,convert_media

class MediaTests(unittest.TestCase):
 def test_missing_engine(self):
  with tempfile.TemporaryDirectory() as folder:
   root=pathlib.Path(folder)
   (root/"tone.wav").write_bytes(b"test")
   with patch("media_tools.shutil.which",return_value=None):
    self.assertIn("unavailable",probe_media(root,"tone.wav",lambda _:True))
    self.assertIn("unavailable",convert_media(root,"tone.wav","new.mp3",lambda _:True))
 def test_path_restriction(self):
  with tempfile.TemporaryDirectory() as folder:
   with self.assertRaises(ValueError):probe_media(folder,"../foo.wav",lambda _:True)
   with self.assertRaises(ValueError):convert_media(folder,"../foo.wav","out.mp3",lambda _:True)
if __name__=="__main__":unittest.main()
