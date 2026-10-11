import pathlib,sys,tempfile,unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from speech_tools import speech_status,text_to_speech,transcribe_local

class SpeechTests(unittest.TestCase):
 def test_no_engine_is_reported(self):
  with tempfile.TemporaryDirectory() as tmp:
   with patch.dict(sys.modules,{"pyttsx3":None}):
    result=text_to_speech(tmp,"שלום","speech.wav",lambda _:True)
    self.assertIn("unavailable",result)
 def test_input_validation(self):
  with tempfile.TemporaryDirectory() as tmp:
   with self.assertRaises(ValueError):
    text_to_speech(tmp,"שלום","../outside.wav",lambda _:True)
   with self.assertRaises(ValueError):
    transcribe_local(tmp,"../a.wav","model","out.txt",lambda _:True)
 def test_status_shape(self):
  state=speech_status()
  self.assertIn("tts_available",state)
  self.assertIn("transcription_available",state)
if __name__=="__main__":unittest.main()
