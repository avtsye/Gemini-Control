import pathlib,sys,tempfile,unittest,wave
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QCoreApplication
from voice_recorder import VoiceRecorder

class Audio:
 def __init__(self):self.stopped=False
 def stop(self):self.stopped=True
class Device:
 def __init__(self,data):self.data=data
 def readAll(self):
  data,self.data=self.data,b""
  return data

class VoiceRecorderTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.app=QCoreApplication.instance() or QCoreApplication([])
 def test_stop_writes_valid_wav(self):
  with tempfile.TemporaryDirectory() as root:
   recorder=VoiceRecorder(root)
   recorder.audio=Audio()
   recorder.device=Device(b"\x00\x00"*160)
   recorder.recording=True
   output=recorder.stop()
   path=pathlib.Path(root)/output["recorded_file"]
   self.assertTrue(path.exists())
   with wave.open(str(path),"rb") as source:
    self.assertEqual(source.getframerate(),16000)
    self.assertEqual(source.getnchannels(),1)
   self.assertFalse(recorder.recording)
 def test_auto_stop_does_not_recurse_and_result_remains_available(self):
  with tempfile.TemporaryDirectory() as root:
   recorder=VoiceRecorder(root)
   recorder.MAX_BYTES=8
   recorder.audio=Audio()
   recorder.device=Device(b"\x00"*10)
   recorder.recording=True
   recorder._read()
   self.assertFalse(recorder.recording)
   result=recorder.stop()
   self.assertIn("recorded_file",result)
   self.assertEqual(recorder.stop(),{"error":"No recording in progress"})
if __name__=="__main__":unittest.main()
