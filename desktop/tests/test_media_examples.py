import pathlib,sys,tempfile,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from capability_workshop import CapabilityWorkshop

ROOT=pathlib.Path(__file__).resolve().parents[1]
class MediaExampleTests(unittest.TestCase):
 def test_audio_example_produces_wav(self):
  with tempfile.TemporaryDirectory() as root:
   workshop=CapabilityWorkshop(pathlib.Path(root)/"extensions")
   source=(ROOT/"examples/audio_tone.py").read_text(encoding="utf-8")
   identifier=workshop.draft("WAV","Test",source)
   workshop.activate(identifier,True)
   result=workshop.run(identifier,{"frequency":440,"seconds":0.1},lambda _:True)
   wav=pathlib.Path(result["result"]["created_file"])
   self.assertEqual(wav.read_bytes()[:4],b"RIFF")
 def test_video_example_has_valid_entrypoint(self):
  with tempfile.TemporaryDirectory() as root:
   workshop=CapabilityWorkshop(pathlib.Path(root)/"extensions")
   source=(ROOT/"examples/video_gif.py").read_text(encoding="utf-8")
   identifier=workshop.draft("GIF","Test",source)
   self.assertEqual(workshop.inspect(identifier)["status"],"draft")
if __name__=="__main__":unittest.main()
