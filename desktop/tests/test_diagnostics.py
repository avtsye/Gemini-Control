import pathlib,sys,tempfile,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from diagnostics import inspect_environment
from capability_workshop import CapabilityWorkshop
from conversation_store import ConversationStore

class HealthTests(unittest.TestCase):
 def test_report_is_safe_and_actionable(self):
  with tempfile.TemporaryDirectory() as root:
   path=pathlib.Path(root)
   store=ConversationStore(path/"history.db")
   workshop=CapabilityWorkshop(path/"plugins")
   workshop.draft("Local example","",
      "def run(payload, output_dir): return {}")
   result=inspect_environment(workshop,store.path)
   self.assertIn("python",result)
   self.assertIn("psutil",result["modules"])
   self.assertIn("tesseract",result["executables"])
   self.assertEqual(result["extensions"]["draft"],1)
   self.assertEqual(result["conversation_database"],"ok")
   self.assertNotIn(str(path),str(result))
if __name__=="__main__":unittest.main()
